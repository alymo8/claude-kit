import json

import pytest
from helpers import PLUGIN, clean_env, run_script

HOOK = PLUGIN / "hooks" / "grill_inject.py"


def run(**env: str):
    return run_script(HOOK, stdin="{}", env=clean_env(**env))


def test_one_injects_the_rule():
    result = run(CLAUDE_KIT_GRILL="1")
    assert result.returncode == 0
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    assert "claude-kit:grill" in out["additionalContext"]
    assert "## Coverage" in out["additionalContext"]


def test_unset_is_off():
    result = run()
    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("value", ["0", "", "true", "yes"])
def test_other_values_are_off(value):
    result = run(CLAUDE_KIT_GRILL=value)
    assert result.returncode == 0
    assert result.stdout == ""
