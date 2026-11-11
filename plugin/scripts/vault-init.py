#!/usr/bin/env python3
"""Create a personal vault from the kit's vault template.

    vault-init.py PATH [--profile personal|work]

Copies plugin/templates/vault/ into PATH (which must not exist, or be an empty
directory), writes `vault.toml` and `.gitignore` for the profile (default
`personal`; `work` keeps `raw/` out of git), then runs `git init -b main` and
one commit. When git has no user.name or user.email, the commit uses the
identity claude-kit <claude-kit@localhost>; it never writes git config. It
never creates a remote or pushes. If a git step fails, it removes what it wrote.

Exit codes: 0 success; 1 refusal or git failure (message on stderr); 2 usage.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "vault"
PROFILES: dict[str, list[str]] = {"personal": [], "work": ["raw/"]}
REGISTRIES = ["people", "topics", "sources"]
OBSIDIAN_IGNORE = ".obsidian/workspace*.json"
COMMIT_MESSAGE = "Scaffold vault from claude-kit"


class GitError(Exception):
    pass


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )


def vault_toml(profile: str) -> str:
    return (
        f"profile = {json.dumps(profile)}\n"
        f"registries = {json.dumps(REGISTRIES)}\n"
        f"git_ignore = {json.dumps(PROFILES[profile])}\n"
    )


def gitignore(profile: str) -> str:
    return "".join(f"{line}\n" for line in [*PROFILES[profile], OBSIDIAN_IGNORE])


def commit_all(dest: Path) -> None:
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
        [*identity, "commit", "-q", "-m", COMMIT_MESSAGE],
    ):
        result = git(*args, cwd=dest)
        if result.returncode != 0:
            cmd = next(a for a in args if not a.startswith("-") and "=" not in a)
            raise GitError(f"git {cmd} failed: {result.stderr.strip()}")


def _clear_readonly(func, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _rmtree(path: Path) -> None:
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_clear_readonly)
    else:
        shutil.rmtree(path, onerror=_clear_readonly)


def remove_written(dest: Path, created: bool) -> None:
    if not dest.exists():
        return
    if created:
        _rmtree(dest)
        return
    for child in dest.iterdir():
        if child.is_dir() and not child.is_symlink():
            _rmtree(child)
        else:
            os.chmod(child, stat.S_IWRITE)
            child.unlink()


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="where to create the vault")
    parser.add_argument("--profile", choices=list(PROFILES), default="personal")
    args = parser.parse_args(argv)

    dest = Path(args.path)
    if dest.is_file():
        print(f"error: {dest} is a file", file=sys.stderr)
        return 1
    if dest.is_dir() and any(dest.iterdir()):
        print(f"error: {dest} is not empty", file=sys.stderr)
        return 1

    created = not dest.exists()
    try:
        shutil.copytree(TEMPLATE, dest, dirs_exist_ok=True)
        (dest / "vault.toml").write_text(vault_toml(args.profile), encoding="utf-8")
        (dest / ".gitignore").write_text(gitignore(args.profile), encoding="utf-8")
        commit_all(dest)
    except (GitError, OSError) as exc:
        remove_written(dest, created)
        print(f"error: {exc}", file=sys.stderr)
        return 1

    vault = dest.resolve().as_posix()
    print(f"Vault created at {vault} (profile {args.profile}).")
    print("Next steps:")
    print(
        f'  1. Set CLAUDE_KIT_VAULT to "{vault}" under "env" in '
        "~/.claude/settings.json."
    )
    print("  2. Open the folder as a vault in Obsidian.")
    print("  3. Create the remote yourself: gh repo create --private")
    return 0


if __name__ == "__main__":
    sys.exit(main())
