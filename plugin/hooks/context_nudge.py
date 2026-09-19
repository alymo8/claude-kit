#!/usr/bin/env python3
"""UserPromptSubmit hook: nudge once per context threshold crossed.

Reads the tail of the transcript, computes the context size after the last API
call (input + cache creation + cache read), and when it first passes
CLAUDE_KIT_NUDGE_AT (default 300000) and then every CLAUDE_KIT_NUDGE_STEP
(default 100000), prints a one-sentence nudge as additionalContext (for Claude)
and systemMessage (for the user). The highest threshold already fired is kept
in <scratchpad_dir>/claude-kit/nudge-level. The temp-dir fallback marker is
never deleted (ADR 0007); it is a few bytes per session. Always exits 0
(ADR 0007). The marker resets to 0 when context falls below the first
threshold, so the next crossing fires again after /compact or any context drop.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _transcript  # noqa: E402

DEFAULT_AT = 300_000
DEFAULT_STEP = 100_000


def next_level(tokens: int, fired: int, at: int, step: int) -> int | None:
    """Highest threshold at or below ``tokens`` that is above ``fired``, or None."""
    if tokens < at:
        return None
    level = at + ((tokens - at) // step) * step
    return level if level > fired else None


def message(tokens: int) -> str:
    return (
        f"Context is at {tokens // 1000}k tokens; every turn now re-sends all of "
        "it. At the next natural boundary, run /handoff and then /clear. "
        "(claude-kit session hygiene)"
    )


def level_file(event: dict) -> Path:
    scratch = event.get("scratchpad_dir")
    if isinstance(scratch, str) and scratch:
        return Path(scratch) / "claude-kit" / "nudge-level"
    session = str(event.get("session_id") or "unknown")
    return Path(tempfile.gettempdir()) / f"claude-kit-nudge-{session}"


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            return 0
        transcript = event.get("transcript_path")
        if not isinstance(transcript, str):
            return 0
        tokens = _transcript.last_usage_tokens(_transcript.read_tail(Path(transcript)))
        if not tokens:
            return 0
        marker = level_file(event)
        fired = 0
        if marker.exists():
            try:
                fired = int(marker.read_text(encoding="utf-8").strip() or 0)
            except ValueError:
                fired = 0
        at = env_int("CLAUDE_KIT_NUDGE_AT", DEFAULT_AT)
        if tokens < at and fired > 0:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("0", encoding="utf-8")
            return 0
        level = next_level(
            tokens,
            fired,
            at,
            env_int("CLAUDE_KIT_NUDGE_STEP", DEFAULT_STEP),
        )
        if level is None:
            return 0
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(level), encoding="utf-8")
        text = message(tokens)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": text,
                    },
                    "systemMessage": text,
                }
            )
        )
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] context nudge error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
