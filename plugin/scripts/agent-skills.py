#!/usr/bin/env python3
"""Generate one wrapper skill per kit command for agents without commands.

Usage: agent-skills.py [--check] [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SKIP = {"ship-many"}

TEMPLATE = """---
name: {name}
description: {desc_json}
disable-model-invocation: true
---

# /{name} (claude-kit command)

Follow `<plugin>/commands/{name}.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected claude-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
"""


def description(text: str) -> str:
    """The raw value of the description: line in a command's frontmatter."""
    parts = text.replace("\r\n", "\n").split("---", 2)
    head = parts[1] if len(parts) > 2 else ""
    for line in head.splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    raise ValueError("command has no description: line")


def render(name: str, desc: str) -> str:
    return TEMPLATE.format(name=name, desc_json=json.dumps(desc, ensure_ascii=False))


def wrappers(commands_dir: Path) -> dict[str, str]:
    result = {}
    for path in sorted(commands_dir.glob("*.md")):
        if path.stem in SKIP:
            continue
        desc = description(path.read_text(encoding="utf-8"))
        result[path.stem] = render(path.stem, desc)
    return result


def main(argv=None) -> int:
    default_out = Path(__file__).resolve().parents[1] / "agent-skills"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path, default=default_out)
    args = parser.parse_args(argv)
    commands = Path(__file__).resolve().parents[1] / "commands"
    wanted = wrappers(commands)
    out: Path = args.out

    if args.check:
        problems = []
        for name, text in wanted.items():
            skill = out / name / "SKILL.md"
            if not skill.is_file():
                problems.append(f"missing: {name}")
            elif skill.read_text(encoding="utf-8") != text:
                problems.append(f"differs: {name}")
        if out.is_dir():
            problems.extend(
                f"stale: {p.name}"
                for p in sorted(out.iterdir())
                if p.is_dir() and p.name not in wanted
            )
        else:
            problems.append(f"missing: {out}")
        for line in problems:
            print(line)
        if problems:
            return 1
        print("ok")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    for p in out.iterdir():
        if p.is_dir() and p.name not in wanted:
            shutil.rmtree(p)
    for name, text in wanted.items():
        folder = out / name
        folder.mkdir(exist_ok=True)
        with (folder / "SKILL.md").open("w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
