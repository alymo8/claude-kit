"""Structure tests for the /archive-session command."""

from __future__ import annotations

from helpers import PLUGIN

TEXT = (PLUGIN / "commands" / "archive-session.md").read_text(encoding="utf-8")
FLAT = " ".join(TEXT.replace("`", "").split())


def test_frontmatter_user_only():
    front = TEXT.split("---", 2)[1]
    assert TEXT.startswith("---\n") and "description:" in front
    assert "disable-model-invocation: true" in front


def test_runs_the_script_for_each_step():
    for needle in (
        'archive-session.py" token',
        'archive-session.py" archive --token TOKEN',
        'archive-session.py" restore',
        'archive-session.py" status --token TOKEN',
    ):
        assert needle in FLAT, needle
    assert '"${CLAUDE_PLUGIN_ROOT}/scripts/archive-session.py"' in TEXT


def test_token_two_pass_and_no_user_wait():
    token_at = FLAT.index('archive-session.py" token')
    archive_at = FLAT.index('archive-session.py" archive --token TOKEN')
    assert token_at < archive_at
    assert "back to back" in FLAT


def test_restore_asks_the_user():
    restore_at = FLAT.index('archive-session.py" restore')
    list_at = FLAT.index("ask the user which to restore")
    assert list_at < restore_at + 200
    assert "Do not guess" in FLAT


def test_explains_reversible_and_vibe_only():
    assert "stays usable" in FLAT or "restore brings the conversation back" in FLAT
    assert "works only in Mistral Vibe" in FLAT
    assert "Nothing was deleted" in FLAT
