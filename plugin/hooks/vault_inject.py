#!/usr/bin/env python3
"""SessionStart hook: point the session at the personal vault.

On whenever CLAUDE_KIT_VAULT is set to a non-empty path. Unset or empty: nothing
is printed. A path with no vault.toml prints one warning line to stderr and no
context. Otherwise the hook injects one line naming the vault's profile and
path. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import sys
import tomllib
from pathlib import Path


def context(path: Path, profile: str) -> str:
    p = path.as_posix()
    return (
        f"Vault ({profile}): {p}. Before answering questions about the user's "
        f"work, people, projects or topics, read {p}/wiki/index.md and the "
        "pages it points to. To add material, use the claude-kit:ingest skill; "
        "to turn a vault task into a prompt, claude-kit:task-prompt."
    )


def main() -> int:
    try:
        value = os.environ.get("CLAUDE_KIT_VAULT", "")
        if not value:
            return 0
        path = Path(value).expanduser()
        if not path.is_absolute():
            print(
                f"[claude-kit] CLAUDE_KIT_VAULT is not an absolute path: {value}",
                file=sys.stderr,
            )
            return 0
        toml_file = path / "vault.toml"
        if not toml_file.is_file():
            print(
                f"[claude-kit] CLAUDE_KIT_VAULT has no vault.toml: {value}",
                file=sys.stderr,
            )
            return 0
        config = tomllib.loads(toml_file.read_text(encoding="utf-8"))
        profile = str(config.get("profile", "unknown"))
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context(path, profile),
            }
        }
        print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] vault inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
