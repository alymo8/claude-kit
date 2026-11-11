import json

import pytest
from helpers import PLUGIN, clean_env, run_script

HOOK = PLUGIN / "hooks" / "precompact_keep.py"


def run(**env: str):
    return run_script(HOOK, stdin="{}", env=clean_env(**env))


def test_on_prints_one_short_instruction():
    result = run()
    assert result.returncode == 0
    assert "approaches already tried" in result.stdout
    assert len(result.stdout) < 10_000


def test_zero_turns_it_off():
    result = run(CLAUDE_KIT_PRECOMPACT="0")
    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("value", ["", "yes", "1"])
def test_other_values_count_as_on(value):
    assert "approaches already tried" in run(CLAUDE_KIT_PRECOMPACT=value).stdout


def test_registered_on_pre_compact():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    commands = [h["command"] for g in hooks["hooks"]["PreCompact"] for h in g["hooks"]]
    assert any("hooks/precompact_keep.py" in c for c in commands)
