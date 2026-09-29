# jev triage pilot Implementation Plan

- **Status:** implemented
- **Date:** 2026-09-28

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in (`CLAUDE_KIT_JEV=off|shadow|active`, default off) `UserPromptSubmit` hook that judges each prompt with TypeSafe's jev model, logs every judgment locally, adds one-line hints in `active` mode, and ships an evaluation script (`replay` / `score` / `report`) that measures whether it helps.

**Architecture:** One stdlib-only hook module, `plugin/hooks/jev_triage.py`, owns the question definitions, prompt filtering, thresholds, the SDK call (`judge`, lazily importing `typesafe_sdk`) and the log. One script, `plugin/scripts/jev-eval.py`, imports that module so the hook and the evaluation judge exactly the same thing, and reads Claude Code transcripts (`~/.claude/projects/*/*.jsonl`) to replay past prompts and to derive outcomes for the report.

**Tech Stack:** Python ≥ 3.11 stdlib; optional `typesafe-sdk>=0.7` (sync `TypeSafeClient`); pytest; ruff.

**Spec:** `docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md`

## Global Constraints

- Hooks always exit 0 and never block a prompt (ADR 0007); every failure goes to stderr prefixed `[claude-kit] jev triage`.
- With `CLAUDE_KIT_JEV` unset, empty or unrecognised: no `typesafe_sdk` import, no network, no output, no log file.
- `typesafe-sdk` is an optional per-machine install; it must **not** be added to `pyproject.toml` or CI.
- Log and eval outputs live in `~/.claude/claude-kit/jev/` (outside every repo). The kit repo is public: no real prompts, private repo names or usernames in tracked files, fixtures included.
- SDK call: `TypeSafeClient(timeout=1.5, retry=RetryPolicy(max_retries=0))`; hook entry `timeout: 3` in `hooks.json`.
- Default threshold `0.65`; overrides `CLAUDE_KIT_JEV_T_UNDERSPECIFIED`, `CLAUDE_KIT_JEV_T_NEW_FEATURE`, `CLAUDE_KIT_JEV_T_KEY_DECISION`, floats in `[0, 1]`, anything else falls back to 0.65.
- Code style: ruff (`E, F, I, UP, B`, line length 88 including E501, target py311). Code blocks below are pre-format: run `ruff format plugin tests`, then rewrap any line `ruff check` still reports as E501 (strings and `# fmt: skip` lines are not rewrapped by the formatter). CI runs on ubuntu and windows, Python 3.12.
- Before every commit: `pytest` and `ruff check plugin tests; ruff format --check plugin tests` from the worktree root, all green.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## SDK reference (confirmed from typesafe-sdk 0.7.2 source)

```python
import typesafe_sdk
with typesafe_sdk.TypeSafeClient(
    timeout=1.5, retry=typesafe_sdk.RetryPolicy(max_retries=0)
) as client:                      # reads TYPESAFE_API_KEY
    result = client.system_one(
        state="prompt text",
        questions={"key": typesafe_sdk.Noul(
            instructions="...", criteria={"true": "...", "false": "..."})},
    )
result.nouls["key"].noul          # float 0..1
result.usage.input_tokens, result.usage.output_tokens   # int | None
result.model                      # str
# typesafe_sdk.TypeSafeAPITimeoutError subclasses TimeoutError.
```

## Refinements to the spec made by this plan

These are applied to the spec in Task 7 so it matches what ships:

1. The hook and replay share `clean(prompt)` (strips `<system-reminder>` and `<pasted_content …>` blocks) and `should_judge(text)` (skips empty, text starting with `/` or `<`, and fewer than 3 words). The spec had the 3-word rule only in replay. Without it, every "lgtm" or "a" the user types in reply to Claude would be judged, and flagged as underspecified.
2. `judge(prompt)` returns `Judgment(scores, usage)` rather than a bare dict, so the log can record usage.
3. `score` reports calls and token totals from usage. TypeSafe prices per evaluation, so cost = calls × the price on the TypeSafe dashboard; the script does not hard-code a price.
4. `report`: *preflight* is `n/a` when the turn made no `Write`/`Edit`, so it is excluded from the miss rate.

## Review Focus

1. **Short replies to Claude** ("lgtm", "a", "1 yes") must not be judged. Covered in Task 2 by `test_should_judge`.
2. **Non-ASCII prompts on Windows** (accents, emoji) must reach jev and the log intact, because Windows stdin defaults to cp1252. Covered in Task 3 by `test_unicode_prompt_survives_stdin`.
3. **Unwritable log location** must still exit 0, and in `active` mode must still inject hints. Covered in Task 3 by `test_unwritable_log_still_injects`.
4. **labels.csv round-tripped through Excel** (BOM, blank rows, `1.0`, ` 1 `) must still score. Covered in Task 5 by `test_score_tolerates_excel_edits`.
5. **Log records whose transcript is missing, and malformed transcript lines**, must be skipped without crashing the report. Covered in Task 6 by `test_report_end_to_end`.

---

### Task 1: Isolate test subprocesses from the developer's kit settings

The baseline fails when the developer shell sets `CLAUDE_KIT_NUDGE_AT` (as it does on the author's machine): `tests/test_context_nudge.py` passes `os.environ` to the hook. The jev tests would hit the same problem with `CLAUDE_KIT_JEV` or `TYPESAFE_API_KEY` set.

**Files:**
- Modify: `tests/helpers.py`
- Modify: `tests/test_context_nudge.py` (the `run` helper, `env=` line)
- Create: `tests/test_helpers.py`

**Interfaces:**
- Produces: `helpers.clean_env(**extra: str) -> dict[str, str]`; `helpers.run_script(script, *args, stdin="", cwd=None, env=None)`, where `env=None` means `clean_env()`.

- [ ] **Step 1: Write the failing test** in `tests/test_helpers.py`:

```python
from helpers import clean_env


def test_clean_env_drops_kit_and_typesafe_settings(monkeypatch):
    monkeypatch.setenv("CLAUDE_KIT_NUDGE_AT", "1")
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setenv("KEEP_ME", "1")
    env = clean_env(EXTRA="x")
    assert "CLAUDE_KIT_NUDGE_AT" not in env
    assert "TYPESAFE_API_KEY" not in env
    assert env["KEEP_ME"] == "1"
    assert env["EXTRA"] == "x"
```

- [ ] **Step 2: Run it.** `pytest tests/test_helpers.py -v` → FAIL (`ImportError: cannot import name 'clean_env'`).

- [ ] **Step 3: Implement** in `tests/helpers.py`. Add `import os`, then add this function above `run_script`:

```python
def clean_env(**extra: str) -> dict[str, str]:
    """os.environ without the developer's CLAUDE_KIT_* and TYPESAFE_* settings."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("CLAUDE_KIT_", "TYPESAFE_"))
    }
    env.update(extra)
    return env
```

Change `run_script` to accept and pass an environment:

```python
def run_script(
    script: Path,
    *args: str,
    stdin: str = "",
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a Python script the way a hook runner would: stdin in, text out."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env=clean_env() if env is None else env,
        timeout=60,
    )
```

In `tests/test_context_nudge.py`, change the import to `from helpers import PLUGIN, clean_env, load_module, run_script` and, in `run`, replace `env={**os.environ, **(env or {})},` with `env={**clean_env(), **(env or {})},`. Remove `import os` if ruff reports it unused.

- [ ] **Step 4: Verify.** `CLAUDE_KIT_NUDGE_AT=999999999 pytest tests/test_helpers.py tests/test_context_nudge.py -v` → all PASS. In PowerShell: `$env:CLAUDE_KIT_NUDGE_AT='999999999'; pytest tests/test_helpers.py tests/test_context_nudge.py -v`. Then run the full `pytest` and ruff.

- [ ] **Step 5: Commit.**

```bash
git add tests/helpers.py tests/test_helpers.py tests/test_context_nudge.py
git commit -m "Isolate test subprocesses from developer CLAUDE_KIT_* settings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: jev_triage core (questions, mode, thresholds, filtering, hints)

**Files:**
- Create: `plugin/hooks/jev_triage.py`
- Create: `tests/test_jev_triage.py`

**Interfaces:**
- Produces (module `jev_triage`): `QUESTIONS: tuple[Question, ...]`; `KEYS == ("underspecified", "new_feature", "key_decision")`; `DEFAULT_THRESHOLD = 0.65`; `mode() -> str`; `thresholds() -> dict[str, float]`; `clean(text: str) -> str`; `should_judge(text: str) -> bool`; `fired(scores: dict[str, float], limits: dict[str, float]) -> list[str]` (in `KEYS` order); `hints(keys: list[str]) -> str`; `jev_dir() -> Path`.

- [ ] **Step 1: Write the failing tests** in `tests/test_jev_triage.py`:

```python
import os

import pytest

from helpers import PLUGIN, load_module

HOOK = PLUGIN / "hooks" / "jev_triage.py"
triage = load_module(HOOK, "jev_triage")


@pytest.fixture(autouse=True)
def no_kit_env(monkeypatch):
    for name in list(os.environ):
        if name.startswith(("CLAUDE_KIT_", "TYPESAFE_")):
            monkeypatch.delenv(name)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "off"),
        ("", "off"),
        ("banana", "off"),
        ("OFF", "off"),
        ("shadow", "shadow"),
        (" Active ", "active"),
    ],
)
def test_mode(monkeypatch, value, expected):
    if value is not None:
        monkeypatch.setenv("CLAUDE_KIT_JEV", value)
    assert triage.mode() == expected


def test_thresholds_default_and_overrides(monkeypatch):
    assert triage.thresholds() == {
        "underspecified": 0.65,
        "new_feature": 0.65,
        "key_decision": 0.65,
    }
    monkeypatch.setenv("CLAUDE_KIT_JEV_T_NEW_FEATURE", "0.8")
    monkeypatch.setenv("CLAUDE_KIT_JEV_T_UNDERSPECIFIED", "high")
    monkeypatch.setenv("CLAUDE_KIT_JEV_T_KEY_DECISION", "1.5")
    assert triage.thresholds() == {
        "underspecified": 0.65,
        "new_feature": 0.8,
        "key_decision": 0.65,
    }


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", False),
        ("   ", False),
        ("/ship docs/x.md now", False),
        ("<command-name>/clear</command-name>", False),
        ("lgtm", False),
        ("1 yes", False),
        ("add a dark mode toggle", True),
    ],
)
def test_should_judge(text, expected):
    assert triage.should_judge(text) is expected


def test_clean_strips_reminders_and_pasted_blocks():
    raw = (
        "fix the login bug <system-reminder>ctx</system-reminder>\n"
        '<pasted_content id="ab">huge log</pasted_content id="ab">'
    )
    assert triage.clean(raw) == "fix the login bug"


def test_fired_and_hints():
    limits = dict.fromkeys(triage.KEYS, 0.65)
    keys = triage.fired(
        {"underspecified": 0.2, "new_feature": 0.65, "key_decision": 0.9}, limits
    )
    assert keys == ["new_feature", "key_decision"]
    text = triage.hints(keys)
    assert "pre-flight branch check" in text
    assert "key decision" in text
    assert "underspecified" not in text
    assert triage.hints([]) == ""
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_triage.py -v` → FAIL (module file does not exist).

- [ ] **Step 3: Implement** `plugin/hooks/jev_triage.py`. This task writes the module up to `jev_dir`; Task 3 adds `Judgment`, `JevError`, `judge`, `append_log` and `main`.

```python
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
import time
from dataclasses import dataclass
from datetime import UTC, datetime
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
```

`json`, `sys`, `time` and `datetime` are used in Task 3. If ruff flags them as unused now, add them in Task 3 instead.

- [ ] **Step 4: Verify.** `pytest tests/test_jev_triage.py -v` → PASS; full `pytest`, ruff.

- [ ] **Step 5: Commit.**

```bash
git add plugin/hooks/jev_triage.py tests/test_jev_triage.py
git commit -m "jev triage: questions, mode, thresholds and prompt filtering

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: jev_triage judge, log and hook entry point

**Files:**
- Modify: `plugin/hooks/jev_triage.py` (append)
- Modify: `tests/test_jev_triage.py` (append)

**Interfaces:**
- Consumes: everything from Task 2.
- Produces: `Judgment(scores: dict[str, float], usage: dict | None)`; `JevError(code: str)` with `.code`; `judge(prompt: str) -> Judgment` (raises `JevError` with code `missing_key`, `missing_sdk`, `timeout` or `api_error: <Type>: <msg>`); `append_log(record: dict) -> None`; `main() -> int`.
- Log record keys, in order: `ts, session_id, project, mode, prompt, scores, thresholds, fired, injected, latency_ms, usage, error`.

- [ ] **Step 1: Write the failing tests** by appending to `tests/test_jev_triage.py`. Add `import io`, `import json`, `import sys`, `import types` at the top and extend the helpers import to `from helpers import PLUGIN, clean_env, load_module, run_script`.

```python
PROMPT = "add a dark mode toggle to settings"
HIGH = {"underspecified": 0.1, "new_feature": 0.9, "key_decision": 0.2}


def fake(scores):
    usage = {"input_tokens": 10, "output_tokens": 3, "model": "jev-test"}
    return lambda prompt: triage.Judgment(scores, usage)


def failing(code):
    def judge(prompt):
        raise triage.JevError(code)

    return judge


def must_not_call(prompt):
    raise AssertionError("judge must not be called")


def run_main(monkeypatch, capsys, tmp_path, prompt=PROMPT, mode="active", judge=None):
    monkeypatch.setattr(triage, "jev_dir", lambda: tmp_path / "jev")
    if mode:
        monkeypatch.setenv("CLAUDE_KIT_JEV", mode)
    if judge:
        monkeypatch.setattr(triage, "judge", judge)
    event = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "s1",
        "cwd": str(tmp_path / "proj"),
        "prompt": prompt,
    }
    raw = io.BytesIO(json.dumps(event).encode("utf-8"))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(raw, encoding="utf-8"))
    assert triage.main() == 0
    return capsys.readouterr()


def read_log(tmp_path):
    path = tmp_path / "jev" / "log.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_off_does_nothing(monkeypatch, capsys, tmp_path):
    monkeypatch.delitem(sys.modules, "typesafe_sdk", raising=False)
    out = run_main(monkeypatch, capsys, tmp_path, mode=None, judge=must_not_call)
    assert out.out == ""
    assert read_log(tmp_path) == []
    assert "typesafe_sdk" not in sys.modules


def test_shadow_logs_without_context(monkeypatch, capsys, tmp_path):
    out = run_main(monkeypatch, capsys, tmp_path, mode="shadow", judge=fake(HIGH))
    assert out.out == ""
    [record] = read_log(tmp_path)
    assert list(record) == [
        "ts", "session_id", "project", "mode", "prompt", "scores", "thresholds",
        "fired", "injected", "latency_ms", "usage", "error",
    ]  # fmt: skip
    assert record["mode"] == "shadow"
    assert record["session_id"] == "s1"
    assert record["project"] == "proj"
    assert record["prompt"] == PROMPT
    assert record["scores"] == HIGH
    assert record["fired"] == ["new_feature"]
    assert record["injected"] is False
    assert isinstance(record["latency_ms"], int)
    assert record["usage"]["model"] == "jev-test"
    assert record["error"] is None


def test_active_injects_only_fired_hints(monkeypatch, capsys, tmp_path):
    out = run_main(monkeypatch, capsys, tmp_path, judge=fake(HIGH))
    payload = json.loads(out.out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "UserPromptSubmit"
    assert "pre-flight branch check" in payload["additionalContext"]
    assert "underspecified" not in payload["additionalContext"]
    assert read_log(tmp_path)[0]["injected"] is True


def test_active_below_threshold_is_silent(monkeypatch, capsys, tmp_path):
    low = dict.fromkeys(triage.KEYS, 0.3)
    out = run_main(monkeypatch, capsys, tmp_path, judge=fake(low))
    assert out.out == ""
    [record] = read_log(tmp_path)
    assert record["fired"] == []
    assert record["injected"] is False


def test_threshold_override_applies(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("CLAUDE_KIT_JEV_T_NEW_FEATURE", "0.95")
    out = run_main(monkeypatch, capsys, tmp_path, judge=fake(HIGH))
    assert out.out == ""
    assert read_log(tmp_path)[0]["thresholds"]["new_feature"] == 0.95


@pytest.mark.parametrize("prompt", ["", "lgtm", "/ship docs/x.md now"])
def test_skipped_prompts_are_not_judged(monkeypatch, capsys, tmp_path, prompt):
    out = run_main(monkeypatch, capsys, tmp_path, prompt=prompt, judge=must_not_call)
    assert out.out == ""
    assert read_log(tmp_path) == []


@pytest.mark.parametrize("code", ["timeout", "api_error: RuntimeError: boom"])
def test_errors_fail_open(monkeypatch, capsys, tmp_path, code):
    out = run_main(monkeypatch, capsys, tmp_path, judge=failing(code))
    assert out.out == ""
    assert "[claude-kit] jev triage" in out.err
    [record] = read_log(tmp_path)
    assert record["error"] == code
    assert record["scores"] is None


def test_missing_key(monkeypatch, capsys, tmp_path):
    run_main(monkeypatch, capsys, tmp_path)
    assert read_log(tmp_path)[0]["error"] == "missing_key"


def test_missing_sdk(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "typesafe_sdk", None)
    run_main(monkeypatch, capsys, tmp_path)
    assert read_log(tmp_path)[0]["error"] == "missing_sdk"


def test_unwritable_log_still_injects(monkeypatch, capsys, tmp_path):
    blocker = tmp_path / "jev"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(triage, "jev_dir", lambda: blocker / "sub")
    monkeypatch.setenv("CLAUDE_KIT_JEV", "active")
    monkeypatch.setattr(triage, "judge", fake(HIGH))
    event = json.dumps({"session_id": "s1", "cwd": "x", "prompt": PROMPT})
    raw = io.BytesIO(event.encode("utf-8"))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(raw, encoding="utf-8"))
    assert triage.main() == 0
    out = capsys.readouterr()
    assert "pre-flight branch check" in out.out
    assert "cannot write log" in out.err


def fake_sdk(calls, result=None, exc=None):
    class Client:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def system_one(self, **kwargs):
            calls.append(("call", kwargs))
            if exc:
                raise exc
            return result

    return types.SimpleNamespace(
        Noul=lambda **kw: kw, RetryPolicy=lambda **kw: kw, TypeSafeClient=Client
    )


def test_judge_calls_sdk_with_pilot_settings(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    result = types.SimpleNamespace(
        nouls={k: types.SimpleNamespace(noul=0.5) for k in triage.KEYS},
        usage=types.SimpleNamespace(input_tokens=5, output_tokens=1),
        model="jev-x",
    )
    calls = []
    monkeypatch.setitem(sys.modules, "typesafe_sdk", fake_sdk(calls, result))
    judgment = triage.judge(PROMPT)
    assert judgment.scores == dict.fromkeys(triage.KEYS, 0.5)
    assert judgment.usage == {"input_tokens": 5, "output_tokens": 1, "model": "jev-x"}
    (_, init), (_, call) = calls
    assert init == {"timeout": 1.5, "retry": {"max_retries": 0}}
    assert call["state"] == PROMPT
    assert list(call["questions"]) == list(triage.KEYS)
    assert set(call["questions"]["new_feature"]["criteria"]) == {"true", "false"}


@pytest.mark.parametrize(
    "exc,code",
    [
        (TimeoutError("slow"), "timeout"),
        (RuntimeError("boom"), "api_error: RuntimeError: boom"),
    ],
)
def test_judge_maps_sdk_errors(monkeypatch, exc, code):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "typesafe_sdk", fake_sdk([], exc=exc))
    with pytest.raises(triage.JevError) as info:
        triage.judge(PROMPT)
    assert info.value.code == code


def test_unicode_prompt_survives_stdin(tmp_path):
    prompt = "ajoute un résumé 🚀 à la page d'accueil"
    event = json.dumps({"session_id": "s1", "cwd": "x", "prompt": prompt})
    env = clean_env(
        CLAUDE_KIT_JEV="shadow", HOME=str(tmp_path), USERPROFILE=str(tmp_path)
    )
    result = run_script(HOOK, stdin=event, env=env)
    assert result.returncode == 0
    assert result.stdout == ""
    log = tmp_path / ".claude" / "claude-kit" / "jev" / "log.jsonl"
    [record] = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert record["prompt"] == prompt
    assert record["error"] == "missing_key"


def test_flag_off_subprocess_creates_nothing(tmp_path):
    event = json.dumps({"session_id": "s1", "cwd": "x", "prompt": PROMPT})
    env = clean_env(HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    result = run_script(HOOK, stdin=event, env=env)
    assert result.returncode == 0
    assert result.stdout == ""
    assert not (tmp_path / ".claude").exists()
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_triage.py -v` → the new tests FAIL (`AttributeError: ... 'Judgment'`, `main`).

- [ ] **Step 3: Implement** by appending to `plugin/hooks/jev_triage.py`:

```python
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
        raise JevError(f"api_error: {type(exc).__name__}: {str(exc)[:200]}") from exc
    return Judgment(scores, usage)


def append_log(record: dict) -> None:
    path = jev_dir() / "log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    try:
        current = mode()
        if current == "off":
            return 0
        # Windows stdin defaults to the ANSI code page; Claude Code sends UTF-8.
        event = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
        if not isinstance(event, dict) or not isinstance(event.get("prompt"), str):
            return 0
        prompt = clean(event["prompt"])
        if not should_judge(prompt):
            return 0
        limits = thresholds()
        record = {
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
        start = time.perf_counter()
        try:
            judgment = judge(prompt)
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
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": text,
                        }
                    }
                )
            )
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] jev triage error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verify.** `pytest tests/test_jev_triage.py -v` → PASS; full `pytest`, ruff (`ruff format plugin tests` first if the format check fails).

- [ ] **Step 5: Commit.**

```bash
git add plugin/hooks/jev_triage.py tests/test_jev_triage.py
git commit -m "jev triage: SDK call, local log and fail-open hook entry point

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Register the hook and bump the plugin version

**Files:**
- Modify: `plugin/hooks/hooks.json` (the `UserPromptSubmit` array)
- Modify: `plugin/.claude-plugin/plugin.json` (`version`, `description`)
- Modify: `tests/test_plugin_manifest.py`

- [ ] **Step 1: Write the failing tests.** In `tests/test_plugin_manifest.py`, change `test_plugin_version_bumped` to expect `"0.4.0"` and add `assert "jev" in data["description"]`, then append:

```python
def test_jev_triage_hook_registered_with_timeout():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    entries = [
        h
        for g in hooks["hooks"]["UserPromptSubmit"]
        for h in g["hooks"]
        if "jev_triage.py" in h["command"]
    ]
    assert len(entries) == 1
    assert entries[0]["timeout"] == 3
```

- [ ] **Step 2: Run them.** `pytest tests/test_plugin_manifest.py -v` → the two tests FAIL.

- [ ] **Step 3: Implement.** In `hooks.json`, append a second group to the `UserPromptSubmit` array, after the `context_nudge.py` group:

```json
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/jev_triage.py\"",
            "timeout": 3
          }
        ]
      }
```

In `plugin.json`, set `"version": "0.4.0"` and insert `opt-in jev triage pilot (CLAUDE_KIT_JEV), ` into `description` before `worktree audit`.

- [ ] **Step 4: Verify.** `python -c "import json;json.load(open('plugin/hooks/hooks.json'))"`, then `pytest` (full, including `test_hook_commands_reference_existing_scripts`) and ruff.

- [ ] **Step 5: Commit.**

```bash
git add plugin/hooks/hooks.json plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py
git commit -m "Register the jev triage hook; plugin 0.4.0

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: jev-eval.py: transcript extraction, `replay` and `score`

**Files:**
- Create: `plugin/scripts/jev-eval.py`
- Create: `tests/test_jev_eval.py`

**Interfaces:**
- Consumes: `jev_triage.KEYS`, `clean`, `should_judge`, `judge`, `JevError`, `jev_dir`, `thresholds`.
- Produces (module loaded as `jev_eval`): `projects_dir() -> Path`; `read_jsonl(path) -> Iterator[dict]`; `typed_text(record) -> str | None`; `prompt_text(record) -> str | None`; `iter_prompts(files) -> Iterator[tuple[str, str]]` yielding `(project_dir_name, text)`; `sample(prompts, n, seed) -> list[tuple[str, str]]`; `percentile(values, pct) -> float | None`; `parse_label(value) -> int | None`; `confusion(rows, key, threshold) -> Confusion`; `main(argv) -> int`.
- `labels.csv` columns: `id, project, prompt, s_underspecified, s_new_feature, s_key_decision, latency_ms, input_tokens, output_tokens, label_underspecified, label_new_feature, label_key_decision` (UTF-8 with BOM, so Excel opens it cleanly).

- [ ] **Step 1: Write the failing tests** in `tests/test_jev_eval.py`:

```python
import csv
import json

import pytest

from helpers import PLUGIN, load_module

ev = load_module(PLUGIN / "scripts" / "jev-eval.py", "jev_eval")
triage = ev.triage


def user(content, **extra):
    return {"type": "user", "message": {"role": "user", "content": content}, **extra}


def write_jsonl(path, records, junk=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r) for r in records]
    if junk:
        lines.insert(1, "{not json")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


FIXTURE = [
    user("add a dark mode toggle to settings"),
    user([{"type": "tool_result", "tool_use_id": "x", "content": "ok"}],
         toolUseResult={}),
    user([{"type": "text", "text": "Caveat: meta"}], isMeta=True),
    user("<command-name>/clear</command-name>"),
    user("lgtm"),
    user([{"type": "text",
           "text": "why does the login test fail <system-reminder>x</system-reminder>"}]),
    user("a sidechain prompt here", isSidechain=True),
]  # fmt: skip


def test_iter_prompts_keeps_only_typed_prompts(tmp_path):
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", FIXTURE, junk=True)
    assert list(ev.iter_prompts([path])) == [
        ("proj-a", "add a dark mode toggle to settings"),
        ("proj-a", "why does the login test fail"),
    ]


def test_sample_is_stratified_and_deduplicated():
    prompts = [("a", "p1 x y"), ("a", "p1 x y"), ("a", "p2 x y"), ("b", "q1 x y")]
    three = ev.sample(prompts, 3, 0)
    assert len(three) == 3
    assert len({t for _, t in three}) == 3
    assert {p for p, _ in ev.sample(prompts, 2, 0)} == {"a", "b"}


def fake(prompt):
    return triage.Judgment(
        {"underspecified": 0.1, "new_feature": 0.9, "key_decision": 0.2},
        {"input_tokens": 10, "output_tokens": 3, "model": "jev-test"},
    )


@pytest.fixture
def dirs(monkeypatch, tmp_path):
    projects = tmp_path / "projects"
    monkeypatch.setattr(ev, "projects_dir", lambda: projects)
    monkeypatch.setattr(triage, "jev_dir", lambda: tmp_path / "jev")
    for name in ("CLAUDE_KIT_JEV_T_UNDERSPECIFIED", "CLAUDE_KIT_JEV_T_NEW_FEATURE",
                 "CLAUDE_KIT_JEV_T_KEY_DECISION"):
        monkeypatch.delenv(name, raising=False)
    return projects, tmp_path / "jev"  # fmt: skip


def test_replay_writes_labels(monkeypatch, dirs):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", FIXTURE)
    monkeypatch.setattr(triage, "judge", fake)
    assert ev.main(["replay", "--n", "5"]) == 0
    with (jev / "labels.csv").open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["s_new_feature"] == "0.9000"
    assert rows[0]["input_tokens"] == "10"
    assert rows[0]["label_new_feature"] == ""
    assert ev.main(["replay"]) == 1
    assert ev.main(["replay", "--force"]) == 0


def test_replay_stops_on_missing_key(monkeypatch, dirs):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", FIXTURE)

    def no_key(prompt):
        raise triage.JevError("missing_key")

    monkeypatch.setattr(triage, "judge", no_key)
    assert ev.main(["replay"]) == 1
    assert not (jev / "labels.csv").exists()


HEADER = [
    "id", "project", "prompt", "s_underspecified", "s_new_feature",
    "s_key_decision", "latency_ms", "input_tokens", "output_tokens",
    "label_underspecified", "label_new_feature", "label_key_decision",
]  # fmt: skip


def labels_csv(path, nf_labels, latencies=(100, 150, 200, 250, 300),
               label_fmt=str, bom=False):
    su = [0.9, 0.1, 0.1, 0.1, 0.8]
    lu = [1, 0, 0, 0, 1]
    sn = [0.9, 0.8, 0.7, 0.3, 0.2]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig" if bom else "utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for i in range(5):
            w.writerow([i + 1, "p", f"prompt {i}", su[i], sn[i], 0.5, latencies[i],
                        10, 3, label_fmt(lu[i]), label_fmt(nf_labels[i]), ""])
        if bom:
            w.writerow([""] * len(HEADER))
    return path  # fmt: skip


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def test_confusion_math(tmp_path):
    rows = read_rows(labels_csv(tmp_path / "l.csv", [1, 1, 0, 1, 0]))
    c = ev.confusion(rows, "new_feature", 0.65)
    assert (c.tp, c.fp, c.fn, c.tn, c.skipped) == (2, 1, 1, 1, 0)
    assert c.precision == pytest.approx(2 / 3)
    assert c.recall == pytest.approx(2 / 3)
    assert ev.confusion(rows, "key_decision", 0.65).skipped == 5


def test_score_gate_fails_on_precision(tmp_path, dirs, capsys):
    path = labels_csv(tmp_path / "l.csv", [1, 1, 0, 1, 0])
    assert ev.main(["score", str(path)]) == 1
    out = capsys.readouterr().out
    assert "Replay gate: FAIL" in out
    assert "new_feature precision 0.67 < 0.8" in out


def test_score_gate_passes(tmp_path, dirs, capsys):
    path = labels_csv(tmp_path / "l.csv", [1, 1, 1, 0, 0])
    assert ev.main(["score", str(path)]) == 0
    out = capsys.readouterr().out
    assert "Replay gate: PASS" in out
    assert "p95 300 ms" in out


def test_score_gate_fails_on_latency(tmp_path, dirs, capsys):
    path = labels_csv(tmp_path / "l.csv", [1, 1, 1, 0, 0],
                      latencies=(100, 150, 200, 250, 900))  # fmt: skip
    assert ev.main(["score", str(path)]) == 1
    assert "p95 latency 900 ms > 500" in capsys.readouterr().out


def test_score_tolerates_excel_edits(tmp_path, dirs):
    path = labels_csv(tmp_path / "l.csv", [1, 1, 1, 0, 0], bom=True,
                      label_fmt=lambda v: f" {v}.0 ")  # fmt: skip
    rows = read_rows(path)
    c = ev.confusion(rows, "new_feature", 0.65)
    assert (c.tp, c.fp, c.fn, c.tn) == (3, 0, 0, 2)
    assert ev.main(["score", str(path)]) == 0
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_eval.py -v` → FAIL (file missing).

- [ ] **Step 3: Implement** `plugin/scripts/jev-eval.py`. The `report` subcommand is added in Task 6; its parser entry is added here so the CLI stays stable.

```python
#!/usr/bin/env python3
"""Evaluate the jev triage pilot.

  replay [--n 60] [--seed 0] [--force]  sample past prompts, judge, write labels.csv
  score [labels.csv]                    precision/recall vs your labels; Replay gate
  report [--since YYYY-MM-DD]           shadow vs active outcomes from the hook log

Outputs go to ~/.claude/claude-kit/jev/. replay needs typesafe-sdk and
TYPESAFE_API_KEY. Spec: docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hooks"))

import jev_triage as triage  # noqa: E402

GATE_KEYS = ("underspecified", "new_feature")
GATE_PRECISION = 0.8
GATE_RECALL = 0.6
GATE_P95_MS = 500
SWEEP = [round(0.50 + 0.05 * i, 2) for i in range(9)]


def projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                yield record


def typed_text(record: dict) -> str | None:
    """Cleaned text of a prompt the user typed; None for anything else."""
    if (
        record.get("type") != "user"
        or record.get("isMeta")
        or record.get("isSidechain")
        or "toolUseResult" in record
    ):
        return None
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        blocks = [b for b in content if isinstance(b, dict)]
        if any(b.get("type") == "tool_result" for b in blocks):
            return None
        text = "\n".join(str(b.get("text", "")) for b in blocks if b.get("type") == "text")
    else:
        return None
    text = triage.clean(text)
    if not text or text.startswith("<"):
        return None
    return text


def prompt_text(record: dict) -> str | None:
    """Typed text the hook would judge."""
    text = typed_text(record)
    return text if text and triage.should_judge(text) else None


def iter_prompts(files: Iterable[Path]) -> Iterator[tuple[str, str]]:
    for path in files:
        for record in read_jsonl(path):
            text = prompt_text(record)
            if text:
                yield path.parent.name, text


def sample(prompts: list[tuple[str, str]], n: int, seed: int) -> list[tuple[str, str]]:
    """Up to n distinct prompts, round-robin across projects."""
    rng = random.Random(seed)
    groups: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    for project, text in prompts:
        if text not in seen:
            seen.add(text)
            groups[project].append(text)
    for texts in groups.values():
        rng.shuffle(texts)
    order = sorted(groups)
    rng.shuffle(order)
    chosen: list[tuple[str, str]] = []
    while len(chosen) < n and any(groups[p] for p in order):
        for project in order:
            if groups[project] and len(chosen) < n:
                chosen.append((project, groups[project].pop()))
    return chosen


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile; None for no values."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(pct / 100 * len(ordered)) - 1)]


def parse_label(value: object) -> int | None:
    try:
        number = float(str(value).strip())
    except ValueError:
        return None
    return int(number) if number in (0.0, 1.0) else None


def parse_score(value: object) -> float | None:
    try:
        return float(str(value).strip())
    except ValueError:
        return None


@dataclass
class Confusion:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    skipped: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0


def confusion(rows: list[dict], key: str, threshold: float) -> Confusion:
    c = Confusion()
    for row in rows:
        label = parse_label(row.get(f"label_{key}", ""))
        score = parse_score(row.get(f"s_{key}", ""))
        if label is None or score is None:
            c.skipped += 1
            continue
        predicted = score >= threshold
        if predicted and label:
            c.tp += 1
        elif predicted:
            c.fp += 1
        elif label:
            c.fn += 1
        else:
            c.tn += 1
    return c


LABEL_FIELDS = [
    "id",
    "project",
    "prompt",
    *(f"s_{k}" for k in triage.KEYS),
    "latency_ms",
    "input_tokens",
    "output_tokens",
    *(f"label_{k}" for k in triage.KEYS),
]


def cmd_replay(args: argparse.Namespace) -> int:
    out = triage.jev_dir() / "labels.csv"
    if out.exists() and not args.force:
        print(f"{out} exists; pass --force to overwrite", file=sys.stderr)
        return 1
    files = sorted(projects_dir().glob("*/*.jsonl"))
    chosen = sample(list(iter_prompts(files)), args.n, args.seed)
    rows = []
    for i, (project, text) in enumerate(chosen, 1):
        start = time.perf_counter()
        try:
            judgment = triage.judge(text)
        except triage.JevError as exc:
            if exc.code in ("missing_key", "missing_sdk"):
                print(f"cannot judge: {exc.code}", file=sys.stderr)
                return 1
            print(f"prompt {i}: {exc.code}", file=sys.stderr)
            judgment = triage.Judgment({}, None)
        usage = judgment.usage or {}
        rows.append(
            {
                "id": i,
                "project": project,
                "prompt": text,
                **{
                    f"s_{k}": f"{judgment.scores[k]:.4f}" if k in judgment.scores else ""
                    for k in triage.KEYS
                },
                "latency_ms": round((time.perf_counter() - start) * 1000),
                "input_tokens": usage.get("input_tokens") or "",
                "output_tokens": usage.get("output_tokens") or "",
                **{f"label_{k}": "" for k in triage.KEYS},
            }
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} prompts to {out}")
    print("fill the label_* columns with 1 or 0, then run: jev-eval.py score")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    path = Path(args.labels) if args.labels else triage.jev_dir() / "labels.csv"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if any((v or "").strip() for v in r.values())]
    limits = triage.thresholds()
    failures: list[str] = []
    for key in triage.KEYS:
        c = confusion(rows, key, limits[key])
        print(
            f"{key}: threshold {limits[key]:.2f}  precision {c.precision:.2f}  "
            f"recall {c.recall:.2f}  f1 {c.f1:.2f}  "
            f"(labelled {len(rows) - c.skipped}, unlabelled {c.skipped})"
        )
        sweep = []
        for t in SWEEP:
            s = confusion(rows, key, t)
            sweep.append(f"{t:.2f} P{s.precision:.2f} R{s.recall:.2f}")
        print("  sweep: " + " | ".join(sweep))
        if key in GATE_KEYS:
            if c.precision < GATE_PRECISION:
                failures.append(f"{key} precision {c.precision:.2f} < {GATE_PRECISION}")
            if c.recall < GATE_RECALL:
                failures.append(f"{key} recall {c.recall:.2f} < {GATE_RECALL}")
    judged = [r for r in rows if parse_score(r.get("s_new_feature", "")) is not None]
    latencies = [v for r in judged if (v := parse_score(r.get("latency_ms", ""))) is not None]
    p50, p95 = percentile(latencies, 50), percentile(latencies, 95)
    tokens_in = sum(int(parse_score(r.get("input_tokens", "")) or 0) for r in judged)
    tokens_out = sum(int(parse_score(r.get("output_tokens", "")) or 0) for r in judged)
    if p95 is None:
        failures.append("no judged rows")
    else:
        print(
            f"latency p50 {p50:.0f} ms, p95 {p95:.0f} ms over {len(judged)} calls; "
            f"tokens in {tokens_in} / out {tokens_out} "
            "(cost = calls x the per-evaluation price on the TypeSafe dashboard)"
        )
        if p95 > GATE_P95_MS:
            failures.append(f"p95 latency {p95:.0f} ms > {GATE_P95_MS}")
    if failures:
        print("Replay gate: FAIL: " + "; ".join(failures))
        return 1
    print("Replay gate: PASS")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    print("report is not implemented yet", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    replay = sub.add_parser("replay", help="judge a sample of past prompts")
    replay.add_argument("--n", type=int, default=60)
    replay.add_argument("--seed", type=int, default=0)
    replay.add_argument("--force", action="store_true")
    score = sub.add_parser("score", help="score labels.csv against the gate")
    score.add_argument("labels", nargs="?")
    report = sub.add_parser("report", help="shadow vs active outcomes")
    report.add_argument("--since", default="")
    args = parser.parse_args(argv)
    handler = {"replay": cmd_replay, "score": cmd_score, "report": cmd_report}
    return handler[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verify.** `pytest tests/test_jev_eval.py -v` → PASS; full `pytest`, `ruff format plugin tests`, ruff check.

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-eval.py tests/test_jev_eval.py
git commit -m "jev-eval: replay past prompts and score labels against the gate

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: jev-eval.py `report`

**Files:**
- Modify: `plugin/scripts/jev-eval.py` (replace the `cmd_report` stub; add helpers above it)
- Modify: `tests/test_jev_eval.py` (append)

**Interfaces:**
- Consumes: `read_jsonl`, `typed_text`, `percentile`, `triage.KEYS`, `triage.jev_dir`, `projects_dir`.
- Produces: `Outcome(asked: bool, preflight: bool | None, corrected: bool)`; `collect(records) -> tuple[list[tuple[dict, Outcome]], dict[str, int]]` (matched pairs and tokens per session); `turns(path) -> list[tuple[str, list[dict], str | None]]`; `outcome(assistant_records, next_prompt) -> Outcome`; `match(records, session_turns) -> list[tuple[dict, Outcome]]`; `summarize(records, matched, tokens) -> dict[str, dict]`; `session_tokens(path) -> int`.

- [ ] **Step 1: Write the failing tests** by appending to `tests/test_jev_eval.py`:

```python
def assistant(*blocks):
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 0,
             "cache_read_input_tokens": 90}
    return {"type": "assistant", "message": {"content": list(blocks), "usage": usage}}  # fmt: skip


def say(text):
    return {"type": "text", "text": text}


def tool(name, **inp):
    return {"type": "tool_use", "id": f"{name}-{len(inp)}", "name": name, "input": inp}


P1 = "add a dark mode toggle to settings"
P2 = "no, use the existing theme module"
P3 = "make the thing better somehow please"
P4 = "ok go ahead with option one"
SESSION = [
    user(P1),
    assistant(say("On it."), tool("Edit", file_path="a.py")),
    user(P2),
    assistant(tool("Bash", command="git branch --show-current"),
              tool("Write", file_path="b.py")),
    user(P3),
    assistant(tool("AskUserQuestion", questions=[])),
    user(P4),
    assistant(say("Done. Anything else?")),
]  # fmt: skip


def log_record(session, mode, prompt, fired=(), error=None, ts="2026-09-28T10:00:00"):
    return {"ts": ts, "session_id": session, "project": "proj-a", "mode": mode,
            "prompt": prompt, "scores": None if error else {"new_feature": 0.5},
            "thresholds": {}, "fired": list(fired), "injected": bool(fired),
            "latency_ms": 200, "usage": None, "error": error}  # fmt: skip


def test_turns_and_outcomes(tmp_path):
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", SESSION, junk=True)
    result = ev.turns(path)
    assert [t[0] for t in result] == [P1, P2, P3, P4]
    o1, o2, o3, o4 = (ev.outcome(a, nxt) for _, a, nxt in result)
    assert (o1.asked, o1.preflight, o1.corrected) == (False, False, True)
    assert (o2.preflight, o2.corrected) == (True, False)
    assert o3.asked is True and o3.preflight is None
    assert o4.asked is True and o4.corrected is False


def test_report_end_to_end(dirs, capsys):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", SESSION, junk=True)
    records = [
        log_record("s1", "active", P1, ["new_feature"], ts="2026-09-28T10:00:01"),
        log_record("s1", "active", P2, ts="2026-09-28T10:00:02"),
        log_record("s1", "active", P3, ["underspecified"], ts="2026-09-28T10:00:03"),
        log_record("s1", "active", P4, ts="2026-09-28T10:00:04"),
        log_record("s1", "active", "never typed here", error="timeout",
                   ts="2026-09-28T10:00:05"),
        log_record("s2-missing", "shadow", P1, ["key_decision"]),
    ]  # fmt: skip
    write_jsonl(jev / "log.jsonl", records)

    matched, tokens = ev.collect(records)
    stats = ev.summarize(records, matched, tokens)
    active = stats["active"]
    assert active["logged"] == 5
    assert active["matched"] == 4
    assert active["error_rate"] == pytest.approx(0.2)
    assert active["fire_share"]["new_feature"] == pytest.approx(0.25)
    assert active["convention_miss_rate"] == pytest.approx(0.5)
    assert active["correction_rate"] == pytest.approx(0.25)
    assert active["median_tokens"] == 400
    assert stats["shadow"]["matched"] == 0
    assert stats["shadow"]["convention_miss_rate"] is None

    assert ev.main(["report"]) == 0
    out = capsys.readouterr().out
    assert "active" in out and "shadow" in out
    spot = read_rows(jev / "spotcheck.csv")
    assert [r["prompt"] for r in spot] == [P1, P3]
    assert ev.main(["report", "--since", "2026-09-29"]) == 1
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_eval.py -v` → the two new tests FAIL (`AttributeError: ... 'turns'`).

- [ ] **Step 3: Implement.** Add `import importlib.util`, `import re` and `import statistics` to the imports, then replace the `cmd_report` stub with:

```python
CORRECTION_RE = re.compile(
    r"^\s*(?:no\b|don['’]?t\b|do not\b|actually\b|stop\b|wait\b|that['’]?s not\b)",
    re.I,
)
CHECK_RE = re.compile(r"git\s+branch\s+--show-current|git\s+fetch")
SESSION_RE = re.compile(r"[\w-]+")
SPOTCHECK_FIELDS = [
    "session_id", "mode", "prompt", "fired", "asked", "preflight", "corrected",
    "false_alarm",
]  # fmt: skip


@dataclass
class Outcome:
    asked: bool
    preflight: bool | None  # None: the turn made no Write/Edit
    corrected: bool


def turns(path: Path) -> list[tuple[str, list[dict], str | None]]:
    """(typed prompt, assistant records until the next typed prompt, next prompt)."""
    out: list[tuple[str, list[dict], str | None]] = []
    current: str | None = None
    bucket: list[dict] = []
    for record in read_jsonl(path):
        text = typed_text(record)
        if text is not None:
            if current is not None:
                out.append((current, bucket, text))
            current, bucket = text, []
        elif current is not None and record.get("type") == "assistant":
            bucket.append(record)
    if current is not None:
        out.append((current, bucket, None))
    return out


def outcome(assistant: list[dict], next_prompt: str | None) -> Outcome:
    asked = False
    checked = False
    preflight: bool | None = None
    last_text = ""
    for record in assistant:
        content = (record.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                last_text = str(block.get("text", ""))
            elif block.get("type") == "tool_use":
                name = block.get("name")
                command = str((block.get("input") or {}).get("command", ""))
                if name == "AskUserQuestion":
                    asked = True
                elif name in ("Bash", "PowerShell") and CHECK_RE.search(command):
                    checked = True
                elif name in ("Write", "Edit") and preflight is None:
                    preflight = checked
    asked = asked or last_text.rstrip().endswith("?")
    corrected = bool(next_prompt and CORRECTION_RE.match(next_prompt))
    return Outcome(asked, preflight, corrected)


def match(
    records: list[dict], session_turns: list[tuple[str, list[dict], str | None]]
) -> list[tuple[dict, Outcome]]:
    """Pair log records (in time order) with transcript turns by prompt text."""
    out: list[tuple[dict, Outcome]] = []
    start = 0
    for record in records:
        k = start
        while k < len(session_turns) and session_turns[k][0] != record.get("prompt"):
            k += 1
        if k == len(session_turns):
            continue
        _, assistant, next_prompt = session_turns[k]
        out.append((record, outcome(assistant, next_prompt)))
        start = k + 1
    return out


def load_token_report():
    spec = importlib.util.spec_from_file_location(
        "token_report", HERE / "token-report.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def session_tokens(path: Path) -> int:
    report = load_token_report().scan([path])
    return sum(report.contexts[0]) if report.contexts else 0


def transcript_for(session_id: object) -> Path | None:
    if not isinstance(session_id, str) or not SESSION_RE.fullmatch(session_id):
        return None
    return next(projects_dir().glob(f"*/{session_id}.jsonl"), None)


def collect(records: list[dict]) -> tuple[list[tuple[dict, Outcome]], dict[str, int]]:
    by_session: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_session[str(record.get("session_id"))].append(record)
    matched: list[tuple[dict, Outcome]] = []
    tokens: dict[str, int] = {}
    for session_id, recs in by_session.items():
        path = transcript_for(session_id)
        if path is None:
            continue
        recs.sort(key=lambda r: str(r.get("ts", "")))
        matched += match(recs, turns(path))
        tokens[session_id] = session_tokens(path)
    return matched, tokens


def ratio(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def summarize(
    records: list[dict], matched: list[tuple[dict, Outcome]], tokens: dict[str, int]
) -> dict[str, dict]:
    stats: dict[str, dict] = {}
    for mode in ("shadow", "active"):
        recs = [r for r in records if r.get("mode") == mode]
        if not recs:
            continue
        judged = [r for r in recs if r.get("scores")]
        pairs = [(r, o) for r, o in matched if r.get("mode") == mode]
        applicable = misses = 0
        for record, result in pairs:
            keys = set(record.get("fired") or [])
            if "new_feature" in keys and result.preflight is not None:
                applicable += 1
                misses += not result.preflight
            if keys & {"underspecified", "key_decision"}:
                applicable += 1
                misses += not result.asked
        session_totals = [
            tokens[s] for s in {str(r.get("session_id")) for r in recs} if s in tokens
        ]
        latencies = [r["latency_ms"] for r in judged if isinstance(r.get("latency_ms"), int)]
        stats[mode] = {
            "logged": len(recs),
            "matched": len(pairs),
            "error_rate": ratio(sum(1 for r in recs if r.get("error")), len(recs)),
            "fire_share": {
                k: ratio(sum(1 for r in judged if k in (r.get("fired") or [])), len(judged))
                for k in triage.KEYS
            },
            "convention_miss_rate": ratio(misses, applicable),
            "correction_rate": ratio(sum(1 for _, o in pairs if o.corrected), len(pairs)),
            "median_tokens": statistics.median(session_totals) if session_totals else None,
            "latency_p50": percentile(latencies, 50),
            "latency_p95": percentile(latencies, 95),
        }
    return stats


def fmt(value: float | None, pct: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0%}" if pct else f"{value:.0f}"


def render(stats: dict[str, dict]) -> str:
    lines = []
    for mode, s in stats.items():
        shares = ", ".join(f"{k} {fmt(v, True)}" for k, v in s["fire_share"].items())
        lines += [
            f"{mode}: {s['logged']} prompts logged, {s['matched']} matched to transcripts",
            f"  fired: {shares}",
            f"  convention misses per applicable check: "
            f"{fmt(s['convention_miss_rate'], True)}",
            f"  correction rate: {fmt(s['correction_rate'], True)}",
            f"  median tokens per session: {fmt(s['median_tokens'])}",
            f"  latency p50 {fmt(s['latency_p50'])} ms, p95 {fmt(s['latency_p95'])} ms; "
            f"errors {fmt(s['error_rate'], True)}",
        ]
    return "\n".join(lines)


def read_log(since: str) -> list[dict]:
    path = triage.jev_dir() / "log.jsonl"
    if not path.exists():
        return []
    return [r for r in read_jsonl(path) if str(r.get("ts", ""))[:10] >= since]


def cmd_report(args: argparse.Namespace) -> int:
    records = read_log(args.since)
    if not records:
        print(f"no log records{' since ' + args.since if args.since else ''}")
        return 1
    matched, tokens = collect(records)
    print(render(summarize(records, matched, tokens)))
    fired_pairs = [(r, o) for r, o in matched if r.get("fired")]
    chosen = random.Random(0).sample(fired_pairs, min(20, len(fired_pairs)))
    chosen.sort(key=lambda pair: str(pair[0].get("ts", "")))
    out = triage.jev_dir() / "spotcheck.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SPOTCHECK_FIELDS)
        writer.writeheader()
        for record, result in chosen:
            writer.writerow(
                {
                    "session_id": record.get("session_id"),
                    "mode": record.get("mode"),
                    "prompt": record.get("prompt"),
                    "fired": " ".join(record.get("fired") or []),
                    "asked": result.asked,
                    "preflight": "n/a" if result.preflight is None else result.preflight,
                    "corrected": result.corrected,
                    "false_alarm": "",
                }
            )
    print(f"spot-check {len(chosen)} fired prompts in {out} (fill false_alarm 1/0)")
    return 0
```

- [ ] **Step 4: Verify.** `pytest tests/test_jev_eval.py -v` → PASS; full `pytest`, `ruff format plugin tests`, ruff check.

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-eval.py tests/test_jev_eval.py
git commit -m "jev-eval: report shadow vs active outcomes from the hook log

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: ADR 0012, README, spec and plan status

**Files:**
- Create: `knowledge/decisions/0012-jev-triage-pilot.md`
- Modify: `knowledge/decisions/README.md` (add the index row after 0011)
- Modify: `README.md` (plugin bullet mentions the hook; new `## Trying jev (opt-in pilot)` section before `## Scope`)
- Modify: `docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md` (Status → `implemented`; apply the four refinements listed at the top of this plan)
- Modify: `docs/superpowers/plans/2026-09-28-jev-triage-pilot.md` (Status → `implemented`)

- [ ] **Step 1: Write the ADR** `knowledge/decisions/0012-jev-triage-pilot.md`:

```markdown
# ADR 0012: jev triage pilot is an opt-in third-party judge

- **Status:** accepted
- **Date:** 2026-09-28
- **Spec:** `docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md`

## Context
TypeSafe AI's jev returns calibrated yes/no probabilities for several
questions in one fast call. The kit cannot use it to replace model calls
(Claude Code owns the loop), but a `UserPromptSubmit` hook can judge each
prompt and add a hint when a workspace rule (pre-flight branch check, verify
key decisions) is likely to apply. Doing so sends prompt text to a third-party
API, and nothing yet shows that it helps.

## Decision
- The hook `plugin/hooks/jev_triage.py` is off unless `CLAUDE_KIT_JEV` is
  `shadow` (judge and log) or `active` (also add hints). Prompts leave the
  machine only in those modes.
- It calls the official `typesafe-sdk` directly (optional per-machine install),
  not `judgment-base-agent`, whose Google ADK and pandas imports are too slow
  for a per-prompt hook. OpenRouter's `typesafe/jev-router` returns
  completions, not judgments, so it cannot drive this.
- Judgments are logged locally to `~/.claude/claude-kit/jev/log.jsonl`, never
  in a repository.
- The pilot advances only through the spec's gates (replay, then shadow, then
  active), measured with `plugin/scripts/jev-eval.py`. A failed gate ends it.
  The outcome is appended to this ADR.

## Consequences
- With the flag unset the kit behaves exactly as before.
- In `shadow`/`active`, each prompt of 3+ words costs one jev evaluation and up
  to 1.5 s; failures are logged and the prompt passes unchanged (ADR 0007).

## Outcome
Pending: replay gate not yet run.
```

- [ ] **Step 2: Add the index row** to `knowledge/decisions/README.md`, after the 0011 row:

```markdown
| [0012](0012-jev-triage-pilot.md) | jev triage pilot is an opt-in third-party judge | accepted | 2026-09-28 |
```

- [ ] **Step 3: README.** In the `plugin/` bullet, change "and six hooks (" to "seven hooks (" and add "an opt-in jev triage of each prompt;" to the list of hooks. Insert before `## Scope`:

````markdown
## Trying jev (opt-in pilot)

An experiment: [jev](https://typesafe.ai), a fast "System One" judge, scores
each prompt (underspecified? new feature? key decision?) and, in `active`
mode, adds a one-line hint for Claude. It is **off by default**; see
[ADR 0012](knowledge/decisions/0012-jev-triage-pilot.md) and the
[spec](docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md).

```
pip install "typesafe-sdk>=0.7"          # once per machine
setx TYPESAFE_API_KEY <key>              # new terminals pick it up
python plugin/scripts/jev-eval.py replay # 1. score ~60 past prompts
#    fill label_* in ~/.claude/claude-kit/jev/labels.csv with 1/0
python plugin/scripts/jev-eval.py score  # Replay gate PASS/FAIL
setx CLAUDE_KIT_JEV shadow               # 2. log only, 1-2 weeks
setx CLAUDE_KIT_JEV active               # 3. add hints, 1-2 weeks
python plugin/scripts/jev-eval.py report --since 2026-10-01
setx CLAUDE_KIT_JEV off                  # stop
```

Judgments are logged to `~/.claude/claude-kit/jev/log.jsonl`; prompts go to
TypeSafe only while the flag is `shadow` or `active`.
````

- [ ] **Step 4: Update the spec** `docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md`:
  - `- **Status:** draft` → `- **Status:** implemented`.
  - Data flow step 3 → `Otherwise clean the prompt (strip <system-reminder> and <pasted_content …> blocks); if the cleaned text is empty, starts with / or <, or has fewer than 3 words, exit 0 without calling jev.`
  - In **Client**, replace `` `judge(prompt: str) -> dict[str, float]` `` with `` `judge(prompt: str) -> Judgment` (scores and usage) ``, and replace the "first implementation step is a short spike…" paragraph with: `Confirmed against typesafe-sdk 0.7.2: sync TypeSafeClient(timeout=1.5, retry=RetryPolicy(max_retries=0)).system_one(state=prompt, questions={key: Noul(instructions=..., criteria={"true": ..., "false": ...})}) returning nouls[key].noul, usage and model.`
  - In **score**, replace `total and per-1k-call cost from usage if available` with `call count and token totals from usage (cost = calls × the per-evaluation price on the TypeSafe dashboard)`.
  - In **report**, append to the *preflight* bullet: `; n/a (excluded from the miss rate) when the turn made no Write/Edit`.
  - Set the plan's `- **Status:** draft` → `- **Status:** implemented`.

- [ ] **Step 5: Verify.** Full `pytest` (including `tests/test_docs.py`, which checks relative links), ruff. Then run `grep -rniF -e "$(git config user.name)" -e "$(git config user.email)" -e "$(whoami)" plugin tests knowledge README.md docs/superpowers` and expect no output.

- [ ] **Step 6: Commit.**

```bash
git add knowledge/decisions/0012-jev-triage-pilot.md knowledge/decisions/README.md README.md docs/superpowers
git commit -m "ADR 0012 and docs for the jev triage pilot; mark spec implemented

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Live smoke check (manual, needs the user's key)

Not automatable: CI has no `TYPESAFE_API_KEY`, and it must not get one. Run it after merge, once the key is set:

```powershell
pip install "typesafe-sdk>=0.7"
$env:TYPESAFE_API_KEY = "<key>"; $env:CLAUDE_KIT_JEV = "shadow"
'{"session_id":"smoke","cwd":"x","prompt":"add a dark mode toggle to settings"}' | python plugin/hooks/jev_triage.py
Get-Content ~/.claude/claude-kit/jev/log.jsonl -Tail 1
```

Expected: no stdout; the last log line has three `scores`, `error: null` and `latency_ms` under 1500.
