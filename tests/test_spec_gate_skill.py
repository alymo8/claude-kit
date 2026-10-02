"""Structure tests for the spec-gate skill."""

from __future__ import annotations

from helpers import PLUGIN, REPO

GATE = PLUGIN / "skills" / "spec-gate"
LINTER_REL = "../../scripts/spec-lint.py"


def read(name):
    return (GATE / name).read_text(encoding="utf-8")


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_frontmatter():
    front = frontmatter(read("SKILL.md"))
    assert front["name"] == "spec-gate"
    assert front["description"].startswith("Use when")
    assert len(front["description"]) <= 1024
    assert "disable-model-invocation" not in front


def test_skill_uses_linter_rubric_and_records():
    body = read("SKILL.md")
    assert LINTER_REL in body and (GATE / LINTER_REL).resolve().is_file()
    assert "rubric.md" in body
    assert "--hash" in body
    assert "docs/superpowers/gates/" in body
    assert "- **Spec SHA-256:**" in body and "- **Verdict:**" in body
    assert "3 rounds" in body


def test_rubric_defines_finding_format_and_probes():
    rubric = read("rubric.md")
    for heading in (
        "### [blocking]",
        "### [minor]",
        "## Dry-run plan",
        "## Key decisions",
    ):
        assert heading in rubric
    for field in ("**Line:**", "**Problem:**", "**Fix:**"):
        assert field in rubric
    assert "more than 15 tasks" in rubric


CLASSES = (
    "wrong-build",
    "contradiction",
    "false-claim",
    "uncheckable",
    "open-what",
    "too-large",
)


def test_rubric_limits_blocking_to_classes_and_adds_plan_severity():
    rubric = read("rubric.md")
    for text in ("### [plan]", "**Class:**", "**Question:**", "six classes"):
        assert text in rubric
    for name in CLASSES:
        assert f"`{name}`" in rubric


def test_verify_rubric_is_scoped_to_the_diff():
    verify = read("verify.md")
    for text in (
        "## Fixes",
        "## Findings",
        "### [blocking]",
        "## Decisions changed",
        "outside the diff",
        "not resolved",
    ):
        assert text in verify


def test_docs_wire_the_gate():
    def text(rel):
        return (REPO / rel).read_text(encoding="utf-8")

    assert "claude-kit:spec-gate" in text("CLAUDE.md")
    assert "## Spec gate" in text("conventions/spec-driven-development.md")
    adr = "0015-spec-gate-replaces-full-read.md"
    assert (REPO / "knowledge" / "decisions" / adr).is_file()
    assert f"]({adr})" in text("knowledge/decisions/README.md")
