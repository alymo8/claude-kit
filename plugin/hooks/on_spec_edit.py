#!/usr/bin/env python3
"""PostToolUse hook: re-render a spec or plan's HTML after its Markdown is written.

Reads the hook event JSON from stdin. If ``tool_input.file_path`` points at
``docs/superpowers/specs/*.md`` or ``docs/superpowers/plans/*.md``, runs the shared
renderer on that one file. Never opens a browser. Always exits 0: a hook must never
block work, so any failure is reported on stderr and otherwise swallowed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RENDERER = Path(__file__).resolve().parent.parent / "scripts" / "render-spec.py"
TARGET_RE = re.compile(r"docs/superpowers/(specs|plans)/[^/]+\.md$")


def target_from_event(raw: str) -> Path | None:
    """Return the spec/plan path named by a hook event, or None if not one."""
    try:
        event = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(event, dict):
        return None
    tool_input = event.get("tool_input")
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(file_path, str):
        return None
    if not TARGET_RE.search(file_path.replace("\\", "/")):
        return None
    return Path(file_path)


def main() -> int:
    try:
        target = target_from_event(sys.stdin.read())
        if target is None or not target.exists():
            return 0
        result = subprocess.run(
            [sys.executable, str(RENDERER), str(target)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(
                f"[claude-kit] render failed: {result.stderr.strip()}", file=sys.stderr
            )
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] on_spec_edit error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
