#!/usr/bin/env python3
"""SessionEnd hook: refresh the branch's handoff file with the current git State.

Creates ``.claude/handoffs/<branch>.md`` (with the last few user prompts) when
none exists; otherwise replaces only its State section and Written line. Outside
a git repo it does nothing. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

import _transcript  # noqa: E402
import handoff  # noqa: E402


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            return 0
        cwd = Path(event.get("cwd") or Path.cwd())
        if handoff.work_tree(cwd) is None:
            return 0
        prompts: list[str] = []
        transcript = event.get("transcript_path")
        if isinstance(transcript, str):
            tail = _transcript.read_tail(Path(transcript))
            prompts = _transcript.recent_prompts(tail)
        handoff.snapshot(cwd, prompts)
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] handoff snapshot error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
