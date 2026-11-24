#!/usr/bin/env python3
"""Scaffold a project from the kit's templates, or add the missing files to one.

    scaffold.py --name NAME --stack {node,python} [--parent DIR]
    scaffold.py --adopt --stack {node,python} [--dest DIR] [--name NAME]

New mode renders plugin/templates/ into PARENT/NAME, then runs `git init -b main`
and one commit. PARENT defaults to the kit's main checkout when the current
folder is inside a kit checkout or one of its worktrees, else to the kit checkout
the plugin runs from (a contributor link), else, inside another git repo, to the
folder that holds that repo's main checkout (never inside it), else to the
current folder; never the plugin cache or a worktree.
It records `.githooks/pre-push` as executable and sets
`core.hooksPath=.githooks`, which enables the pre-push lint hook.
It refuses a non-empty destination. Adopt mode writes only the files that do not
already exist in DEST (default: the current directory, which must be a git work
tree) and never commits. It stages `.githooks/pre-push` as executable when it
creates it, and never sets git config. Neither mode creates a GitHub repository
or a stack manifest (package.json / pyproject.toml): run the framework's own init
for that.

Exit codes: 0 success; 1 refusal (message on stderr); 2 usage.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PLUGIN_ROOT / "templates"
INDEXER = PLUGIN_ROOT / "scripts" / "spec-index.py"
KIT_HOOK = PLUGIN_ROOT / "hooks" / "workspace_rules_inject.py"
STACKS = ("node", "python")
PLACEHOLDER_RE = re.compile(r"\{\{[a-z_]+\}\}")
CI_PATH = Path(".github/workflows/ci.yml")
HOOK_PATH = Path(".githooks/pre-push")
GITATTRIBUTES = Path(".gitattributes")
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


def load_kit_hook():
    """The workspace-rules hook module: one definition of a kit checkout."""
    spec = importlib.util.spec_from_file_location("workspace_rules_inject", KIT_HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main_checkout(kit: Path) -> Path:
    """The main checkout of the kit's repo (kit itself when not a worktree)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(kit), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return kit
    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        return kit
    common = (kit / out).resolve()
    return common.parent if common.name == ".git" else kit


def enclosing_repo(cwd: Path) -> Path | None:
    """The top level of the git work tree holding cwd, or None outside one."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return None
    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        return None
    return Path(out).resolve()


def default_parent(cwd: Path) -> Path:
    """Where a new project goes when --parent is not given."""
    hook = load_kit_hook()
    kit = hook.find_kit(cwd)
    if kit is not None:
        return main_checkout(kit)
    if hook.is_kit_checkout(PLUGIN_ROOT.parent):
        return main_checkout(PLUGIN_ROOT.parent)
    top = enclosing_repo(cwd)
    if top is not None:
        main = main_checkout(top)
        if main.parent == main:
            print(
                f"error: cannot pick a folder next to {main}; pass --parent <dir>",
                file=sys.stderr,
            )
            raise SystemExit(2)
        return main.parent
    return cwd


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

    def render(text: str, rel: Path) -> str:
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        leftover = PLACEHOLDER_RE.search(text)
        if leftover:
            raise ValueError(f"unresolved placeholder {leftover.group(0)} in {rel}")
        return text

    root = TEMPLATES / "project"
    files: dict[Path, str] = {}
    for src in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = src.relative_to(root)
        source = stack_dir / "ci.yml" if rel == CI_PATH else src
        files[rel] = render(source.read_text(encoding="utf-8"), rel)
    hook = (stack_dir / "pre-push").read_text(encoding="utf-8")
    files[HOOK_PATH] = render(hook, HOOK_PATH)
    return files


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_files(dest: Path, files: dict[Path, str]) -> None:
    for rel, text in files.items():
        write_file(dest / rel, text)


def make_executable(path: Path) -> None:
    """Set the executable bits (no effect on Windows)."""
    path.chmod(path.stat().st_mode | 0o111)


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
            "user.name=agent-kit",
            "-c",
            "user.email=agent-kit@localhost",
        ]
    make_executable(dest / HOOK_PATH)
    for args in (
        ["init", "-q", "-b", "main"],
        ["add", "-A"],
        ["update-index", "--chmod=+x", HOOK_PATH.as_posix()],
        [*identity, "commit", "-q", "-m", message],
        ["config", "core.hooksPath", ".githooks"],
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
        commit_all(dest, "Scaffold project from agent-kit")
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
    print(
        "then: mark build-test and gitleaks as required checks on main "
        "(see .github/workflows/README.md)."
    )
    print("hooks: pre-push lint is enabled for this clone (core.hooksPath=.githooks).")
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
        write_file(path, text)
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
            "(the spec-index hook regenerates it on the next spec edit)"
        )
    print("created:")
    for rel in created:
        print(f"  {rel.as_posix()}")
    print("skipped (already present):")
    for rel in skipped:
        print(f"  {rel.as_posix()}")
    if Path(".gitignore") in skipped:
        print(
            "check .gitignore contains: docs/superpowers/**/*.html, .env* "
            "and .claude/handoffs/"
        )
    workflows = Path(".github/workflows")
    if workflows / "README.md" in created and workflows / "ci.yml" in skipped:
        print(
            "check .github/workflows/README.md: its required check names "
            "must match your workflows' job IDs."
        )
    if HOOK_PATH in created:
        make_executable(dest / HOOK_PATH)
        staged = git("add", "--chmod=+x", HOOK_PATH.as_posix(), cwd=dest)
        if staged.returncode != 0:
            raise SystemExit(f"error: git add failed: {staged.stderr.strip()}")
        print(
            "hooks: .githooks/pre-push is staged; enable it with "
            "`git config core.hooksPath .githooks` (this replaces the current "
            "hooks setup: .git/hooks or an existing core.hooksPath)."
        )
        if GITATTRIBUTES in skipped:
            print("check .gitattributes contains: .githooks/* text eol=lf")
    print("review with `git status`, then commit.")
    return created, skipped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", help="project name (new mode: also the folder name)")
    parser.add_argument("--stack", choices=STACKS, required=True)
    parser.add_argument(
        "--parent",
        type=Path,
        default=None,
        help=(
            "new mode: directory to create the project in "
            "(default: the kit's main checkout, else, inside another git repo, "
            "the folder that holds that repo's main checkout, "
            "else the current folder)"
        ),
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
    parent = args.parent or default_parent(Path.cwd().resolve())
    scaffold_new(args.name, args.stack, parent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
