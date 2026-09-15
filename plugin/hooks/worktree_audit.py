#!/usr/bin/env python3
"""SessionStart hook: report worktrees and branches left over from finished work.

Advisory only. Prints one short block when the repo containing ``cwd`` has
worktrees other than the main one (and the one we are in), or local branches that
are already merged into the default branch, have no upstream, or had their upstream
deleted (e.g. squash-merged then pruned). Prints nothing when clean or outside a
git repo. Never deletes or prunes. Always exits 0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FOOTER = (
    "Clean up with superpowers:finishing-a-development-branch once the work is "
    "landed; ask before deleting anything unmerged."
)


def git(*args: str, cwd: Path) -> str | None:
    """Run git; return stdout on success, None on any failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def _norm(path: str) -> str:
    return path.strip().replace("\\", "/").rstrip("/").lower()


def default_branch(cwd: Path) -> str | None:
    for name in ("main", "master"):
        if git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}", cwd=cwd):
            return name
    return None


def leftover_worktrees(cwd: Path) -> list[str]:
    out = git("worktree", "list", "--porcelain", cwd=cwd)
    if not out:
        return []
    here = _norm(git("rev-parse", "--show-toplevel", cwd=cwd) or "")
    found: list[str] = []
    for entry in out.strip().split("\n\n")[1:]:  # first entry is the main worktree
        path = branch = None
        for line in entry.splitlines():
            if line.startswith("worktree "):
                path = line[len("worktree ") :]
            elif line.startswith("branch "):
                branch = line[len("branch ") :].removeprefix("refs/heads/")
        if path and _norm(path) != here:
            found.append(f"{path} ({branch or 'detached'})")
    return found


def leftover_branches(cwd: Path, default: str) -> list[str]:
    current = (git("branch", "--show-current", cwd=cwd) or "").strip()
    merged_out = git(
        "branch", "--format=%(refname:short)", "--merged", default, cwd=cwd
    )
    merged = {line.strip() for line in (merged_out or "").splitlines()}
    refs = git(
        "for-each-ref",
        "--format=%(refname:short) %(upstream:short) %(upstream:track)",
        "refs/heads/",
        cwd=cwd,
    )
    found: list[str] = []
    for line in (refs or "").splitlines():
        name, _, rest = line.partition(" ")
        upstream, _, track = rest.partition(" ")
        if name in (default, "main", "master", current):
            continue
        if name in merged:
            found.append(f"{name} (merged)")
        elif track.strip() == "[gone]":
            found.append(f"{name} (upstream gone)")
        elif not upstream:
            found.append(f"{name} (no upstream)")
    return found


def report(cwd: Path) -> str:
    if git("rev-parse", "--is-inside-work-tree", cwd=cwd) is None:
        return ""
    default = default_branch(cwd)
    worktrees = leftover_worktrees(cwd)
    branches = leftover_branches(cwd, default) if default else []
    if not worktrees and not branches:
        return ""
    lines = ["[claude-kit] Leftover from earlier feature work in this repo:"]
    if worktrees:
        lines.append("  worktrees: " + ", ".join(worktrees))
    if branches:
        lines.append("  branches:  " + ", ".join(branches))
    lines.append(FOOTER)
    return "\n".join(lines)


def main() -> int:
    try:
        text = report(Path.cwd())
        if text:
            print(text)
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] worktree audit error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
