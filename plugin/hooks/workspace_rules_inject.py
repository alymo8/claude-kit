#!/usr/bin/env python3
"""SessionStart hook: inject the workspace rules in repos outside the kit.

Claude Code loads the workspace CLAUDE.md only for repos inside the kit
checkout. In any other repo this prints the rules, up to their
"## Developing the kit" section, so they apply wherever a repo is cloned
(ADR 0034). The rules come from the kit's AGENTS.md when present (CLAUDE.md is
then an @AGENTS.md stub), else from CLAUDE.md. Silent inside the kit root and
in git worktrees of the kit, which load a kit CLAUDE.md natively. With
CLAUDE_KIT_AGENT set (by plugin/hooks/run.py, for a non-Claude agent), child
repos inside the kit folder get the rules too, since that agent does not load
the parent folder's file (ADR 0050). On by default;
CLAUDE_KIT_WORKSPACE_RULES=0 turns it off. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

KIT_DEV = "## Developing the kit"


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_WORKSPACE_RULES") != "0"


def kit_root() -> Path | None:
    """The kit checkout: the parent of the real plugin/ folder, links followed."""
    root = Path(__file__).resolve().parents[2]
    return root if (root / "CLAUDE.md").is_file() else None


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


def inside(path: Path, root: Path) -> bool:
    return same(path, root) or any(same(parent, root) for parent in path.parents)


def in_kit_worktree(project: Path, root: Path) -> bool:
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
    return same((project / common).resolve(), (root / ".git").resolve())


def toplevel(project: Path) -> Path | None:
    """The git top level of the project, or None outside a repo or on error."""
    try:
        done = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    top = done.stdout.strip()
    if done.returncode != 0 or not top:
        return None
    return Path(top).resolve()


def child_repo(project: Path, root: Path) -> bool:
    """True when the project is in its own git repo nested inside the kit."""
    top = toplevel(project)
    if top is None or same(top, root) or not inside(top, root):
        return False
    return not in_kit_worktree(project, root)


def rules_file(root: Path) -> Path:
    agents = root / "AGENTS.md"
    return agents if agents.is_file() else root / "CLAUDE.md"


def rules(root: Path) -> str:
    lines = rules_file(root).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith(KIT_DEV):
            lines = lines[:index]
            break
    return "\n".join(lines).strip()


def build(root: Path, agent: str = "") -> str:
    where = root.as_posix()
    name = rules_file(root).name
    if agent:
        header = (
            f"Workspace rules (claude-kit, from {where}/{name}). Your agent did "
            "not load them for this repo; follow them as you would an AGENTS.md. "
            f"Relative links resolve against {where}."
        )
    else:
        header = (
            f"Workspace rules (claude-kit, from {where}/{name}). This repo is "
            "outside the kit folder, so Claude Code did not load them; follow them "
            f"as you would a CLAUDE.md. Relative links resolve against {where}."
        )
    return f"{header}\n\n{rules(root)}"


def main() -> int:
    try:
        stdin_text = "" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
        root = kit_root() if enabled() else None
        if root is not None:
            project = project_dir(stdin_text)
            agent = os.environ.get("CLAUDE_KIT_AGENT", "")
            if inside(project, root):
                inject = bool(agent) and child_repo(project, root)
            else:
                inject = not in_kit_worktree(project, root)
            if inject:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": build(root, agent),
                    }
                }
                print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] workspace-rules inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
