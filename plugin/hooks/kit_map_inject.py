#!/usr/bin/env python3
"""SessionStart hook: inject the kit map unless it is switched off.

The workspace CLAUDE.md links to conventions/ and knowledge/ relative to the
kit root, which breaks in child repos. This prints the kit root and the
absolute path of each playbook (from the table under ``## The playbooks`` in
conventions/README.md) and of the kit's ADR folder, so Claude can read them
from any repo (ADR 0032). On by default; CLAUDE_KIT_KIT_MAP=0 turns it off.
Prints nothing when the kit root has no conventions/README.md (a plugin-only
install). Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROW_RE = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)#\s]+\.md)\)\s*\|")
SECTION = "## The playbooks"


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_KIT_MAP") != "0"


def kit_root() -> Path | None:
    """The kit checkout: the parent of the real plugin/ folder, links followed."""
    root = Path(__file__).resolve().parents[2]
    return root if (root / "conventions" / "README.md").is_file() else None


def playbooks(root: Path) -> list[tuple[str, Path]]:
    """(link text, path) for each playbook row whose file exists."""
    conventions = root / "conventions"
    found: list[tuple[str, Path]] = []
    in_section = False
    for line in (conventions / "README.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = line.strip() == SECTION
            continue
        match = ROW_RE.match(line.strip())
        if in_section and match and (conventions / match.group(2)).is_file():
            found.append((match.group(1), conventions / match.group(2)))
    return found


def build_map(root: Path) -> str:
    lines = [
        f"Kit map (claude-kit). Kit root: {root.as_posix()}. Relative links in "
        "the workspace CLAUDE.md (e.g. conventions/, knowledge/, plugin/) "
        "resolve against the kit root, not the current repo."
    ]
    books = playbooks(root)
    if books:
        lines.append("Playbooks (read the one a task needs):")
        lines += [f"- {name}: {path.as_posix()}" for name, path in books]
    adrs = root / "knowledge" / "decisions"
    if adrs.is_dir():
        lines.append(f"Kit ADRs: {adrs.as_posix()}/")
    return "\n".join(lines)


def main() -> int:
    try:
        root = kit_root() if enabled() else None
        if root is not None:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": build_map(root),
                }
            }
            print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] kit-map inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
