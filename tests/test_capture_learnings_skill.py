"""Structure tests for the capture-learnings skill."""

from __future__ import annotations

from helpers import PLUGIN

SKILL = PLUGIN / "skills" / "capture-learnings" / "SKILL.md"


def body():
    return SKILL.read_text(encoding="utf-8")


def flat():
    """The body with all whitespace runs collapsed, so wrapped phrases match."""
    return " ".join(body().split())


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_frontmatter():
    front = frontmatter(body())
    assert front["name"] == "capture-learnings"
    assert front["description"].startswith("Use when")
    assert "/ship" in front["description"]
    assert "/ship-fast" in front["description"]
    assert "disable-model-invocation" not in front


def test_routes_every_kind():
    text = flat()
    for needle in ("CLAUDE.md", "knowledge/", "knowledge/decisions/", "MEMORY.md"):
        assert needle in text, needle


def test_none_is_a_valid_result():
    text = flat()
    assert "`none`" in text
    assert "write nothing" in text
    assert "dropped candidate" in text
    assert "rule that dropped it" in text


def test_never_writes_secrets():
    text = flat().lower()
    for needle in ("secrets", "personal data", "private repos"):
        assert needle in text, needle


def test_commits_on_the_feature_branch():
    text = flat()
    assert "`Capture learnings`" in text
    assert "feature branch" in text
    assert "Auto-memory writes are not committed" in text


def test_missing_homes_have_fallbacks():
    text = flat()
    assert "0000-template.md" in text
    assert "no `knowledge/` folder" in text
    assert "no `knowledge/decisions/` folder" in text
    assert "`poc/`" in text


def test_claude_md_limit_is_exact():
    text = flat()
    assert "more than 100 lines" in text


def test_rerun_writes_nothing_new():
    text = flat()
    assert "already recorded at its destination" in text
    assert "no commit" in text


def test_memory_index_is_reread_before_adding():
    text = flat()
    assert "re-read `MEMORY.md`" in text


def test_adr_gets_an_index_row():
    text = flat()
    assert "knowledge/decisions/README.md" in text
    assert "index row" in text


def test_mines_subagent_reports_and_handoff():
    text = flat()
    assert "subagent" in text
    assert ".claude/handoffs/" in text
