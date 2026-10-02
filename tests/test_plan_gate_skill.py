"""Structure tests for the plan-gate skill."""

from __future__ import annotations

import json

from helpers import PLUGIN, REPO

GATE = PLUGIN / "skills" / "plan-gate"
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
    assert front["name"] == "plan-gate"
    assert front["description"].startswith("Use when")
    assert len(front["description"]) <= 1024
    assert "disable-model-invocation" not in front


def test_skill_uses_linter_rubric_and_records():
    body = read("SKILL.md")
    assert LINTER_REL in body and (GATE / LINTER_REL).resolve().is_file()
    assert "rubric.md" in body
    assert "--hash" in body and "--verify-record" in body
    assert "docs/superpowers/gates/plans/" in body
    for field in (
        "- **Plan SHA-256:**",
        "- **Spec SHA-256:**",
        "- **Verdict:**",
        "- **Decisions approved:**",
    ):
        assert field in body
    assert "pass-with-decisions" in body
    assert "3 discovery rounds" in body
    assert "../spec-gate/verify.md" in body
    assert (GATE / "../spec-gate/verify.md").resolve().is_file()
    for text in (
        "verification round",
        "Plan questions",
        "## Decisions changed",
        "3 discovery + 2 verification",
        "skip verification",
        "runs steps 1–6 only",
    ):
        assert text in body
    assert "3 discovery rounds" in frontmatter(body)["description"]
    assert "P4-spec-gated" in body


def test_rubric_defines_finding_format_and_probes():
    rubric = read("rubric.md")
    for heading in (
        "## Coverage",
        "## Findings",
        "### [blocking]",
        "### [minor]",
        "## Plan-introduced decisions",
    ):
        assert heading in rubric
    for field in ("**Line:**", "**Problem:**", "**Fix:**"):
        assert field in rubric
    for probe in ("Cold execution", "Order", "Code claims", "scope creep"):
        assert probe in rubric
    assert "Plan questions" in rubric


def test_docs_and_manifest_wire_the_gate():
    def text(rel):
        return (REPO / rel).read_text(encoding="utf-8")

    assert "## Plan gate" in text("conventions/spec-driven-development.md")
    adr = "0016-plan-gate-signs-off-on-new-decisions-only.md"
    assert (REPO / "knowledge" / "decisions" / adr).is_file()
    assert f"]({adr})" in text("knowledge/decisions/README.md")
    manifest = json.loads(text("plugin/.claude-plugin/plugin.json"))
    version = tuple(int(part) for part in manifest["version"].split("."))
    assert version >= (0, 7, 0)
    assert "spec and plan gates" in manifest["description"]
