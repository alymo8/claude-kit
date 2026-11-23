#!/usr/bin/env python3
"""SessionStart hook: inject the kit map unless it is switched off.

The workspace rules (plugin/rules.md) and the playbooks link to each other
relative to the plugin root, the folder holding rules.md, which breaks when
read from another repo. This prints the plugin root, the folder next to this
hook wherever the plugin is installed (a kit checkout, a skills-dir link or
Claude Code's plugin cache), and the absolute path of each playbook (from the
table under ``## The playbooks`` in plugin/conventions/README.md), so Claude
can read them from any repo (ADR 0032). On by default; CLAUDE_KIT_KIT_MAP=0
turns it off. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# The link target is a bare file name: no folders, so it stays in
# plugin/conventions/.
ROW_RE = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)#\s/\\]+\.md)\)\s*\|")
SECTION = "## The playbooks"


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_KIT_MAP") != "0"


def plugin_root() -> Path:
    """The plugin folder holding this hook, links followed."""
    return Path(__file__).resolve().parents[1]


def playbooks(root: Path) -> list[tuple[str, Path]]:
    """(link text, path) for each playbook row whose file exists."""
    conventions = root / "conventions"
    readme = conventions / "README.md"
    if not readme.is_file():
        return []
    found: list[tuple[str, Path]] = []
    in_section = False
    for line in readme.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = line.strip() == SECTION
            continue
        match = ROW_RE.match(line.strip())
        if in_section and match and (conventions / match.group(2)).is_file():
            found.append((match.group(1), conventions / match.group(2)))
    return found


def build_map(root: Path) -> str:
    lines = [
        "Kit map (claude-kit). Relative links in the workspace rules and the "
        "playbooks resolve against the plugin root, not the current repo.",
        f"Plugin root: {root.as_posix()}",
    ]
    books = playbooks(root)
    if books:
        lines.append("Playbooks (read the one a task needs):")
        lines += [f"- {name}: {path.as_posix()}" for name, path in books]
    return "\n".join(lines)


def main() -> int:
    try:
        if enabled():
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": build_map(plugin_root()),
                }
            }
            print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] kit-map inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
