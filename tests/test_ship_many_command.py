"""Structure tests for the /ship-many command."""

from __future__ import annotations

from helpers import PLUGIN, REPO

SHIP_MANY = (PLUGIN / "commands" / "ship-many.md").read_text(encoding="utf-8")
SHIP_CHILD = (PLUGIN / "scripts" / "ship-child.py").read_text(encoding="utf-8")


def section(title, until):
    return SHIP_MANY.split(title, 1)[1].split(until, 1)[0]


def step(n):
    rest = SHIP_MANY.split(f"{n}. **", 1)[1]
    return rest.split(f"{n + 1}. **", 1)[0]


def test_user_only_frontmatter():
    front = SHIP_MANY.split("---", 2)[1]
    assert "disable-model-invocation: true" in front
    assert "description:" in front


def test_child_command_and_defaults():
    for needle in (
        '"/claude-kit:ship ',
        '"--permission-mode"',
        '"auto"',
        '"--permission-prompts"',
        '"none"',
        '"--output-format"',
        '"json"',
        "CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS",
    ):
        assert needle in SHIP_CHILD, needle
    assert "default 3" in SHIP_MANY and "limits concurrent specs only" in SHIP_MANY
    assert "2.1.259" in SHIP_MANY


def test_step_4_launches_the_runner():
    text = step(4)
    for needle in ("ship-child.py", "--spec", "--main", "--log", "--name"):
        assert needle in text, needle
    for quoted in (
        '--spec "<spec>"',
        '--main "<main checkout>"',
        '--log "<log>"',
        '--name "<log-name>"',
    ):
        assert quoted in text, quoted
    assert "not enforced" in text
    assert "`-2`" not in text


def test_step_2_excludes_duplicate_slugs():
    assert "`duplicate slug`" in step(2)


def test_step_5_reads_status_file():
    text = step(5)
    for needle in ("status.json", "attempts", "timed_out"):
        assert needle in text, needle
    assert "number of entries in the `attempts` list" in " ".join(text.split())


def test_step_6_drops_timed_out_recheck():
    text = step(6)
    assert "may still be running" not in text
    assert "look up its PR once more" not in text
    assert "attempts" in text and "2 (resumed)" in text
    assert "`unknown`" in text


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
