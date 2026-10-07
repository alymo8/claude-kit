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


def test_cleanup_waits_for_the_user():
    # The run hands over a running POC; cleanup runs only on request.
    steps = SHIP_FAST.split("## Steps", 1)[1].split("## Cleanup (on request)", 1)
    assert len(steps) == 2, "missing Cleanup (on request) section"
    run, cleanup = steps
    assert "worktree remove" not in run and "branch -D" not in run
    assert "worktree remove" in cleanup and "branch -D" in cleanup
    assert "**Hand over.**" in run and "leave it running" in run
    assert "Do not suggest cleaning up in the report" in run
    assert "tested the app or finished presenting" in run
    assert "ask before removing anything" in cleanup
    assert ".docker-baseline.txt" in SHIP_FAST


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


def test_review_fixes_for_edge_paths():
    # Risky stop keeps its question; early stops need no repo; title line;
    # early non-interactive check; Home is confirmed; idea text ending in .md.
    for needle in (
        "before `## Decisions` is written",
        "without a handoff",
        "single token",
        "a `# <title>` line",
        "At the start of step 0",
        "the grill summary names Home",
    ):
        assert needle in SHIP_FAST, needle
