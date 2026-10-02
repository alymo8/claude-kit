#!/usr/bin/env python3
"""SessionStart hook: inject the spec-grill rule when it is switched on.

Off by default. CLAUDE_KIT_GRILL=1 turns it on; any other value, or none,
counts as off and nothing is printed. The ``claude-kit:grill`` skill stays
invocable either way. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import sys

RULE = (
    "Spec grill is on (CLAUDE_KIT_GRILL=1). When designing a spec, after "
    "presenting the design summary and before writing the spec, run the "
    "`claude-kit:grill` skill on the agreed design. Write the spec only after "
    "the user confirms a shared understanding, and give it a `## Coverage` "
    "section in the format the skill describes."
)


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_GRILL") == "1"


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
        print(f"[claude-kit] grill inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
