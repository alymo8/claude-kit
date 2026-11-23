#!/usr/bin/env python3
"""SessionStart hook: inject the workspace rules where the agent lacks them.

The rules live in plugin/rules.md, next to this hook's folder, so they ship
with the plugin wherever it is installed (a kit checkout, a skills-dir link or
Claude Code's plugin cache). The kit's AGENTS.md imports them, so Claude Code
loads them natively inside a kit checkout; other agents read AGENTS.md without
expanding the import (ADR 0034, ADR 0050). Where the session runs decides:

| Where the session runs                    | Claude Code | Vibe/Codex/Cursor |
|-------------------------------------------|-------------|-------------------|
| A kit checkout (its root or a child repo) | silent      | inject            |
| A git worktree of the kit, anywhere       | silent      | inject            |
| Any other repo                            | inject      | inject            |

A kit checkout is a folder holding plugin/rules.md and a
.claude-plugin/marketplace.json named agent-kit, found by walking up from the
project. A git worktree of the kit (also one of a branch from before the move,
without plugin/rules.md) is found by comparing git common dirs with the kit
checkout the plugin runs from. CLAUDE_KIT_AGENT, set by plugin/hooks/run.py,
names a non-Claude agent. On by default; CLAUDE_KIT_WORKSPACE_RULES=0 turns it
off. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

KIT_NAME = "agent-kit"


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_WORKSPACE_RULES") != "0"


def is_kit_checkout(folder: Path) -> bool:
    """True when the folder holds plugin/rules.md and the agent-kit marketplace."""
    try:
        if not (folder / "plugin" / "rules.md").is_file():
            return False
        marketplace = folder / ".claude-plugin" / "marketplace.json"
        data = json.loads(marketplace.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("name") == KIT_NAME


def find_kit(project: Path) -> Path | None:
    """The first of the project and its parents that is a kit checkout."""
    for folder in (project, *project.parents):
        if is_kit_checkout(folder):
            return folder
    return None


def plugin_root() -> Path:
    """The plugin folder holding this hook, links followed."""
    return Path(__file__).resolve().parents[1]


def plugin_kit() -> Path | None:
    """The kit checkout the plugin runs from, or None for an installed copy."""
    kit = plugin_root().parent
    return kit if is_kit_checkout(kit) else None


def project_dir(stdin_text: str) -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    try:
        data = json.loads(stdin_text) if stdin_text.strip() else {}
    except ValueError:
        data = {}
    cwd = data.get("cwd") if isinstance(data, dict) else None
    return Path(cwd).resolve() if cwd else Path.cwd().resolve()


def same(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def in_kit_worktree(project: Path, kit: Path) -> bool:
    """True when the project is in a git worktree whose common dir is the kit's."""
    try:
        done = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    common = done.stdout.strip()
    if done.returncode != 0 or not common:
        return False
    return same((project / common).resolve(), (kit / ".git").resolve())


def should_inject(project: Path, agent: str) -> bool:
    if agent:
        return True
    if find_kit(project) is not None:
        return False
    kit = plugin_kit()
    return not (kit is not None and in_kit_worktree(project, kit))


def build(plugin: Path, agent: str = "") -> str:
    where = plugin.as_posix()
    if agent:
        middle = (
            "Your agent did not load them for this repo; follow them as you "
            "would an AGENTS.md."
        )
    else:
        middle = (
            "This repo is outside the kit folder, so Claude Code did not load "
            "them; follow them as you would a CLAUDE.md."
        )
    header = (
        f"Workspace rules (claude-kit, from {where}/rules.md). {middle} "
        f"Relative links resolve against the plugin root, {where}."
    )
    rules = (plugin / "rules.md").read_text(encoding="utf-8").strip()
    return f"{header}\n\n{rules}"


def main() -> int:
    try:
        stdin_text = "" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
        plugin = plugin_root()
        if enabled() and (plugin / "rules.md").is_file():
            project = project_dir(stdin_text)
            agent = os.environ.get("CLAUDE_KIT_AGENT", "")
            if should_inject(project, agent):
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": build(plugin, agent),
                    }
                }
                print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] workspace-rules inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
