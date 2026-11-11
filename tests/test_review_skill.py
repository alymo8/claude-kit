from helpers import PLUGIN, REPO

REVIEW = PLUGIN / "skills" / "review"
SMELLS = (
    "Mysterious Name",
    "Duplicated Code",
    "Feature Envy",
    "Data Clumps",
    "Primitive Obsession",
    "Repeated Switches",
    "Shotgun Surgery",
    "Divergent Change",
    "Speculative Generality",
    "Message Chains",
    "Middle Man",
    "Refused Bequest",
)
SURGICAL_RULES = (
    "Trace every line",
    "Mention unrelated dead code",
    "Remove only your own leftovers",
    "Nothing speculative",
    "Deleting is a win",
    "Ask during design",
)


def read(name):
    return (REVIEW / name).read_text(encoding="utf-8")


def flat(name):
    return " ".join(read(name).split())


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_frontmatter():
    front = frontmatter(read("SKILL.md"))
    assert front["name"] == "review"
    assert front["description"].startswith("Use when")
    assert "/ship" in front["description"]
    assert len(front["description"]) <= 1024
    assert front["argument-hint"] == "[base-ref] [spec.md] [plan.md]"
    assert "disable-model-invocation" not in front


def test_skill_dispatches_both_reviewers_in_one_message():
    text = flat("SKILL.md")
    for phrase in (
        "standards-reviewer.md",
        "spec-reviewer.md",
        "in one message",
        "general-purpose",
        "## Standards",
        "## Spec",
        "git diff <base>...HEAD",
        "origin/main",
        "Spec: no spec found",
        "never merged or reranked",
    ):
        assert phrase in text, phrase


def test_skill_runs_frozen_check_before_dispatch():
    text = flat("SKILL.md")
    for phrase in (
        "frozen-check.py",
        "--base <base>",
        "~/.claude/skills/claude-kit/scripts/frozen-check.py",
        "Frozen: skipped (no spec or plan)",
    ):
        assert phrase in text, phrase
    assert text.index("frozen-check.py") < text.index("in one message")


def test_process_files_are_never_scope_creep():
    text = flat("SKILL.md")
    for phrase in (
        "never scope creep",
        "gate records",
        "ADRs",
        "docs/superpowers/README.md",
        "Capture learnings",
    ):
        assert phrase in text, phrase
    assert "never scope creep" in flat("spec-reviewer.md")


def test_standards_reviewer_baseline():
    text = flat("standards-reviewer.md")
    for phrase in (
        *SMELLS,
        *SURGICAL_RULES,
        "`hard`",
        "`judgement`",
        "wins over the baseline",
        "linter or formatter",
        "frozen: changed",
        "<frozen-check output>",
        "Under 400 words",
    ):
        assert phrase in text, phrase


def test_spec_reviewer_axes():
    text = flat("spec-reviewer.md")
    for phrase in (
        "missing or partial",
        "scope creep",
        "implemented but wrong",
        "Quote the spec line",
        "Under 400 words",
        "<spec path>",
    ):
        assert phrase in text, phrase


def collapsed(path):
    return " ".join(path.read_text(encoding="utf-8").split())


def test_engineering_practices_name_the_surgical_rules():
    text = collapsed(REPO / "conventions" / "engineering-practices.md")
    for phrase in (
        "### Surgical diffs and simplicity",
        *(f"**{name}.**" for name in SURGICAL_RULES),
        "The diff is surgical: every changed line traces to the spec or task.",
        "No dead or commented-out code introduced by the change.",
        "no dead code introduced by the change",
        "ADR 0044",
    ):
        assert phrase in text, phrase


def test_knowledge_layer_names_the_reviewer_only_file():
    text = collapsed(REPO / "conventions" / "knowledge-layer.md")
    assert "knowledge/review-standards.md" in text
    assert "never link it from `CLAUDE.md`" in text


ADRS = (
    "0041-two-axis-review-in-ship.md",
    "0042-frozen-evaluator-diff-check.md",
    "0043-harden-in-capture-learnings.md",
    "0044-surgical-diffs-and-simplicity.md",
    "0045-merge-danger-in-pr-bodies.md",
)


def test_adrs_exist_and_are_indexed():
    decisions = REPO / "knowledge" / "decisions"
    index = (decisions / "README.md").read_text(encoding="utf-8")
    for adr in ADRS:
        assert (decisions / adr).is_file(), adr
        assert f"]({adr})" in index, adr
    assert "0037" in (decisions / ADRS[0]).read_text(encoding="utf-8")


def test_readme_names_the_review_skill_and_frozen_check():
    readme = " ".join((REPO / "README.md").read_text(encoding="utf-8").split())
    assert "`review`" in readme and "frozen-check.py" in readme
