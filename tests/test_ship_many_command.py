"""Structure tests for the /ship-many command."""

from __future__ import annotations

from helpers import PLUGIN, REPO

SHIP_MANY = (PLUGIN / "commands" / "ship-many.md").read_text(encoding="utf-8")


def section(title, until):
    return SHIP_MANY.split(title, 1)[1].split(until, 1)[0]


def test_user_only_frontmatter():
    front = SHIP_MANY.split("---", 2)[1]
    assert "disable-model-invocation: true" in front
    assert "description:" in front


def test_child_command_and_defaults():
    flags = "--permission-mode auto --permission-prompts none --output-format json"
    assert f'claude -p "/claude-kit:ship <spec>" {flags}' in SHIP_MANY
    assert "default 3" in SHIP_MANY and "limits concurrent specs only" in SHIP_MANY
    assert "2.1.259" in SHIP_MANY


def test_dry_run_never_gates():
    assert "--dry-run" in SHIP_MANY
    assert "Never run the gate" in SHIP_MANY


def test_exclusions_and_paths():
    for needle in (
        "not found",
        "outside the main checkout",
        "not in this repository",
        "rev-parse --show-toplevel",
        "`duplicate`",
        "`duplicate title`",
        "relative to the main checkout",
        "ExitWorktree",
        "git worktree list --porcelain",
    ):
        assert needle in SHIP_MANY, needle


def test_collect_and_status_order():
    assert "--json url,title,state,mergeCommit,headRefName,createdAt" in SHIP_MANY
    assert "createdAt" in SHIP_MANY
    order = [SHIP_MANY.index(f"`{s}`") for s in ("merged", "timed out", "stopped")]
    assert order == sorted(order)
    assert "`excluded`" in SHIP_MANY
    assert "look up its PR once more" in SHIP_MANY
    finish = SHIP_MANY.split("6. **Finish.**", 1)[1]
    assert "set the status to `merged`" in finish


def test_scripts_named():
    assert "spec-lint.py" in SHIP_MANY and "--verify-record" in SHIP_MANY
    assert "parallel-plan.py" in SHIP_MANY and " specs " in SHIP_MANY
    assert "claude-kit:spec-gate" in SHIP_MANY


def test_five_stop_rules():
    stops = section("## Stop rules", "## Steps")
    bullets = [line for line in stops.splitlines() if line.startswith("- ")]
    assert len(bullets) == 5
    for needle in (
        "2.1.259",
        "git fetch origin",
        "below 1",
        "Every spec is excluded",
        "exits non-zero",
    ):
        assert needle in stops, needle


def test_exact_title_match():
    assert "equals the recorded title exactly" in SHIP_MANY


def test_docs_wire_ship_many():
    assert "/ship-many" in (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    adr = "0018-ship-many-headless-children.md"
    assert (REPO / "knowledge" / "decisions" / adr).is_file()
    index = (REPO / "knowledge" / "decisions" / "README.md").read_text(encoding="utf-8")
    assert f"]({adr})" in index


def test_dry_run_is_read_only_except_fetch():
    assert "read-only except for `git fetch`" in SHIP_MANY
