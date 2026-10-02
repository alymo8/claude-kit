"""Structure tests for the grill skill."""

from __future__ import annotations

import re

from helpers import PLUGIN

GRILL = PLUGIN / "skills" / "grill"
AREAS = [
    "Purpose and success",
    "Scope boundary",
    "Interfaces",
    "Data and irreversible actions",
    "Failure modes",
    "Security and secrets",
    "Testing",
    "Rollout and compatibility",
    "Docs and decisions",
]


def read(name):
    return (GRILL / name).read_text(encoding="utf-8")


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_frontmatter():
    front = frontmatter(read("SKILL.md"))
    assert front["name"] == "grill"
    assert front["description"].startswith("Use when")
    assert len(front["description"]) <= 1024
    assert front["argument-hint"] == "[topic]"
    assert "disable-model-invocation" not in front


def test_body_defines_the_procedure():
    body = read("SKILL.md")
    for phrase in ("➡️", "shared understanding", "coverage.md", "MIT"):
        assert phrase in body, phrase
    assert "mattpocock/skills" in body


def test_coverage_lists_the_nine_areas_in_order():
    text = read("coverage.md")
    areas_section = text.split("\n## Areas\n", 1)[1].split("\n## ", 1)[0]
    found = re.findall(r"^- \*\*([^*]+?):\*\*", areas_section, re.M)
    assert found == AREAS
