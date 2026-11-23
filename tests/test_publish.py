"""Tests for publishing the kit as an installable plugin (agent-kit)."""

from __future__ import annotations

import json
import subprocess

from helpers import PLUGIN, REPO

MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"


def test_marketplace_fields():
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert data["name"] == "agent-kit"
    assert data["owner"]["name"] == "alymo8"
    [entry] = data["plugins"]
    assert entry["name"] == "agent-kit"
    assert entry["source"] == "./plugin"
    assert entry["description"].strip()
    assert "version" not in entry


def test_marketplace_file_is_tracked():
    out = subprocess.run(
        ["git", "ls-files", ".claude-plugin/marketplace.json"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.strip() == ".claude-plugin/marketplace.json"


def test_gitignore_whitelists_marketplace():
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "!/.claude-plugin/" in lines


def test_frontmatter_hints_are_quoted():
    review = (PLUGIN / "skills" / "review" / "SKILL.md").read_text("utf-8")
    assert 'argument-hint: "[base-ref] [spec.md] [plan.md]"' in review
    new = (PLUGIN / "commands" / "new-project.md").read_text("utf-8")
    assert 'argument-hint: "[name] [node|python]"' in new
