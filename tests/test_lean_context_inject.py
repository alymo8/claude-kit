import json

import pytest
from helpers import PLUGIN, clean_env, run_script

HOOK = PLUGIN / "hooks" / "lean_context_inject.py"


def run(**env: str):
    return run_script(HOOK, stdin="{}", env=clean_env(**env))


@pytest.mark.parametrize("env", [{}, {"CLAUDE_KIT_LEAN_CONTEXT": "1"}])
def test_on_injects_the_rule(env):
    result = run(**env)
    assert result.returncode == 0
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    assert "claude-kit:lean-context" in out["additionalContext"]


def test_zero_turns_it_off():
    result = run(CLAUDE_KIT_LEAN_CONTEXT="0")
    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("value", ["", "yes", "true", " 0x"])
def test_other_values_count_as_on(value):
    result = run(CLAUDE_KIT_LEAN_CONTEXT=value)
    assert "claude-kit:lean-context" in result.stdout


def test_registered_on_session_start():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    commands = [
        h["command"] for group in hooks["hooks"]["SessionStart"] for h in group["hooks"]
    ]
    assert any("hooks/lean_context_inject.py" in c for c in commands)
