#!/usr/bin/env python3
"""Print an inventory of the user-scope Claude Code setup as one JSON object.

Usage: user-config-inventory.py [--home DIR]

``--home`` defaults to the current user's home directory. The output has the
keys ``settings``, ``mcp_servers``, ``plugins``, ``skills``,
``scheduled_tasks``, ``instructions`` and ``errors``. Every item carries a
``file`` (a posix path relative to the home directory, or an absolute posix
path when the file lies outside it) and a 1-based ``line`` (``null`` when it is
not known).

Env and header values never appear in the output: only their key names. Hook
and statusLine commands and MCP ``command``, ``args`` and ``url`` are masked by
``redact``: ``NAME=value`` and ``$env:NAME = value`` values, URL passwords, query
values and auth header values become ``***``.

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
SCALAR_RE = re.compile(r"-?\d+(\.\d+)?([eE][-+]?\d+)?|true|false|null|NaN|-?Infinity")
USERINFO_RE = re.compile(r"(://)([^/?#@\s:]*)(:[^/?#@\s]*)?@")
ASSIGN_RE = re.compile(
    r"""(?<![\w-])(-{0,2}[A-Za-z_][\w.-]*)=("[^"]*"|'[^']*'|[^\s&;#"']+)"""
)
HEADER_RE = re.compile(
    r"""(?i)\b(authorization|proxy-authorization|x-api-key|api-key)(\s*:\s*)"""
    r"""(?:(?:bearer|basic|token)\s+)?[^\s"']+"""
)
PS_ENV_RE = re.compile(r"""(\$env:[A-Za-z_]\w*\s*=\s*)("[^"]*"|'[^']*'|[^\s;&|"']+)""")
MASK = "***"


def redact(text: str) -> str:
    """Mask URL passwords, ``NAME=value`` and ``$env:NAME = value`` values, query
    values and auth header values; keep names."""
    text = HEADER_RE.sub(lambda m: f"{m[1]}{m[2]}{MASK}", text)
    text = PS_ENV_RE.sub(lambda m: f"{m[1]}{MASK}", text)
    text = USERINFO_RE.sub(
        lambda m: f"{m[1]}{m[2]}:{MASK}@" if m[3] else f"{m[1]}{MASK}@", text
    )
    return ASSIGN_RE.sub(lambda m: f"{m[1]}={MASK}", text)


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
    except (OSError, UnicodeDecodeError, ValueError, RecursionError) as exc:
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
                        "command": redact(command),
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
        status_line = {
            "command": redact(status["command"]),
            **at("statusLine", "command"),
        }

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


def string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def sorted_keys(value: object) -> list[str]:
    return sorted(value) if isinstance(value, dict) else []


def mcp_item(name: str, server: dict, scope: str, project: str | None, line) -> dict:
    command = string_or_none(server.get("command"))
    args = server.get("args")
    return {
        "name": name,
        "scope": scope,
        "project": project,
        "type": string_or_none(server.get("type")) or ("stdio" if command else None),
        "command": redact(command) if command else None,
        "args": [redact(a) for a in args if isinstance(a, str)]
        if isinstance(args, list)
        else [],
        "url": redact(url) if isinstance(url := server.get("url"), str) else None,
        "env_keys": sorted_keys(server.get("env")),
        "header_keys": sorted_keys(server.get("headers")),
        "file": ".claude.json",
        "line": line,
    }


def mcp_servers(home: Path, errors: list[dict]) -> list[dict]:
    """MCP servers of ``.claude.json``: user scope, then each project's."""
    loaded = load_json(home / ".claude.json", home, errors)
    if loaded is None or not isinstance(loaded[0], dict):
        return []
    data, lines = loaded
    items = []

    def collect(servers: object, scope: str, project: str | None, prefix: tuple):
        if not isinstance(servers, dict):
            return
        for name, server in servers.items():
            if isinstance(server, dict):
                line = lines.get((*prefix, "mcpServers", name))
                items.append(mcp_item(name, server, scope, project, line))

    collect(data.get("mcpServers"), "user", None, ())
    projects = data.get("projects")
    if isinstance(projects, dict):
        for path, project in projects.items():
            if isinstance(project, dict):
                collect(project.get("mcpServers"), "local", path, ("projects", path))
    return items


def plugin_hooks(root: Path, home: Path, errors: list[dict]) -> list[dict]:
    """Hook items of ``<root>/hooks/hooks.json``, cited through ``root``."""
    path = root / "hooks" / "hooks.json"
    loaded = load_json(path, home, errors)
    if loaded is None:
        return []
    return hooks_from(loaded[0], loaded[1], rel(path, home))


def has_manifest_hooks(root: Path, home: Path, errors: list[dict]) -> bool:
    loaded = load_json(root / ".claude-plugin" / "plugin.json", home, errors)
    return loaded is not None and isinstance(loaded[0], dict) and "hooks" in loaded[0]


def plugins(home: Path, errors: list[dict], enabled: dict) -> list[dict]:
    """One item per install entry of ``installed_plugins.json``."""
    file = ".claude/plugins/installed_plugins.json"
    loaded = load_json(home / file, home, errors)
    if loaded is None or not isinstance(loaded[0], dict):
        return []
    data, lines = loaded
    installed = data.get("plugins")
    if not isinstance(installed, dict):
        return []
    items = []
    for name, value in installed.items():
        if isinstance(value, dict):
            entries = [(("plugins", name), value)]
        elif isinstance(value, list):
            entries = [(("plugins", name, i), v) for i, v in enumerate(value)]
        else:
            continue
        for path, entry in entries:
            if not isinstance(entry, dict):
                continue
            install = string_or_none(entry.get("installPath"))
            root = Path(install) if install else None
            shown = rel(root, home) if root else None
            items.append(
                {
                    "name": name,
                    "scope": string_or_none(entry.get("scope")),
                    "project_path": string_or_none(entry.get("projectPath")),
                    "version": string_or_none(entry.get("version")),
                    "git_commit_sha": string_or_none(entry.get("gitCommitSha")),
                    "install_path": shown,
                    "root": shown,
                    "enabled": enabled.get(name),
                    "file": file,
                    "line": lines.get(path),
                    "manifest_hooks": bool(root)
                    and has_manifest_hooks(root, home, errors),
                    "hooks": plugin_hooks(root, home, errors) if root else [],
                }
            )
    return items


def link_info(entry: Path, home: Path) -> tuple[str | None, str | None]:
    """``(link kind, target)`` of a symlink or Windows junction, else nulls."""
    try:
        target = os.readlink(entry)
    except (OSError, ValueError):
        return None, None
    target = Path(str(target).removeprefix("\\\\?\\"))
    if not target.is_absolute():
        target = entry.parent / target
    return ("symlink" if entry.is_symlink() else "junction"), rel(target, home)


def skills(home: Path, errors: list[dict]) -> list[dict]:
    """One item per entry of ``.claude/skills/``."""
    folder = home / ".claude" / "skills"
    if not folder.is_dir():
        return []
    items = []
    for entry in sorted(folder.iterdir(), key=lambda p: p.name):
        file = rel(entry, home)
        link, target = link_info(entry, home)
        plugin = (entry / ".claude-plugin" / "plugin.json").exists()
        items.append(
            {
                "name": entry.name,
                "file": file,
                "link": link,
                "target": target,
                "plugin": plugin,
                "root": file if plugin else None,
                "manifest_hooks": plugin and has_manifest_hooks(entry, home, errors),
                "hooks": plugin_hooks(entry, home, errors) if plugin else [],
            }
        )
    return items


def files_under(folder: Path, home: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(rel(p, home) for p in folder.rglob("*") if p.is_file())


def scheduled_tasks(home: Path) -> list[dict]:
    folder = home / ".claude" / "scheduled-tasks"
    if not folder.is_dir():
        return []
    return [
        {"name": task.name, "file": rel(task, home), "files": files_under(task, home)}
        for task in sorted(folder.iterdir(), key=lambda p: p.name)
        if task.is_dir()
    ]


def instructions(home: Path) -> list[dict]:
    files = []
    if (home / ".claude" / "CLAUDE.md").is_file():
        files.append(".claude/CLAUDE.md")
    for sub in ("agents", "commands", "output-styles"):
        files.extend(files_under(home / ".claude" / sub, home))
    return [{"file": file} for file in files]


def inventory(home: Path) -> dict:
    """The full inventory of the user-scope setup under ``home``."""
    errors: list[dict] = []
    settings = []
    enabled: dict = {}
    for name in SETTINGS_FILES:
        loaded = load_json(home / name, home, errors)
        if loaded is not None:
            data, lines = loaded
            settings.append(settings_item(data, lines, name))
            flags = data.get("enabledPlugins") if isinstance(data, dict) else None
            if isinstance(flags, dict):
                enabled.update({k: v for k, v in flags.items() if isinstance(v, bool)})
    return {
        "settings": settings,
        "mcp_servers": mcp_servers(home, errors),
        "plugins": plugins(home, errors, enabled),
        "skills": skills(home, errors),
        "scheduled_tasks": scheduled_tasks(home),
        "instructions": instructions(home),
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
