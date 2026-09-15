#!/usr/bin/env python3
"""Scaffold a project from the kit's templates, or add the missing files to one.

    scaffold.py --name NAME --stack {node,python} [--parent DIR]
    scaffold.py --adopt --stack {node,python} [--dest DIR] [--name NAME]

New mode renders plugin/templates/ into PARENT/NAME (PARENT defaults to the
workspace directory that contains the kit checkout's `plugin/` folder, i.e. the
kit checkout's own root — new projects land beside the other repos there), then
runs `git init -b main` and one commit.
It refuses a non-empty destination. Adopt mode writes only the files that do not
already exist in DEST (default: the current directory, which must be a git work
tree) and never commits. Neither mode creates a GitHub repository or a stack
manifest (package.json / pyproject.toml): run the framework's own init for that.

Exit codes: 0 success; 1 refusal (message on stderr); 2 usage.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PLUGIN_ROOT / "templates"
INDEXER = PLUGIN_ROOT / "scripts" / "spec-index.py"
STACKS = ("node", "python")
PLACEHOLDER_RE = re.compile(r"\{\{[a-z_]+\}\}")
CI_PATH = Path(".github/workflows/ci.yml")
NEXT_STEPS = {
    "node": (
        "next: `pnpm init` (or a framework starter), ensure package.json has a "
        "packageManager field, run `pnpm install`, then commit package.json and "
        "pnpm-lock.yaml"
    ),
    "python": (
        "next: `uv init` and `uv add --dev pytest ruff`, then commit pyproject.toml"
    ),
}


def render_files(name: str, stack: str, today: str) -> dict[Path, str]:
    """Render every template file for one stack. Keys are project-relative paths."""
    stack_dir = TEMPLATES / "stacks" / stack
    values = {
        "project_name": name,
        "date": today,
        "stack": stack,
        "stack_commands": (stack_dir / "commands.part").read_text("utf-8").rstrip("\n"),
        "stack_gitignore": (stack_dir / "gitignore.part")
        .read_text("utf-8")
        .rstrip("\n"),
    }
    root = TEMPLATES / "project"
    files: dict[Path, str] = {}
    for src in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = src.relative_to(root)
        source = stack_dir / "ci.yml" if rel == CI_PATH else src
        text = source.read_text(encoding="utf-8")
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        leftover = PLACEHOLDER_RE.search(text)
        if leftover:
            raise ValueError(f"unresolved placeholder {leftover.group(0)} in {rel}")
        files[rel] = text
    return files


def write_files(dest: Path, files: dict[Path, str]) -> None:
    for rel, text in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )


def commit_all(dest: Path, message: str) -> None:
    identity: list[str] = []
    name_set = git("config", "--get", "user.name", cwd=dest).returncode == 0
    email_set = git("config", "--get", "user.email", cwd=dest).returncode == 0
    if not (name_set and email_set):
        identity = [
            "-c",
            "user.name=claude-kit",
            "-c",
            "user.email=claude-kit@localhost",
        ]
    for args in (
        ["init", "-q", "-b", "main"],
        ["add", "-A"],
        [*identity, "commit", "-q", "-m", message],
    ):
        result = git(*args, cwd=dest)
        if result.returncode != 0:
            raise SystemExit(f"error: git {args[0]} failed: {result.stderr.strip()}")


def scaffold_new(name: str, stack: str, parent: Path) -> Path:
    dest = parent / name
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise SystemExit(f"error: {dest} already exists and is not an empty directory")
    created_dir = not dest.exists()
    try:
        files = render_files(name, stack, dt.date.today().isoformat())
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    write_files(dest, files)
    try:
        commit_all(dest, "Scaffold project from claude-kit")
    except (SystemExit, OSError) as exc:
        if created_dir:
            shutil.rmtree(dest, ignore_errors=True)
        if isinstance(exc, OSError):
            raise SystemExit(f"error: {exc}") from exc
        raise
    print(f"created: {len(files)} files at {dest}")
    for rel in files:
        print(f"  {rel.as_posix()}")
    print()
    print(NEXT_STEPS[stack])
    print(
        "then: /init to fill in CLAUDE.md; create the remote when ready "
        "(e.g. `gh repo create --private`)."
    )
    return dest


def inside_git_work_tree(path: Path) -> bool:
    return git("rev-parse", "--is-inside-work-tree", cwd=path).returncode == 0


def scaffold_adopt(name: str, stack: str, dest: Path) -> tuple[list[Path], list[Path]]:
    if not dest.is_dir() or not inside_git_work_tree(dest):
        raise SystemExit(f"error: {dest} is not inside a git work tree")
    files = render_files(name, stack, dt.date.today().isoformat())
    created: list[Path] = []
    skipped: list[Path] = []
    for rel, text in files.items():
        path = dest / rel
        keep_in_populated_dir = (
            rel.name == ".gitkeep"
            and path.parent.is_dir()
            and any(path.parent.iterdir())
        )
        if path.exists() or keep_in_populated_dir:
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        created.append(rel)
    # The template index is empty; regenerate it from whatever specs/plans exist.
    # But never overwrite an index the repo already had before this run.
    index = Path("docs/superpowers/README.md")
    if index in created:
        subprocess.run(
            [sys.executable, str(INDEXER), str(dest / "docs" / "superpowers")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    else:
        print(
            "index: docs/superpowers/README.md left as-is "
            "(the render hook regenerates it on the next spec edit)"
        )
    print("created:")
    for rel in created:
        print(f"  {rel.as_posix()}")
    print("skipped (already present):")
    for rel in skipped:
        print(f"  {rel.as_posix()}")
    if Path(".gitignore") in skipped:
        print("check .gitignore contains: docs/superpowers/**/*.html and .env*")
    print("review with `git status`, then commit.")
    return created, skipped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", help="project name (new mode: also the folder name)")
    parser.add_argument("--stack", choices=STACKS, required=True)
    parser.add_argument(
        "--parent",
        type=Path,
        default=PLUGIN_ROOT.parent.parent,
        help="new mode: directory to create the project in",
    )
    parser.add_argument(
        "--adopt",
        action="store_true",
        help="add missing files to an existing repo instead",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path.cwd(),
        help="adopt mode: the repo to add files to (default: cwd)",
    )
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.adopt:
        dest = args.dest.resolve()
        scaffold_adopt(args.name or dest.name, args.stack, dest)
        return 0
    if not args.name:
        parser.error("--name is required in new mode")
    scaffold_new(args.name, args.stack, args.parent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
