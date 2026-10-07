"""Structure tests for the /ship-fast command."""

from __future__ import annotations

from helpers import PLUGIN

SHIP_FAST = (PLUGIN / "commands" / "ship-fast.md").read_text(encoding="utf-8")


def test_frontmatter_is_user_only():
    assert SHIP_FAST.startswith("---\n")
    front = SHIP_FAST.split("---", 2)[1]
    assert "description:" in front
    assert "disable-model-invocation: true" in front


def test_no_gates_no_review_round_no_merge():
    for needle in ("spec-gate", "plan-gate", "gh pr merge", "requesting-code-review"):
        assert needle not in SHIP_FAST, needle


def test_names_its_pieces():
    for needle in (
        "parallel-plan.py",
        "claude-kit:parallel-tasks",
        "code-review",
        "low --fix",
        "origin/main",
        "poc/<slug>",
        "gh repo create",
        "--private",
        "**Repo:** new",
        "Assumptions",
        "Success criteria",
        "gh pr checks --watch",
        "scaffold.py",
    ):
        assert needle in SHIP_FAST, needle


def test_resume_and_cleanup():
    assert "## Resume" in SHIP_FAST
    assert ".claude/handoffs/poc_<slug>.md" in SHIP_FAST


def test_review_fixes_are_pinned():
    # Workspace pre-flight is waived, parallel-tasks' own review is skipped,
    # CI presence is read from workflow files, and resume needs the spec copy.
    assert "pre-flight branch" in SHIP_FAST
    assert "skip its final whole-branch" in SHIP_FAST
    assert ".github/workflows/*.yml" in SHIP_FAST
    assert "name collision" in SHIP_FAST
    assert "--no-workspace" in SHIP_FAST


PRODUCT_AREAS = (
    "Users and outcome",
    "Core flows",
    "In and cut",
    "Data",
    "States and wording",
    "Acceptance criteria",
    "Home",
)


def test_spec_phase():
    for needle in (
        "superpowers:brainstorming",
        "claude-kit:grill",
        "at most 7",
        "Assumed (not asked)",
        "[spec.md | idea]",
        "~/.claude/ship-fast-specs/",
        "visual-companion",
        *PRODUCT_AREAS,
    ):
        assert needle in SHIP_FAST, needle


def test_input_rules():
    assert "names no existing file" in SHIP_FAST
    assert "newest" not in SHIP_FAST


def test_decisions_round():
    for needle in (
        "Decisions round",
        "## Decisions",
        "at most 3",
        "**Product:**",
        "**Engineering:**",
        "- none new",
    ):
        assert needle in SHIP_FAST, needle


def test_questions_rules():
    for needle in (
        "risky engineering choice",
        "does not end",
        "AskUserQuestion",
        "non-interactive",
        "Progress lines",
        "including step 3b",
    ):
        assert needle in SHIP_FAST, needle


def test_old_stop_rule_and_repo_deletion_absent():
    assert "changes scope, product behaviour" not in SHIP_FAST
    assert "gh repo delete" not in SHIP_FAST
    assert "Never delete a repository" in SHIP_FAST
