"""Tests for plugin/hooks/vault_inject.py."""

from __future__ import annotations

import json
import sys

import pytest
from helpers import PLUGIN, clean_env, run_script

HOOK = PLUGIN / "hooks" / "vault_inject.py"


def run(**env: str):
    return run_script(HOOK, stdin="{}", env=clean_env(**env))


@pytest.mark.parametrize("env", [{}, {"CLAUDE_KIT_VAULT": ""}])
def test_unset_or_empty_prints_nothing(env):
    result = run(**env)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_path_without_vault_toml_warns_on_stderr(tmp_path):
    result = run(CLAUDE_KIT_VAULT=str(tmp_path))
    assert (result.returncode, result.stdout) == (0, "")
    assert result.stderr == (
        f"[claude-kit] CLAUDE_KIT_VAULT has no vault.toml: {tmp_path}\n"
    )


@pytest.mark.parametrize(
    "suffix",
    [
        "",
        pytest.param(
            "\\",
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="backslash separator"
            ),
        ),
    ],
)
def test_valid_vault_injects_pointer(tmp_path, suffix):
    (tmp_path / "vault.toml").write_text('profile = "work"\n', encoding="utf-8")
    result = run(CLAUDE_KIT_VAULT=str(tmp_path) + suffix)
    assert result.returncode == 0
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    text = out["additionalContext"]
    p = tmp_path.as_posix()
    assert text.startswith(f"Vault (work): {p}. ")
    assert f"{p}/wiki/index.md" in text
    assert "claude-kit:ingest" in text
    assert "claude-kit:task-prompt" in text


def test_tilde_is_expanded(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "vault.toml").write_text('profile = "work"\n', encoding="utf-8")
    result = run(
        CLAUDE_KIT_VAULT="~/vault", HOME=str(tmp_path), USERPROFILE=str(tmp_path)
    )
    assert result.returncode == 0
    text = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert text.startswith(f"Vault (work): {vault.as_posix()}. ")


def test_relative_path_is_refused():
    result = run(CLAUDE_KIT_VAULT="relative/vault")
    assert (result.returncode, result.stdout) == (0, "")
    assert result.stderr == (
        "[claude-kit] CLAUDE_KIT_VAULT is not an absolute path: relative/vault\n"
    )


def test_broken_vault_toml_reports_error_and_exits_0(tmp_path):
    (tmp_path / "vault.toml").write_text("profile = \n", encoding="utf-8")
    result = run(CLAUDE_KIT_VAULT=str(tmp_path))
    assert (result.returncode, result.stdout) == (0, "")
    assert result.stderr.startswith("[claude-kit] vault inject error:")


def test_registered_after_workspace_rules_without_matcher():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text("utf-8"))
    groups = hooks["hooks"]["SessionStart"]
    names = [g["hooks"][0]["command"] for g in groups]
    rules = next(i for i, c in enumerate(names) if "workspace_rules_inject.py" in c)
    assert "hooks/vault_inject.py" in names[rules + 1]
    assert "matcher" not in groups[rules + 1]
