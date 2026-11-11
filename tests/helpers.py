"""Shared helpers for the kit's tests."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"


REFERENCE_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/references/([\w.-]+\.md)")


def command_text(name: str) -> str:
    """A command's text with each reference file it points to inlined after the
    paragraph that points to it, so tests read the steps in run order."""
    text = (PLUGIN / "commands" / f"{name}.md").read_text(encoding="utf-8")
    parts = []
    for para in text.split("\n\n"):
        parts.append(para)
        for ref in dict.fromkeys(REFERENCE_RE.findall(para)):
            parts.append((PLUGIN / "references" / ref).read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def load_module(path: Path, name: str) -> ModuleType:
    """Import a script by file path (works for names with hyphens)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def clean_env(**extra: str) -> dict[str, str]:
    """os.environ without the developer's CLAUDE_KIT_* settings."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_KIT_")}
    env.update(extra)
    return env


def run_script(
    script: Path,
    *args: str,
    stdin: str = "",
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a Python script the way a hook runner would: stdin in, text out."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env=clean_env() if env is None else env,
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
