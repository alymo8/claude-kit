#!/usr/bin/env python3
"""Per-branch session handoff file: path, generated State section, snapshot.

Usage:
  handoff.py path     [--cwd DIR]                  print the handoff path
  handoff.py state    [--cwd DIR]                  print the generated State section
  handoff.py snapshot [--cwd DIR] [--prompts FILE]  create or refresh the file

The file lives at ``<work-tree>/.claude/handoffs/<branch>.md`` (gitignored). The
``/handoff`` command writes the whole file; ``snapshot`` (run by the SessionEnd
hook) creates it if missing and otherwise replaces only the ``## State`` section
and the ``**Written:**`` line, leaving every other byte untouched. Exit 1 outside a
git work tree.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")
STATE_HEADER = "## State"
STATE_NOTE = "<!-- generated; do not edit -->"
WRITTEN_RE = re.compile(r"^- \*\*Written:\*\* [^\r\n]*$", re.M)


def git(*args: str, cwd: Path, timeout: int = 30) -> str | None:
    """Run git; return stripped stdout on success, None on any failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def work_tree(cwd: Path) -> Path | None:
    top = git("rev-parse", "--show-toplevel", cwd=cwd)
    return Path(top) if top else None


def branch_name(cwd: Path) -> str:
    name = git("branch", "--show-current", cwd=cwd)
    if name:
        return name
    sha = git("rev-parse", "--short=7", "HEAD", cwd=cwd) or "unknown"
    return f"detached-{sha}"


def safe_name(branch: str) -> str:
    return SAFE_RE.sub("_", branch)


def handoff_path(cwd: Path) -> Path:
    top = work_tree(cwd)
    if top is None:
        raise RuntimeError("not inside a git work tree")
    return top / ".claude" / "handoffs" / f"{safe_name(branch_name(cwd))}.md"


def pr_url(cwd: Path) -> str | None:
    """URL of the open PR for the current branch via gh, or None."""
    if not shutil.which("gh"):
        return None
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "url", "-q", ".url"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    url = result.stdout.strip()
    return url if result.returncode == 0 and url.startswith("http") else None


def state_section(cwd: Path) -> str:
    top = work_tree(cwd)
    if top is None:
        raise RuntimeError("not inside a git work tree")
    lines = [STATE_HEADER, STATE_NOTE]
    lines.append(f"- branch: {branch_name(cwd)}  (worktree: {top.as_posix()})")
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", cwd=cwd)
    if upstream:
        counts = git("rev-list", "--left-right", "--count", "@{u}...HEAD", cwd=cwd)
        behind, _, ahead = (counts or "0\t0").partition("\t")
        lines.append(
            f"- upstream: {upstream}, ahead {ahead.strip()}, behind {behind.strip()}"
        )
    else:
        lines.append("- upstream: none")
    porcelain = git("status", "--porcelain", cwd=cwd) or ""
    dirty = [line[3:].strip() for line in porcelain.splitlines() if line.strip()]
    lines.append("- dirty: " + (", ".join(dirty) if dirty else "clean"))
    log = git("log", "--oneline", "-5", cwd=cwd) or ""
    commits = [line.strip() for line in log.splitlines() if line.strip()]
    lines.append("- last commits: " + ("; ".join(commits) if commits else "none"))
    lines.append(f"- PR: {pr_url(cwd) or 'none'}")
    return "\n".join(lines) + "\n"


def written_line(by: str) -> str:
    return f"- **Written:** {datetime.now():%Y-%m-%dT%H:%M} by {by}"


def replace_state(text: str, state: str) -> str:
    """Replace the ``## State`` section (up to the next ``## ``) with
    ``state``."""
    start = text.find(STATE_HEADER)
    if start == -1:
        return text.rstrip("\n") + "\n\n" + state
    end = text.find("\n## ", start + len(STATE_HEADER))
    if end == -1:
        end = len(text)
    return text[:start] + state.rstrip("\n") + "\n" + text[end:]


def new_file_text(branch: str, state: str, prompts: list[str]) -> str:
    parts = [
        f"# Handoff: {branch}",
        "",
        written_line("session-end snapshot"),
        "- **Spec / plan:** none",
        "",
        state.rstrip("\n"),
    ]
    if prompts:
        parts += ["", "## Recent prompts", *[f"- {p}" for p in prompts]]
    return "\n".join(parts) + "\n"


def ensure_ignored(folder: Path) -> None:
    """Write a ``*`` .gitignore into ``folder`` if it doesn't already have one."""
    ignore = folder / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8", newline="\n")


def snapshot(cwd: Path, prompts: list[str]) -> Path:
    path = handoff_path(cwd)
    state = state_section(cwd)
    if path.exists():
        text = replace_state(path.read_text(encoding="utf-8"), state)
        text = WRITTEN_RE.sub(written_line("session-end snapshot"), text, count=1)
    else:
        text = new_file_text(branch_name(cwd), state, prompts)
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_ignored(path.parent)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("subcommand", choices=("path", "state", "snapshot"))
    parser.add_argument("--cwd", default=".", help="a directory inside the repo")
    parser.add_argument("--prompts", help="file with one recent prompt per line")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cwd = Path(args.cwd).resolve()
    if work_tree(cwd) is None:
        print("[claude-kit] handoff: not inside a git work tree", file=sys.stderr)
        return 1
    if args.subcommand == "path":
        print(handoff_path(cwd).as_posix())
    elif args.subcommand == "state":
        sys.stdout.write(state_section(cwd))
    else:
        prompts: list[str] = []
        if args.prompts:
            raw = Path(args.prompts).read_text(encoding="utf-8")
            prompts = [line.strip() for line in raw.splitlines() if line.strip()]
        print(snapshot(cwd, prompts).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
