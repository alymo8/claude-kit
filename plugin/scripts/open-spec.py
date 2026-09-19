#!/usr/bin/env python3
"""Render one spec/plan to HTML and open it in the browser (the /spec-html command).

Usage: open-spec.py [--no-open] [PATH]

PATH is a Markdown spec or plan (an .html path is mapped back to its .md). With no
PATH, the most recently modified file under ``docs/superpowers/{specs,plans}/`` of
the current repo is used. Rendering goes through the shared ``render-spec.py`` so
the HTML never drifts from the hook's output. ``--no-open`` renders only.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

RENDERER = Path(__file__).resolve().parent / "render-spec.py"
SEARCH_DIRS = ("docs/superpowers/specs", "docs/superpowers/plans")


def _renderer():
    spec = importlib.util.spec_from_file_location("render_spec", RENDERER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def latest_spec(root: Path) -> Path | None:
    """Most recently modified spec or plan Markdown under ``root``, or None."""
    candidates = [
        md for d in SEARCH_DIRS for md in (root / d).glob("*.md") if md.is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def resolve_target(arg: str | None, root: Path) -> Path | None:
    if arg is None:
        return latest_spec(root)
    path = Path(arg)
    if path.suffix.lower() == ".html":
        path = path.with_suffix(".md")
    return path if path.is_file() else None


def _launch(path: Path) -> None:
    """Open ``path`` with the OS default handler."""
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # noqa: S606 - intended: open in the default browser
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def main(argv: list[str]) -> int:
    no_open = "--no-open" in argv
    args = [a for a in argv if a != "--no-open"]
    target = resolve_target(args[0] if args else None, Path.cwd())
    if target is None:
        where = args[0] if args else " or ".join(SEARCH_DIRS)
        print(f"No spec found: {where}", file=sys.stderr)
        return 1
    html = _renderer().render(target)
    print(f"rendered {target} -> {html}")
    if not no_open:
        _launch(html)
        print(f"opened {html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
