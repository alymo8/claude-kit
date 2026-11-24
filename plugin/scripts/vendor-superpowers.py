#!/usr/bin/env python3
"""Vendor the superpowers skills the kit references into vendor/superpowers/.

Usage: vendor-superpowers.py --from DIR [--repo DIR] [--source TEXT]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REF_RE = re.compile(r"superpowers:([a-z0-9-]+)")


def _scan(paths) -> set[str]:
    found: set[str] = set()
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        found.update(REF_RE.findall(text))
    return found


def kit_references(repo: Path) -> set[str]:
    paths = list(repo.glob("plugin/**/*.md"))
    agents = repo / "AGENTS.md"
    if agents.is_file():
        paths.append(agents)
    return _scan(p for p in paths if p.is_file())


def closure(start: set[str], skills_dir: Path) -> set[str]:
    result = set(start)
    todo = set(start)
    while todo:
        name = todo.pop()
        folder = skills_dir / name
        if not folder.is_dir():
            continue
        new = _scan(p for p in folder.rglob("*.md") if p.is_file()) - result
        result |= new
        todo |= new
    return result


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="upstream", required=True)
    ap.add_argument("--repo", default=str(root))
    ap.add_argument("--source", default="https://github.com/obra/superpowers")
    args = ap.parse_args(argv)
    upstream = Path(args.upstream)
    repo = Path(args.repo)
    skills = upstream / "skills"

    wanted = closure(kit_references(repo), skills)
    missing = sorted(n for n in wanted if not (skills / n).is_dir())
    if missing:
        print(f"ERROR: unknown superpowers skill(s): {', '.join(missing)}")
        return 1

    version = json.loads((upstream / "package.json").read_text(encoding="utf-8"))[
        "version"
    ]
    bundle = repo / "vendor" / "superpowers"
    if (bundle / "skills").exists():
        shutil.rmtree(bundle / "skills")
    (bundle / "skills").mkdir(parents=True)
    for name in sorted(wanted):
        shutil.copytree(skills / name, bundle / "skills" / name)
        print(f"copied {name}")
    shutil.copyfile(upstream / "LICENSE", bundle / "LICENSE")
    with (bundle / "VERSION").open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"version: {version}\nsource: {args.source}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
