#!/usr/bin/env python3
"""PreCompact hook: steer the compaction summary toward what a restart needs.

Claude Code uses a PreCompact hook's plain stdout as instructions for the
compaction summary, so this prints one short instruction and nothing else. On
by default; CLAUDE_KIT_PRECOMPACT=0 prints nothing. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import os
import sys

INSTRUCTION = (
    "When summarising, keep: the approaches already tried and why each failed "
    "or was rejected, so they are not retried; open problems and unanswered "
    "questions; decisions the user confirmed; and the path of the branch "
    "handoff file if one exists."
)


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_PRECOMPACT") != "0"


def main() -> int:
    try:
        sys.stdin.read()
        if enabled():
            print(INSTRUCTION)
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] precompact error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
