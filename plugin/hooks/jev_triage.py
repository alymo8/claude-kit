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

import os
import re
from dataclasses import dataclass
from pathlib import Path

MODES = ("off", "shadow", "active")
DEFAULT_THRESHOLD = 0.65
TIMEOUT_S = 1.5
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
