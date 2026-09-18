"""Shared helpers for the kit's tests."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"


def load_module(path: Path, name: str) -> ModuleType:
    """Import a script by file path (works for names with hyphens)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_script(
    script: Path, *args: str, stdin: str = "", cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a Python script the way a hook runner would: stdin in, text out."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        timeout=60,
    )


LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^```.*?^```[ \t]*$", re.M | re.S)


def broken_links(md_files: Iterable[Path]) -> list[str]:
    """Relative markdown links (outside code fences) that do not resolve."""
    broken = []
    for md in md_files:
        prose = FENCE_RE.sub("", md.read_text(encoding="utf-8"))
        for match in LINK_RE.finditer(prose):
            href = match.group(1).split("#", 1)[0]
            if not href or "://" in href or href.startswith("mailto:"):
                continue
            if not (md.parent / href).exists():
                broken.append(f"{md} -> {href}")
    return broken
