#!/usr/bin/env python3
"""UserPromptSubmit hook: opt-in jev triage of each prompt (pilot).

CLAUDE_KIT_JEV selects the mode: off (default; unset, empty or unknown),
shadow (judge and log only) or active (also add one-line hints as
additionalContext). One TypeSafe system_one call asks the three Noul questions
in QUESTIONS; a score at or above its threshold (default 0.65, override with
CLAUDE_KIT_JEV_T_<KEY>) fires. Every judged prompt is appended to
~/.claude/claude-kit/jev/log.jsonl. Needs `pip install "typesafe-sdk>=0.7"` and
TYPESAFE_API_KEY; any failure is logged and the prompt passes unchanged.
Always exits 0 (ADR 0007). Spec:
docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

MODES = ("off", "shadow", "active")
DEFAULT_THRESHOLD = 0.65
TIMEOUT_S = 1.5  # SDK timeout, per HTTP phase
DEADLINE_S = 2.0  # wall clock for the whole judgment; hook entry timeout is 3 s
MIN_WORDS = 3
STRIP_RE = re.compile(
    r"<system-reminder>.*?</system-reminder>"
    r"|<pasted_content[^>]*>.*?</pasted_content[^>]*>",
    re.S,
)


@dataclass(frozen=True)
class Question:
    key: str
    instructions: str
    yes: str
    no: str
    hint: str


QUESTIONS = (
    Question(
        "underspecified",
        "Would acting on this request to a coding assistant need information it "
        "does not give, such as the target, the scope or the expected result?",
        "Important details are missing; the assistant would have to guess.",
        "The request is clear enough to act on, or it is a question or a reply.",
        "jev triage: this prompt looks underspecified; ask one focused "
        "clarifying question before acting.",
    ),
    Question(
        "new_feature",
        "Is this a request to build a new feature or capability, rather than a "
        "question, a bug fix, a review or a chore?",
        "It asks for new functionality to be built.",
        "It is a question, fix, review, chore, or a reply to the assistant.",
        "jev triage: this looks like a new feature; run the pre-flight branch "
        "check (CLAUDE.md) before starting.",
    ),
    Question(
        "key_decision",
        "Does carrying out this request hinge on a choice about scope, "
        "architecture, product boundary or an irreversible action?",
        "A significant choice must be made that the request does not settle.",
        "No significant choice is involved, or the request already settles it.",
        "jev triage: this may hinge on a key decision; surface it by name with "
        "options and a recommendation, and get explicit confirmation.",
    ),
)
KEYS = tuple(q.key for q in QUESTIONS)


def mode() -> str:
    value = os.environ.get("CLAUDE_KIT_JEV", "").strip().lower()
    return value if value in MODES else "off"


def thresholds() -> dict[str, float]:
    limits = {}
    for key in KEYS:
        try:
            value = float(os.environ.get(f"CLAUDE_KIT_JEV_T_{key.upper()}", ""))
        except ValueError:
            value = DEFAULT_THRESHOLD
        limits[key] = value if 0.0 <= value <= 1.0 else DEFAULT_THRESHOLD
    return limits


def clean(text: str) -> str:
    """The prompt without harness-injected reminders and pasted blocks."""
    return STRIP_RE.sub("", text).strip()


def should_judge(text: str) -> bool:
    """Skip empty text, slash commands, harness tags and short replies."""
    if not text or text[0] in "/<":
        return False
    return len(text.split()) >= MIN_WORDS


def fired(scores: dict[str, float], limits: dict[str, float]) -> list[str]:
    return [k for k in KEYS if k in scores and scores[k] >= limits[k]]


def hints(keys: list[str]) -> str:
    by_key = {q.key: q.hint for q in QUESTIONS}
    return " ".join(by_key[k] for k in keys)


def jev_dir() -> Path:
    return Path.home() / ".claude" / "claude-kit" / "jev"


class JevError(Exception):
    """A judgment failed; ``code`` is the short string written to the log."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Judgment:
    scores: dict[str, float]
    usage: dict | None = None


def judge(prompt: str) -> Judgment:
    """One TypeSafe system_one call with the three Noul questions."""
    if not os.environ.get("TYPESAFE_API_KEY", "").strip():
        raise JevError("missing_key")
    try:
        import typesafe_sdk
    except ImportError as exc:
        raise JevError("missing_sdk") from exc
    try:
        questions = {
            q.key: typesafe_sdk.Noul(
                instructions=q.instructions, criteria={"true": q.yes, "false": q.no}
            )
            for q in QUESTIONS
        }
        with typesafe_sdk.TypeSafeClient(
            timeout=TIMEOUT_S, retry=typesafe_sdk.RetryPolicy(max_retries=0)
        ) as client:
            result = client.system_one(state=prompt, questions=questions)
        scores = {k: float(result.nouls[k].noul) for k in KEYS}
        usage = {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "model": result.model,
        }
    except TimeoutError as exc:
        raise JevError("timeout") from exc
    except Exception as exc:
        raise api_error(exc) from exc
    return Judgment(scores, usage)


def api_error(exc: BaseException) -> JevError:
    detail = " ".join(str(exc).split())[:200]  # one line in stderr and the log
    return JevError(f"api_error: {type(exc).__name__}: {detail}")


def judge_before_deadline(prompt: str) -> Judgment:
    """judge() with a wall-clock cap: the SDK timeout is per HTTP phase, and the
    hook is killed at its 3 s entry timeout before it could log anything."""
    box: dict[str, object] = {}

    def run() -> None:
        try:
            box["judgment"] = judge(prompt)
        except JevError as exc:
            box["error"] = exc
        except Exception as exc:
            box["error"] = api_error(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(DEADLINE_S)
    if worker.is_alive():
        raise JevError("timeout")
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box["judgment"]  # type: ignore[return-value]


def append_log(record: dict) -> None:
    path = jev_dir() / "log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def new_record(event: dict, current: str, prompt: str, limits: dict) -> dict:
    return {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "session_id": event.get("session_id"),
        "project": Path(str(event.get("cwd") or "")).name,
        "mode": current,
        "prompt": prompt,
        "scores": None,
        "thresholds": limits,
        "fired": [],
        "injected": False,
        "latency_ms": None,
        "usage": None,
        "error": None,
    }


def main() -> int:
    try:
        # Always drain stdin, so a large prompt never meets a closed pipe. Windows
        # stdin defaults to the ANSI code page; Claude Code sends UTF-8.
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        current = mode()
        if current == "off":
            return 0
        event = json.loads(raw or "{}")
        if not isinstance(event, dict) or not isinstance(event.get("prompt"), str):
            return 0
        prompt = clean(event["prompt"])
        if not should_judge(prompt):
            return 0
        limits = thresholds()
        record = new_record(event, current, prompt, limits)
        start = time.perf_counter()
        try:
            judgment = judge_before_deadline(prompt)
        except JevError as exc:
            record["error"] = exc.code
        else:
            record["scores"] = judgment.scores
            record["usage"] = judgment.usage
            record["fired"] = fired(judgment.scores, limits)
        record["latency_ms"] = round((time.perf_counter() - start) * 1000)
        text = hints(record["fired"]) if current == "active" else ""
        record["injected"] = bool(text)
        if record["error"]:
            print(f"[claude-kit] jev triage: {record['error']}", file=sys.stderr)
        try:
            append_log(record)
        except OSError as exc:
            print(f"[claude-kit] jev triage: cannot write log: {exc}", file=sys.stderr)
        if text:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": text,
                }
            }
            print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] jev triage error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
