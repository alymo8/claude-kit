"""Structure tests for the pr-review-respond skill."""

from __future__ import annotations

from helpers import PLUGIN

SKILL = PLUGIN / "skills" / "pr-review-respond" / "SKILL.md"


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def body():
    return SKILL.read_text(encoding="utf-8").split("---", 2)[2]


def test_frontmatter():
    front = frontmatter(SKILL.read_text(encoding="utf-8"))
    assert front["name"] == "pr-review-respond"
    assert front["description"].startswith("Use when")
    assert len(front["description"]) <= 1024
    assert front.get("argument-hint")


def test_body_names_the_steps_and_tools():
    text = body()
    for needle in (
        "review-threads.py",
        "superpowers:receiving-code-review",
        "AskUserQuestion",
        "clarify",
        "Never resolve",
        "/replies",
        "gh pr checks --watch",
    ):
        assert needle in text, needle
    assert "untrusted" in text.lower()


def test_body_never_bypasses_hooks():
    assert "--no-verify" not in SKILL.read_text(encoding="utf-8")
