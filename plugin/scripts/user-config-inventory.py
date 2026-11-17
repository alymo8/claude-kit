#!/usr/bin/env python3
"""Print an inventory of the user-scope Claude Code setup as one JSON object.

Usage: user-config-inventory.py [--home DIR]

``--home`` defaults to the current user's home directory. The output has the
keys ``settings``, ``mcp_servers``, ``plugins``, ``skills``,
``scheduled_tasks``, ``instructions`` and ``errors``. Every item carries a
``file`` (a posix path relative to the home directory, or an absolute posix
path when the file lies outside it) and a 1-based ``line`` (``null`` when it is
not known).

Env and header values never appear in the output: only their key names.

A missing file or key yields an empty list (or ``null`` for a single-valued
field), never an error. A file that is not valid JSON adds an ``errors`` entry
``{file, error}`` and the rest still prints. The script exits 0, or 2 when
``--home`` is not a directory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from json.decoder import scanstring
from pathlib import Path

PERMISSION_KINDS = ("allow", "ask", "deny")
SETTINGS_FILES = (".claude/settings.json", ".claude/settings.local.json")
WHITESPACE = " \t\r\n"
SCALAR_RE = re.compile(r"-?\d+(\.\d+)?([eE][-+]?\d+)?|true|false|null")


def value_lines(text: str) -> dict[tuple[str | int, ...], int]:
    """Map each value's path (object keys and list indices) to the 1-based line
    where it starts; for an object member, the line of its key.

    Run only on text that ``json.loads`` accepted. A duplicate key keeps the
    last one, as ``json.loads`` does.
    """
    lines: dict[tuple[str | int, ...], int] = {}
    pos = 0
    line = 1

    def skip() -> None:
        nonlocal pos, line
        while pos < len(text) and text[pos] in WHITESPACE:
            if text[pos] == "\n":
                line += 1
            pos += 1

    def string() -> str:
        nonlocal pos, line
        value, end = scanstring(text, pos + 1)
        line += text.count("\n", pos, end)
        pos = end
        return value

    def value(path: tuple[str | int, ...]) -> None:
        nonlocal pos
        skip()
        char = text[pos]
        if char == "{":
            pos += 1
            skip()
            if text[pos] == "}":
                pos += 1
                return
            while True:
                skip()
                key_line = line
                key = string()
                lines[path + (key,)] = key_line
                skip()
                pos += 1  # ':'
                value(path + (key,))
                skip()
                if text[pos] == ",":
                    pos += 1
                    continue
                pos += 1  # '}'
                return
        if char == "[":
            pos += 1
            skip()
            if text[pos] == "]":
                pos += 1
                return
            index = 0
            while True:
                skip()
                lines[path + (index,)] = line
                value(path + (index,))
                skip()
                index += 1
                if text[pos] == ",":
                    pos += 1
                    continue
                pos += 1  # ']'
                return
        if char == '"':
            string()
            return
        match = SCALAR_RE.match(text, pos)
        if not match:
            raise ValueError(f"unexpected character at {pos}")
        pos = match.end()

    if text.startswith("﻿"):
        pos = 1
    value(())
    return lines


def rel(path: Path, home: Path) -> str:
    """Home-relative posix path when ``path`` is under ``home`` (compared on
    absolute paths, without resolving links), else the absolute posix path."""
    target = os.path.abspath(path)
    base = os.path.abspath(home)
    try:
        common = os.path.commonpath([os.path.normcase(target), os.path.normcase(base)])
    except ValueError:
        common = ""
    if common == os.path.normcase(base):
        return Path(os.path.relpath(target, base)).as_posix()
    return Path(target).as_posix()


def load_json(path: Path, home: Path, errors: list[dict]) -> tuple[object, dict] | None:
    """``(data, value_lines)`` for a JSON file, ``None`` when it is missing or
    does not parse (the latter also appends an ``errors`` entry)."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8-sig")
        data = json.loads(text)
        return data, value_lines(text)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        errors.append({"file": rel(path, home), "error": str(exc)})
        return None


def hooks_from(
    data: object, lines: dict, file: str, prefix: tuple = ("hooks",)
) -> list[dict]:
    """One item per hook command in a ``{"hooks": {event: [group]}}`` shape."""
    if not isinstance(data, dict):
        return []
    events = data.get("hooks")
    if not isinstance(events, dict):
        return []
    items = []
    for event, groups in events.items():
        if not isinstance(groups, list):
            continue
        for gi, group in enumerate(groups):
            if not isinstance(group, dict):
                continue
            matcher = group.get("matcher")
            hooks = group.get("hooks")
            if not isinstance(hooks, list):
                continue
            for hi, hook in enumerate(hooks):
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command")
                if not isinstance(command, str):
                    continue
                items.append(
                    {
                        "event": event,
                        "matcher": matcher if isinstance(matcher, str) else None,
                        "command": command,
                        "file": file,
                        "line": lines.get((*prefix, event, gi, "hooks", hi, "command")),
                    }
                )
    return items


def settings_item(data: object, lines: dict, file: str) -> dict:
    """The inventory of one settings file."""
    if not isinstance(data, dict):
        data = {}

    def at(*path: str | int) -> dict:
        return {"file": file, "line": lines.get(path)}

    permissions: list[dict] = []
    default_mode = None
    perms = data.get("permissions")
    if isinstance(perms, dict):
        for kind in PERMISSION_KINDS:
            rules = perms.get(kind)
            if not isinstance(rules, list):
                continue
            for i, rule in enumerate(rules):
                if isinstance(rule, str):
                    permissions.append(
                        {"kind": kind, "rule": rule, **at("permissions", kind, i)}
                    )
        mode = perms.get("defaultMode")
        if isinstance(mode, str):
            default_mode = {"value": mode, **at("permissions", "defaultMode")}

    env = data.get("env")
    env_items = (
        [{"key": key, **at("env", key)} for key in env] if isinstance(env, dict) else []
    )

    enabled = data.get("enabledPlugins")
    enabled_items = (
        [
            {"name": name, "enabled": value, **at("enabledPlugins", name)}
            for name, value in enabled.items()
        ]
        if isinstance(enabled, dict)
        else []
    )

    status_line = None
    status = data.get("statusLine")
    if isinstance(status, dict) and isinstance(status.get("command"), str):
        status_line = {"command": status["command"], **at("statusLine", "command")}

    auto_mode = None
    auto = data.get("autoMode")
    if isinstance(auto, dict):
        auto_mode = {"keys": list(auto), **at("autoMode")}

    return {
        "file": file,
        "permissions": permissions,
        "defaultMode": default_mode,
        "hooks": hooks_from(data, lines, file),
        "env": env_items,
        "enabledPlugins": enabled_items,
        "statusLine": status_line,
        "autoMode": auto_mode,
    }


def inventory(home: Path) -> dict:
    """The full inventory of the user-scope setup under ``home``."""
    errors: list[dict] = []
    settings = []
    for name in SETTINGS_FILES:
        loaded = load_json(home / name, home, errors)
        if loaded is not None:
            data, lines = loaded
            settings.append(settings_item(data, lines, name))
    return {
        "settings": settings,
        "mcp_servers": [],
        "plugins": [],
        "skills": [],
        "scheduled_tasks": [],
        "instructions": [],
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args(argv)
    home: Path = args.home
    if not home.is_dir():
        print(f"not a directory: {home}", file=sys.stderr)
        return 2
    print(json.dumps(inventory(home), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
