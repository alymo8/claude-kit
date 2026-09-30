#!/usr/bin/env python3
"""SessionStart hook: inject the token-discipline rule unless it is switched off.

On by default. CLAUDE_KIT_LEAN_CONTEXT=0 turns it off: nothing is printed. Any
other value, or none, counts as on. To also stop Claude invoking the skill,
deny ``Skill(claude-kit:lean-context)`` in settings. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import sys

RULE = (
    "Token discipline: the cost of a session is context size times turn count. "
    "Before exploring or running anything with long output, use the "
    "`claude-kit:lean-context` skill. Details: conventions/session-hygiene.md."
)


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_LEAN_CONTEXT") != "0"


def main() -> int:
    try:
        if enabled():
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": RULE,
                }
            }
            print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] lean-context inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
