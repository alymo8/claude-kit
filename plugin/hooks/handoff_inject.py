#!/usr/bin/env python3
"""SessionStart hook (startup|clear): inject the branch's recent handoff file.

Prints the handoff for the current branch when it is younger than seven days,
wrapped in a short header. Otherwise prints one line naming fresh handoffs for
other branches, or nothing. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import handoff  # noqa: E402

MAX_AGE_DAYS = 7
WRITTEN_RE = re.compile(r"^- \*\*Written:\*\* (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", re.M)
HEADER = (
    "Handoff from the previous session on this branch. Read it before "
    "exploring.\nThe State section was generated at session end; verify it "
    "against git before\ntrusting it."
)


def written_at(path: Path) -> datetime:
    match = WRITTEN_RE.search(path.read_text(encoding="utf-8"))
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M")
    return datetime.fromtimestamp(path.stat().st_mtime)


def age_text(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 0)}m"
    if minutes < 60 * 24:
        return f"{minutes // 60}h"
    return f"{minutes // (60 * 24)}d"


def render(cwd: Path, now: datetime) -> str:
    top = handoff.work_tree(cwd)
    if top is None:
        return ""
    folder = top / ".claude" / "handoffs"
    if not folder.is_dir():
        return ""
    limit = timedelta(days=MAX_AGE_DAYS)
    current = handoff.handoff_path(cwd)
    if current.exists() and now - written_at(current) <= limit:
        age = age_text(now - written_at(current))
        rel = current.relative_to(top).as_posix()
        body = current.read_text(encoding="utf-8").rstrip("\n")
        return f'<handoff age="{age}" path="{rel}">\n{HEADER}\n\n{body}\n</handoff>'
    others = []
    for path in sorted(folder.glob("*.md")):
        if path == current:
            continue
        delta = now - written_at(path)
        if delta <= limit:
            others.append(f"{path.stem} ({age_text(delta)})")
    if others:
        return "[claude-kit] Handoffs exist for other branches: " + ", ".join(others)
    return ""


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if isinstance(event, dict):
            cwd = Path(event.get("cwd") or Path.cwd())
        else:
            cwd = Path.cwd()
        text = render(cwd, datetime.now())
        if text:
            print(text)
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] handoff inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
