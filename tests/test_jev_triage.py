import os

import pytest
from helpers import PLUGIN, load_module

HOOK = PLUGIN / "hooks" / "jev_triage.py"
triage = load_module(HOOK, "jev_triage")


@pytest.fixture(autouse=True)
def no_kit_env(monkeypatch):
    for name in list(os.environ):
        if name.startswith(("CLAUDE_KIT_", "TYPESAFE_")):
            monkeypatch.delenv(name)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "off"),
        ("", "off"),
        ("banana", "off"),
        ("OFF", "off"),
        ("shadow", "shadow"),
        (" Active ", "active"),
    ],
)
def test_mode(monkeypatch, value, expected):
    if value is not None:
        monkeypatch.setenv("CLAUDE_KIT_JEV", value)
    assert triage.mode() == expected


def test_thresholds_default_and_overrides(monkeypatch):
    assert triage.thresholds() == {
        "underspecified": 0.65,
        "new_feature": 0.65,
        "key_decision": 0.65,
    }
    monkeypatch.setenv("CLAUDE_KIT_JEV_T_NEW_FEATURE", "0.8")
    monkeypatch.setenv("CLAUDE_KIT_JEV_T_UNDERSPECIFIED", "high")
    monkeypatch.setenv("CLAUDE_KIT_JEV_T_KEY_DECISION", "1.5")
    assert triage.thresholds() == {
        "underspecified": 0.65,
        "new_feature": 0.8,
        "key_decision": 0.65,
    }


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", False),
        ("   ", False),
        ("/ship docs/x.md now", False),
        ("<command-name>/clear</command-name>", False),
        ("lgtm", False),
        ("1 yes", False),
        ("add a dark mode toggle", True),
    ],
)
def test_should_judge(text, expected):
    assert triage.should_judge(text) is expected


def test_clean_strips_reminders_and_pasted_blocks():
    raw = (
        "fix the login bug <system-reminder>ctx</system-reminder>\n"
        '<pasted_content id="ab">huge log</pasted_content id="ab">'
    )
    assert triage.clean(raw) == "fix the login bug"


def test_fired_and_hints():
    limits = dict.fromkeys(triage.KEYS, 0.65)
    keys = triage.fired(
        {"underspecified": 0.2, "new_feature": 0.65, "key_decision": 0.9}, limits
    )
    assert keys == ["new_feature", "key_decision"]
    text = triage.hints(keys)
    assert "pre-flight branch check" in text
    assert "key decision" in text
    assert "underspecified" not in text
    assert triage.hints([]) == ""
