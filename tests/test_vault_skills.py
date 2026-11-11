"""Structure tests for the vault skills and the /vault-init command."""

from __future__ import annotations

from helpers import PLUGIN

INGEST = PLUGIN / "skills" / "ingest" / "SKILL.md"
TASK_PROMPT = PLUGIN / "skills" / "task-prompt" / "SKILL.md"
COMMAND = PLUGIN / "commands" / "vault-init.md"


def frontmatter(text: str) -> dict[str, str]:
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def flat(path) -> str:
    return " ".join(path.read_text("utf-8").split())


def test_skill_frontmatter():
    for path, name in ((INGEST, "ingest"), (TASK_PROMPT, "task-prompt")):
        front = frontmatter(path.read_text("utf-8"))
        assert front["name"] == name
        assert front["description"]


def test_ingest_rules():
    text = flat(INGEST)
    for needle in (
        "vault-pending.py",
        "--json",
        "--extract",
        "CLAUDE_KIT_VAULT",
        "Never edit `raw/`.",
        "Never invent people, owners, dates or facts",
        "Do not commit",
        "wiki/_templates/",
        "status: inbox",
        "missing",
        "sha256",
        "aliases",
        "unsupported",
        "wiki/index.md",
    ):
        assert needle in text, needle


def test_task_prompt_shape_and_read_only():
    text = flat(TASK_PROMPT)
    assert "It changes no file." in text
    for needle in (
        "# Task:",
        "## Acceptance criteria",
        "none written",
        "## Context",
        "## Verification",
        "done",
    ):
        assert needle in text, needle


def test_vault_init_command_is_user_only():
    text = COMMAND.read_text("utf-8")
    front = frontmatter(text)
    assert front["disable-model-invocation"] == "true"
    assert front["description"]
    assert "<path>" in front["argument-hint"]
    assert "scripts/vault-init.py" in text
    assert "--profile" in text
