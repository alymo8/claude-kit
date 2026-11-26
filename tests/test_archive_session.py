"""Tests for archive-session.py (finding and archiving the session)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module

MOD = load_module(PLUGIN / "scripts" / "archive-session.py", "archive_session")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+00:00$")


def make_session(
    root: Path, sid: str, *, title=None, archived_at=None, token=None, live_only=False
):
    d = root / "unified" / sid
    (d / "chunks").mkdir(parents=True)
    (d / "journal").mkdir()
    meta = {
        "session_id": sid,
        "title": title,
        "archived_at": archived_at,
        "environment": {"working_directory": "C:\\repo"},
    }
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    body = json.dumps({"tool_result": f"ran {token}"}).encode() if token else b"{}"
    # The live journal receives within-turn writes, chunks turn boundaries.
    (d / "journal" / "0000000000000001.jsonl").write_bytes(body)
    (d / "chunks" / "c1.json").write_bytes(body if not live_only else b"{}")
    return d


@pytest.fixture
def root(tmp_path: Path) -> Path:
    make_session(tmp_path, "11111111-1111-1111-1111-111111111111", title="other")
    make_session(
        tmp_path, "22222222-2222-2222-2222-222222222222", title="mine", token=None
    )
    return tmp_path


def test_token_format():
    tok = MOD.make_token()
    assert tok.startswith("kit-archive-")
    assert re.fullmatch(r"kit-archive-[0-9a-f]{32}", tok)


def test_root_missing_exits(tmp_path):
    with pytest.raises(SystemExit) as exc:
        MOD.sessions_root(tmp_path)
    assert exc.value.code == 1


def test_find_session_by_token(root):
    tok = MOD.make_token()
    mine = make_session(root, "33333333-3333-3333-3333-333333333333", token=tok)
    found = MOD.find_session_by_token(root / "unified", tok, time.time())
    assert found == mine


def test_find_session_by_token_only_in_live_journal(root):
    tok = MOD.make_token()
    mine = make_session(
        root, "cccccccc-cccc-cccc-cccc-cccccccccccc", token=tok, live_only=True
    )
    found = MOD.find_session_by_token(root / "unified", tok, time.time())
    assert found == mine


def test_find_rejects_foreign_token(root):
    with pytest.raises(SystemExit):
        MOD.find_session_by_token(root / "unified", "not-a-token", time.time())


def test_find_missing_token_exits(root):
    with pytest.raises(SystemExit):
        MOD.find_session_by_token(root / "unified", MOD.make_token(), time.time())


def test_archive_sets_iso_stamp_and_keeps_fields(root):
    mine = make_session(root, "44444444-4444-4444-4444-444444444444")
    MOD.archive(mine)
    meta = MOD.read_meta(mine)
    assert ISO.match(meta["archived_at"])
    assert meta["title"] is None
    assert meta["environment"]["working_directory"] == "C:\\repo"


def test_archive_twice_is_idempotent(root):
    mine = make_session(root, "55555555-5555-5555-5555-555555555555")
    MOD.archive(mine)
    first = MOD.read_meta(mine)["archived_at"]
    MOD.archive(mine)
    assert MOD.read_meta(mine)["archived_at"] == first


def test_restore_clears_and_stays_cleared(root):
    mine = make_session(
        root,
        "66666666-6666-6666-6666-666666666666",
        archived_at="2026-11-25T21:09:38.632987+00:00",
    )
    MOD.restore(mine)
    MOD.restore(mine)
    assert MOD.read_meta(mine)["archived_at"] is None


def test_archived_sessions_sorted_newest_first(root):
    make_session(
        root,
        "77777777-7777-7777-7777-777777777777",
        title="older",
        archived_at="2026-11-24T00:00:00+00:00",
    )
    make_session(
        root,
        "88888888-8888-8888-8888-888888888888",
        title="newer",
        archived_at="2026-11-25T00:00:00+00:00",
    )
    rows = MOD.archived_sessions(root / "unified")
    assert [r[1] for r in rows] == ["newer", "older"]


def test_main_archive_and_restore_last(root, capsys):
    tok = MOD.make_token()
    make_session(root, "99999999-9999-9999-9999-999999999999", title="me", token=tok)
    assert MOD.main(["--root", str(root), "archive", "--token", tok]) == 0
    assert "archived 99999999" in capsys.readouterr().out
    newest = make_session(root, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", title="newest")
    meta = MOD.read_meta(newest)
    meta["archived_at"] = "2999-01-01T00:00:00+00:00"
    MOD.write_meta(newest, meta)
    capsys.readouterr()
    assert MOD.main(["--root", str(root), "restore", "--last"]) == 0
    out = capsys.readouterr().out
    assert "restored aaaaaaaa" in out


def test_main_restore_lists_candidates(root, capsys):
    make_session(
        root,
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        title="pick me",
        archived_at="2026-11-25T12:00:00+00:00",
    )
    assert MOD.main(["--root", str(root), "restore"]) == 0
    out = capsys.readouterr().out
    assert "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" in out
    assert "pick me" in out


def test_main_token_prints_only_the_token(root, capsys):
    assert MOD.main(["--root", str(root), "token"]) == 0
    out = capsys.readouterr().out.strip()
    assert re.fullmatch(r"kit-archive-[0-9a-f]{32}", out)
