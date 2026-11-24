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


def test_adr_number_accounts_for_origin_main():
    text = flat()
    assert "git fetch origin" in text
    assert "`origin/main`" in text
    assert "highest number" in text


def test_overflow_creates_knowledge_when_missing():
    text = flat()
    assert "create `knowledge/<topic>.md` for the overflow" in text


def test_resume_reports_earlier_learnings():
    text = flat()
    assert "already has a `Capture learnings` commit" in text
    assert "already written:" in text


def test_harden_step_sits_between_route_and_commit():
    text = flat()
    assert (
        text.index("3. **Route**")
        < text.index("4. **Prune.**")
        < text.index("5. **Harden.**")
        < text.index("6. **Write and commit.**")
        < text.index("7. **Return**")
    )


def test_harden_classifies_mistakes():
    text = flat()
    for needle in (
        "**Mechanical:**",
        "**Judgement call:**",
        "harden (mechanical):",
        "harden (steering):",
        "harden (navigation):",
        "knowledge/review-standards.md",
        "## Rules",
        "status: stable",
        "Hardening:",
        "Hardening: none",
        "CI failure",
    ):
        assert needle in text, needle


def test_steering_scan_does_not_edit():
    assert "Do not edit these files for this scan." in flat()


def test_standards_file_is_never_linked_from_claude_md():
    assert "Never link this file from `CLAUDE.md`" in flat()


def test_mechanical_proposals_are_built_only_on_a_hand_run():
    assert frontmatter(body())["argument-hint"] == "[--auto]"
    text = flat()
    for needle in (
        "## Mode",
        "--auto",
        "/ship-many",
        "only on a yes",
        "separate commit",
    ):
        assert needle in text, needle


def test_stub_claude_md_routes_to_agents_md():
    text = flat()
    assert "is only `@AGENTS.md`" in text
    assert "write to the root `AGENTS.md` instead" in text


def test_description_mentions_pruning():
    description = frontmatter(body())["description"]
    assert "prunes entries the feature made stale" in description


def test_prune_reads_the_feature_diff():
    assert "`git diff --name-status origin/main...HEAD`" in flat()


def test_prune_reads_origin_main():
    text = flat().split("4. **Prune.**", 1)[1].split("5. **Harden.**", 1)[0]
    assert "git show origin/main:<path>" in text
    assert "already fixed there" in text


def test_prune_skips_adrs():
    text = flat()
    assert "`knowledge/decisions/` excluded" in text
    assert "ADRs are never edited" in text
    assert "not written: ADR <NNNN> may be superseded: <why>" in text


def test_prune_never_edits_feedback_or_user_memory():
    text = flat()
    assert "`type: feedback` and `type: user`: never edit or delete" in text
    assert "not written: memory <file> may conflict: <why>" in text
    assert "only when nothing in it stays true" in text


def test_prune_memory_edits_are_exact_replacements():
    text = flat()
    assert "exact replacement" in text
    assert "re-reading the file right before each edit" in text


def test_prune_stays_within_the_diff():
    text = flat()
    assert "leave it alone, even if it looks stale for another reason" in text


def test_prune_spares_this_runs_learnings():
    assert "Never prune a learning routed in step 3 of this run" in flat()


def test_prune_follows_agents_md_stub():
    text = flat().split("4. **Prune.**", 1)[1].split("5. **Harden.**", 1)[0]
    assert "only `@AGENTS.md`" in text


def test_none_needs_no_repo_or_memory_prune():
    assert "nothing was pruned in the repo or in memory" in flat()


def test_prune_has_no_approval_pause():
    text = flat().split("4. **Prune.**", 1)[1].split("5. **Harden.**", 1)[0]
    assert "with and without `--auto`" in text


def test_summary_reports_prune_edits():
    text = flat()
    assert "`pruned: <file>: <old entry, shortened> → <new entry | removed>`" in text
    assert "`memory: <file>: <resolved | rewritten | deleted>: <why>`" in text
    assert "no learning was written and nothing was pruned" in text
