"""Structure tests for the parallel-tasks skill."""

from __future__ import annotations

from helpers import PLUGIN

SKILL = PLUGIN / "skills" / "parallel-tasks" / "SKILL.md"
SCRIPT_REL = "../../scripts/parallel-plan.py"


def body():
    return SKILL.read_text(encoding="utf-8")


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_frontmatter():
    front = frontmatter(body())
    assert front["name"] == "parallel-tasks"
    assert front["description"].startswith("Use when")
    assert "disable-model-invocation" not in front


def test_skill_names_its_commands():
    text = body()
    assert SCRIPT_REL in text and (SKILL.parent / SCRIPT_REL).resolve().is_file()
    for needle in (
        "git worktree add",
        "git merge --no-ff",
        "git worktree remove --force",
        "git branch -D",
        "superpowers:executing-plans",
        "git log --merges --format=%P",
        "git rev-list --count",
    ):
        assert needle in text, needle


def test_subagent_prompt_has_the_lock_retry():
    prompt = body().split("only this prompt", 1)[1]
    assert "Unable to create '...lock': File exists" in prompt
    assert "cannot lock ref" in prompt


def test_resume_skips_complete_tasks():
    assert "complete` ledger line" in body()
