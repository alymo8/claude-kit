#!/usr/bin/env python3
"""Archive or restore the Vibe session this command runs in.

Usage::

    archive-session.py token
    archive-session.py archive --token TOKEN
    archive-session.py status --token TOKEN
    archive-session.py restore [--session-id ID | --last | (no selector)]

In Mistral Vibe, archiving a session sets ``archived_at`` in its
``meta.json`` (under ``~/.vibe/logs/session/unified/<session-id>/``): the
session then leaves the Sessions list while staying fully readable and
restorable. Vibe offers no way for a session to archive itself, so this
script finds its own session first:

- ``token`` prints a unique token. The command's first bash call prints
  it, and the tool result that carried it lands in the session's journal
  chunks seconds later.
- ``archive --token TOKEN`` then searches the journal chunks for the
  token; the session whose chunk holds it is this session. The match
  window is bounded to recent chunks, so the search stays cheap.

``restore`` needs no token because it runs in a different session than
the one it targets: without a selector it lists the most recently
archived sessions (id, title, archived at) and the caller asks the user
which to bring back; ``--session-id`` restores that one, ``--last`` the
most recently archived one without asking.

Exit codes: 0 on success (including ``restore`` of an already active
session and ``status`` reporting, which keeps the change reversible),
1 when the session cannot be identified or Vibe's session storage is
missing (Claude Code, say, has no such concept).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

TOKEN_PREFIX = "kit-archive-"
# A session journal chunk last written earlier than this is not searched:
# the token pass and the archive pass run a few seconds apart.
FRESH_WINDOW_SECONDS = 15 * 60
LIST_LIMIT = 10


def sessions_root(root: Path | None) -> Path:
    """The unified session storage, or exit when it is missing."""
    base = root if root is not None else Path.home() / ".vibe" / "logs" / "session"
    unified = base / "unified"
    if not unified.is_dir():
        print(
            f"error: no Vibe session storage at {unified}; "
            "this command works only in Mistral Vibe.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return unified


def make_token() -> str:
    """A token no transcript will contain by accident."""
    return TOKEN_PREFIX + uuid.uuid4().hex


def read_meta(session_dir: Path) -> dict:
    return json.loads((session_dir / "meta.json").read_text(encoding="utf-8"))


def write_meta(session_dir: Path, meta: dict) -> None:
    """Atomically (tmp + replace) so a parallel write never truncates it."""
    tmp = session_dir / "meta.json.tmp"
    tmp.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, session_dir / "meta.json")


def find_session_by_token(unified: Path, token: str, now: float) -> Path:
    """The session dir whose journal holds the token.

    Searches each session's live ``journal/*.jsonl`` and its ``chunks/``
    (written at turn boundaries), newest first, only files written inside
    ``FRESH_WINDOW_SECONDS``: the token was printed moments ago, so the
    first hit is this session. No hit is an error (stale token, or the
    result never got journalled): the caller prints a fresh token and
    retries.
    """
    if not re.fullmatch(re.escape(TOKEN_PREFIX) + r"[0-9a-f]{16,}", token):
        print(f"error: not a token this script printed: {token!r}", file=sys.stderr)
        raise SystemExit(1)
    needle = token.encode("ascii")
    files: list[tuple[float, Path]] = []
    for session in unified.iterdir():
        for name in ("journal", "chunks"):
            folder = session / name
            if not folder.is_dir():
                continue
            for entry in os.scandir(folder):
                try:
                    mtime = entry.stat().st_mtime
                except OSError:
                    continue
                if now - mtime <= FRESH_WINDOW_SECONDS:
                    files.append((mtime, folder / entry.name))
    for _, path in sorted(files, reverse=True):
        try:
            if needle in path.read_bytes():
                return path.parent.parent
        except OSError:
            continue
    print(
        "error: token not found in any recent session journal; "
        "rerun the token pass and retry with the new token.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def archive(session_dir: Path) -> None:
    meta = read_meta(session_dir)
    if meta.get("archived_at"):
        print(f"already archived (archived_at {meta['archived_at']})")
        return
    meta["archived_at"] = datetime.now(UTC).isoformat()
    write_meta(session_dir, meta)
    print(f"archived {meta.get('session_id')} ({meta.get('title') or 'untitled'})")


def restore(session_dir: Path) -> None:
    meta = read_meta(session_dir)
    if not meta.get("archived_at"):
        print(f"already active: {meta.get('session_id')}")
        return
    meta["archived_at"] = None
    write_meta(session_dir, meta)
    print(f"restored {meta.get('session_id')} ({meta.get('title') or 'untitled'})")


def archived_sessions(unified: Path) -> list[tuple[str, str | None, str]]:
    """(session_id, title, archived_at) of archived sessions, newest first."""
    rows: list[tuple[str, str | None, str, float]] = []
    for session in unified.iterdir():
        m = session / "meta.json"
        if not m.is_file():
            continue
        try:
            meta = read_meta(session)
        except (OSError, ValueError):
            continue
        at = meta.get("archived_at")
        if at:
            rows.append((meta.get("session_id"), meta.get("title"), at, _parse(at)))
    rows.sort(key=lambda r: r[3], reverse=True)
    return [(sid, title, at) for sid, title, at, _ in rows]


def _parse(stamp: str) -> float:
    try:
        return datetime.fromisoformat(stamp).timestamp()
    except ValueError:
        return 0.0


def current(unified: Path, token: str) -> Path:
    return find_session_by_token(unified, token, datetime.now().timestamp())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", metavar="DIR", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("token", help="print a fresh identification token")
    for name, help_ in (
        ("archive", "archive the session the token run in"),
        ("status", "report whether that session is archived"),
    ):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--token", required=True)
    p = sub.add_parser("restore", help="restore an archived session")
    p.add_argument("--session-id", dest="session_id")
    p.add_argument("--last", action="store_true")
    args = parser.parse_args(argv)

    unified = sessions_root(Path(args.root) if args.root else None)

    if args.action == "token":
        print(make_token())
    elif args.action == "archive":
        archive(current(unified, args.token))
    elif args.action == "status":
        meta = read_meta(current(unified, args.token))
        print(
            f"archived {meta['archived_at']}"
            if meta.get("archived_at")
            else "not archived"
        )
    elif args.action == "restore":
        if args.last or args.session_id:
            sessions = {m.get("session_id"): s for s, m in _metas(unified)}
            sid = args.session_id
            if args.last:
                rows = archived_sessions(unified)
                if not rows:
                    print("no archived sessions")
                    return 0
                sid = rows[0][0]
            if sid not in sessions:
                print(f"error: no session {sid!r}", file=sys.stderr)
                return 1
            restore(sessions[sid])
        else:
            rows = archived_sessions(unified)
            if not rows:
                print("no archived sessions")
            for sid, title, at in rows[:LIST_LIMIT]:
                print(f"{sid}  {at}  {title or 'untitled'}")
    return 0


def _metas(unified: Path):
    for session in unified.iterdir():
        m = session / "meta.json"
        if m.is_file():
            try:
                yield session, read_meta(session)
            except (OSError, ValueError):
                continue


if __name__ == "__main__":
    raise SystemExit(main())
