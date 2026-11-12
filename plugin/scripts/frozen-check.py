#!/usr/bin/env python3
"""Check that no frozen file changed since its snapshot commit.

    python frozen-check.py FILE.md [FILE.md ...] [--base REF] [--root DIR]

Reads the ``- **Frozen:**`` header bullets of each spec or plan FILE.md
(before the first ``## `` heading, outside code fences; indented continuation
lines count) and takes their backticked spans as path patterns: ``*`` and
``?`` stay inside one path segment, ``**/`` matches zero or more directories,
a trailing ``**`` matches anything. A pattern ending in ``/``, or one that
matches no file but names a directory, freezes everything under it.

The base is ``git merge-base REF HEAD`` (REF defaults to ``origin/main``) in
the repository holding ``--root`` (default: the current directory). A frozen
file's snapshot is the base when the file is in the base tree, else the branch
commit that added it, moved to the last later commit carrying a
``Frozen-change-approved: <path>`` trailer line. A file that differs between
its snapshot and HEAD is a violation.

Prints, warnings first:

    frozen: none declared
    frozen: warning: no file matches <pattern>
    frozen: changed <path> since <short snapshot>
    frozen: ok (<n> files)

Exits 0 when nothing changed or nothing is declared, 1 on violations, 2 on bad
usage, an unreadable file or a git failure (one stderr line).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

BULLET_RE = re.compile(r"^\s*- \*\*Frozen:\*\*")
SPAN_RE = re.compile(r"`([^`]+)`")
TRAILER_RE = re.compile(r"^Frozen-change-approved:[ \t]*(\S+)[ \t]*$", re.M)


class GitError(Exception):
    pass


def parse_patterns(text: str) -> list[str]:
    """The backticked spans of every ``- **Frozen:**`` header bullet, in order."""
    bullets: list[str] = []
    in_fence = False
    in_bullet = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            in_bullet = False
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            break
        if BULLET_RE.match(line):
            bullets.append(line)
            in_bullet = True
        elif (
            in_bullet
            and line.strip()
            and line[0].isspace()
            and not line.strip().startswith("- ")
        ):
            bullets[-1] += "\n" + line
        else:
            in_bullet = False
    patterns = []
    for bullet in bullets:
        for span in SPAN_RE.findall(bullet):
            patterns.append(span[2:] if span.startswith("./") else span)
    return patterns


def pattern_regex(pattern: str) -> re.Pattern[str]:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )
    except subprocess.CalledProcessError as exc:
        raise GitError(f"{' '.join(cmd)}: {exc.stderr.strip()}") from exc
    except OSError as exc:
        raise GitError(f"{' '.join(cmd)}: {exc}") from exc
    return result


def _check(patterns: list[str], base_ref: str, root: str) -> int:
    top = _run(["git", "-C", root, "rev-parse", "--show-toplevel"]).stdout.strip()

    def git(*args: str) -> str:
        return _run(["git", "-c", "core.quotepath=off", "-C", top, *args]).stdout

    base = git("merge-base", base_ref, "HEAD").strip()
    commits = git("rev-list", "--reverse", f"{base}..HEAD").split()
    index = {sha: i for i, sha in enumerate(commits)}

    base_tree = set(
        git("ls-tree", "-r", "--full-tree", "--name-only", base).split("\n")
    )
    head_tree = set(
        git("ls-tree", "-r", "--full-tree", "--name-only", "HEAD").split("\n")
    )
    added = set(
        git(
            "log",
            "--no-renames",
            "--diff-filter=A",
            "--name-only",
            "--format=",
            f"{base}..HEAD",
        ).split("\n")
    )
    candidates = {p for p in base_tree | head_tree | added if p}

    frozen: set[str] = set()
    warnings = []
    for pattern in patterns:
        glob = pattern + "**" if pattern.endswith("/") else pattern
        matched = {p for p in candidates if pattern_regex(glob).fullmatch(p)}
        if not matched and not glob.endswith("**"):
            regex = pattern_regex(glob + "/**")
            matched = {p for p in candidates if regex.fullmatch(p)}
        if not matched:
            warnings.append(f"frozen: warning: no file matches {pattern}")
        frozen |= matched
    for line in warnings:
        print(line)

    approvals: dict[str, list[int]] = {}
    for record in git("log", "--format=%H%x00%B%x1e", f"{base}..HEAD").split("\x1e"):
        record = record.strip()
        if not record:
            continue
        sha, _, body = record.partition("\x00")
        if sha not in index:
            continue
        for path in TRAILER_RE.findall(body):
            approvals.setdefault(path, []).append(index[sha])

    violations = []
    for path in sorted(frozen):
        if path in base_tree:
            start = -1
        else:
            first = git(
                "log",
                "--no-renames",
                "--diff-filter=A",
                "--reverse",
                "--format=%H",
                f"{base}..HEAD",
                "--",
                path,
            ).split()
            start = index[first[0]] if first and first[0] in index else -1
        later = [i for i in approvals.get(path, []) if i > start]
        snap_index = max(later) if later else start
        snapshot = base if snap_index == -1 else commits[snap_index]
        cmd = [
            "git",
            "-c",
            "core.quotepath=off",
            "-C",
            top,
            "diff",
            "--quiet",
            snapshot,
            "HEAD",
            "--",
            path,
        ]
        result = _run(cmd, check=False)
        if result.returncode == 1:
            violations.append(f"frozen: changed {path} since {snapshot[:7]}")
        elif result.returncode != 0:
            raise GitError(f"{' '.join(cmd)}: {result.stderr.strip()}")

    if violations:
        for line in violations:
            print(line)
        return 1
    print(f"frozen: ok ({len(frozen)} files)")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check frozen files.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)

    patterns: list[str] = []
    for name in args.files:
        try:
            text = Path(name).resolve().read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            print(f"frozen-check: cannot read {name}", file=sys.stderr)
            return 2
        for pattern in parse_patterns(text):
            if pattern not in patterns:
                patterns.append(pattern)
    if not patterns:
        print("frozen: none declared")
        return 0

    root = args.root if args.root is not None else str(Path.cwd())
    try:
        return _check(patterns, args.base, root)
    except GitError as exc:
        print(f"frozen-check: git failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
