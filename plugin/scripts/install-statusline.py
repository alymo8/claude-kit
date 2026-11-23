#!/usr/bin/env python3
"""Add the agent-kit status line to Claude Code user settings if none is set.

Usage: install-statusline.py [--config-dir DIR] [--settings PATH]
                             [--skills-dir PATH] [--stable-copy]

Reads ``settings.json`` (default ``<config-dir>/settings.json``; created as
``{}`` if missing; ``<config-dir>`` is ``$CLAUDE_CONFIG_DIR``, else
``~/.claude``). With no ``statusLine`` key it adds one pointing at
``<skills-dir>/agent-kit/scripts/statusline.py`` (the link path, so it stays
valid if the checkout moves). With ``--stable-copy`` it instead copies
``statusline.py`` into the kit's state folder under ``<config-dir>`` (see
STATE_FOLDER) and points the line there, so it survives plugin updates;
rerunning refreshes that copy. A status line still pointing at the old link
is moved to the new target. Never overwrites any other status line. Exit 1 if
the file is not valid JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

LINK_NAME = "agent-kit"
LEGACY_LINK = "claude-kit"
STATE_FOLDER = "claude-kit"


def default_config_dir() -> Path:
    value = os.environ.get("CLAUDE_CONFIG_DIR", "")
    return Path(value) if value else Path.home() / ".claude"


def link_command(skills_dir: Path) -> str:
    script = (skills_dir / LINK_NAME / "scripts" / "statusline.py").as_posix()
    return f'python "{script}"'


def stable_command(config: Path) -> str:
    return f'python "{(config / STATE_FOLDER / "statusline.py").as_posix()}"'


def is_legacy(command: str, skills_dir: Path) -> bool:
    """True when `command` runs the status line through the old link."""
    old = (skills_dir / LEGACY_LINK / "scripts" / "statusline.py").as_posix()
    norm = command.replace("\\", "/").casefold()
    return old.replace("\\", "/").casefold() in norm


def install(settings: Path, skills_dir: Path, stable: Path | None = None) -> str:
    """'added', 'migrated', 'refreshed' or 'unchanged' (file untouched)."""
    data: dict = {}
    if settings.exists():
        data = json.loads(settings.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings.json is not a JSON object")
    target = stable_command(stable) if stable is not None else link_command(skills_dir)
    line = data.get("statusLine")
    command = line.get("command") if isinstance(line, dict) else None
    if "statusLine" not in data:
        outcome = "added"
    elif isinstance(command, str) and is_legacy(command, skills_dir):
        outcome = "migrated"
    elif stable is not None and command == target:
        outcome = "refreshed"
    else:
        return "unchanged"
    if stable is not None:
        folder = stable / STATE_FOLDER
        folder.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_name("statusline.py")
        shutil.copyfile(source, folder / "statusline.py")
    if outcome == "refreshed":
        return outcome
    data["statusLine"] = {"type": "command", "command": target}
    settings.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(tmp, settings)
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config-dir", default=None)
    parser.add_argument("--settings", default=None)
    parser.add_argument("--skills-dir", default=None)
    parser.add_argument(
        "--stable-copy",
        action="store_true",
        help="copy statusline.py into the state folder under --config-dir",
    )
    args = parser.parse_args(argv)
    config = Path(args.config_dir) if args.config_dir else default_config_dir()
    settings = Path(args.settings or config / "settings.json")
    skills_dir = Path(args.skills_dir or config / "skills")
    stable = config if args.stable_copy else None
    try:
        outcome = install(settings, skills_dir, stable)
    except (OSError, ValueError) as exc:
        print(f"[agent-kit] {settings}: {exc}; left unchanged", file=sys.stderr)
        return 1
    if outcome == "added":
        print(f"statusLine added to {settings}")
    elif outcome == "migrated":
        line = json.loads(settings.read_text(encoding="utf-8"))["statusLine"]
        print(f"statusLine moved to {line['command']} in {settings}")
    elif outcome == "refreshed":
        copy = config / STATE_FOLDER / "statusline.py"
        print(f"statusLine copy refreshed at {copy}")
    else:
        print("statusLine already configured; left unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
