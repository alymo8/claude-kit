#!/usr/bin/env python3
"""Add the claude-kit status line to Claude Code user settings if none is set.

Usage: install-statusline.py [--settings PATH] [--skills-dir PATH]

Reads ``settings.json`` (default ``~/.claude/settings.json``; created as ``{}``
if missing). If it has no ``statusLine`` key, adds one pointing at
``<skills-dir>/claude-kit/scripts/statusline.py`` (the junction path, so it stays
valid if the checkout moves) and rewrites the file with two-space indentation.
Never overwrites an existing status line. Exit 1 if the file is not valid JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def install(settings: Path, skills_dir: Path) -> str:
    data: dict = {}
    if settings.exists():
        data = json.loads(settings.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings.json is not a JSON object")
    if "statusLine" in data:
        return "unchanged"
    script = (skills_dir / "claude-kit" / "scripts" / "statusline.py").as_posix()
    data["statusLine"] = {"type": "command", "command": f'python "{script}"'}
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return "added"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_settings = str(Path.home() / ".claude" / "settings.json")
    default_skills_dir = str(Path.home() / ".claude" / "skills")
    parser.add_argument("--settings", default=default_settings)
    parser.add_argument("--skills-dir", default=default_skills_dir)
    args = parser.parse_args(argv)
    settings = Path(args.settings)
    try:
        outcome = install(settings, Path(args.skills_dir))
    except ValueError as exc:
        print(f"[claude-kit] {settings}: {exc}; left unchanged", file=sys.stderr)
        return 1
    if outcome == "added":
        print(f"statusLine added to {settings}")
    else:
        print("statusLine already configured; left unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
