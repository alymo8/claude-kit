"""Structure tests for the audit and audit-deep skills."""

from __future__ import annotations

from helpers import PLUGIN, load_module

SKILLS = PLUGIN / "skills"
AUDIT = SKILLS / "audit"
DEEP = SKILLS / "audit-deep"
CHECKER_REL = "../../scripts/check-findings.py"

cf = load_module(PLUGIN / "scripts" / "check-findings.py", "check_findings_s")


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def read(path):
    return path.read_text(encoding="utf-8")


def test_audit_frontmatter():
    front = frontmatter(AUDIT / "SKILL.md")
    assert front["name"] == "audit"
    assert front["description"].startswith("Use when")
    assert len(front["description"]) <= 1024
    assert "disable-model-invocation" not in front


def test_rules_define_the_checker_format():
    rules = read(AUDIT / "rules.md")
    for field in cf.FIELDS:
        assert f"**{field}:**" in rules
    for severity in cf.SEVERITIES:
        assert severity in rules
    assert "(absent)" in rules
    assert "(history <sha>)" in rules
    assert "Does it work" in rules and "Is it built well" in rules


def test_rules_point_at_the_checker():
    rules = read(AUDIT / "rules.md")
    assert CHECKER_REL in rules
    assert (AUDIT / CHECKER_REL).resolve().is_file()


def test_audit_skill_uses_rules_and_names_its_output():
    body = read(AUDIT / "SKILL.md")
    assert "rules.md" in body
    assert "docs/audit/audit.md" in body
    assert "## What is missing" in body
    assert "## Fix first" in body
    assert "$ARGUMENTS" in body


def test_no_hand_made_conventions_file():
    for path in SKILLS.glob("audit*/**/*.md"):
        assert "CLAUDE.md.local" not in read(path), path


PHASES = [
    "A-map.md",
    "B-quality.md",
    "C-context.md",
    "D-security.md",
    "E-design.md",
    "F-onboarding.md",
    "G-report.md",
]
OUTPUTS = [
    "00-repo-map.md",
    "01-product.md",
    "02-quality.md",
    "03-context-engineering.md",
    "04-security.md",
    "05-design.md",
    "06-onboarding.md",
    "report.html",
]


def test_deep_frontmatter():
    front = frontmatter(DEEP / "SKILL.md")
    assert front["name"] == "audit-deep"
    assert front["description"].startswith("Use when")
    assert len(front["description"]) <= 1024
    assert front["disable-model-invocation"] == "true"


def test_deep_references_resolve():
    body = read(DEEP / "SKILL.md")
    assert "../audit/rules.md" in body
    assert (DEEP / "../audit/rules.md").resolve().is_file()
    assert CHECKER_REL in body
    assert (DEEP / CHECKER_REL).resolve().is_file()


def test_every_phase_file_exists_and_is_referenced():
    body = read(DEEP / "SKILL.md")
    on_disk = sorted(p.name for p in (DEEP / "phases").glob("*.md"))
    assert on_disk == sorted(PHASES)
    for name in PHASES:
        assert name in body, name


def test_deep_names_every_output():
    body = read(DEEP / "SKILL.md")
    for name in OUTPUTS:
        assert name in body, name


def test_deep_stops_after_the_map():
    body = read(DEEP / "SKILL.md")
    assert "**stop**" in body.lower()


def test_area_phases_end_with_missing_and_top_10():
    for name in PHASES[1:5]:
        text = read(DEEP / "phases" / name)
        assert "## What is missing" in text, name
        assert "## Top 10" in text, name


def test_report_phase_is_offline_and_source_blind():
    text = read(DEEP / "phases" / "G-report.md")
    assert "No CDN" in text
    assert "Do not read the source" in text
