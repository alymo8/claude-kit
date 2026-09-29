import io
import json
import os
import sys
import types

import pytest
from helpers import PLUGIN, clean_env, load_module, run_script

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


PROMPT = "add a dark mode toggle to settings"
HIGH = {"underspecified": 0.1, "new_feature": 0.9, "key_decision": 0.2}
RECORD_KEYS = [
    "ts",
    "session_id",
    "project",
    "mode",
    "prompt",
    "scores",
    "thresholds",
    "fired",
    "injected",
    "latency_ms",
    "usage",
    "error",
]


def fake(scores):
    usage = {"input_tokens": 10, "output_tokens": 3, "model": "jev-test"}
    return lambda prompt: triage.Judgment(scores, usage)


def failing(code):
    def judge(prompt):
        raise triage.JevError(code)

    return judge


def must_not_call(prompt):
    raise AssertionError("judge must not be called")


def feed_stdin(monkeypatch, event):
    raw = io.BytesIO(json.dumps(event).encode("utf-8"))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(raw, encoding="utf-8"))


def run_main(monkeypatch, capsys, tmp_path, prompt=PROMPT, mode="active", judge=None):
    monkeypatch.setattr(triage, "jev_dir", lambda: tmp_path / "jev")
    if mode:
        monkeypatch.setenv("CLAUDE_KIT_JEV", mode)
    if judge:
        monkeypatch.setattr(triage, "judge", judge)
    feed_stdin(
        monkeypatch,
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s1",
            "cwd": str(tmp_path / "proj"),
            "prompt": prompt,
        },
    )
    assert triage.main() == 0
    return capsys.readouterr()


def read_log(tmp_path):
    path = tmp_path / "jev" / "log.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_off_does_nothing(monkeypatch, capsys, tmp_path):
    monkeypatch.delitem(sys.modules, "typesafe_sdk", raising=False)
    out = run_main(monkeypatch, capsys, tmp_path, mode=None, judge=must_not_call)
    assert out.out == ""
    assert read_log(tmp_path) == []
    assert "typesafe_sdk" not in sys.modules


def test_shadow_logs_without_context(monkeypatch, capsys, tmp_path):
    out = run_main(monkeypatch, capsys, tmp_path, mode="shadow", judge=fake(HIGH))
    assert out.out == ""
    [record] = read_log(tmp_path)
    assert list(record) == RECORD_KEYS
    assert record["mode"] == "shadow"
    assert record["session_id"] == "s1"
    assert record["project"] == "proj"
    assert record["prompt"] == PROMPT
    assert record["scores"] == HIGH
    assert record["fired"] == ["new_feature"]
    assert record["injected"] is False
    assert isinstance(record["latency_ms"], int)
    assert record["usage"]["model"] == "jev-test"
    assert record["error"] is None


def test_active_injects_only_fired_hints(monkeypatch, capsys, tmp_path):
    out = run_main(monkeypatch, capsys, tmp_path, judge=fake(HIGH))
    payload = json.loads(out.out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "UserPromptSubmit"
    assert "pre-flight branch check" in payload["additionalContext"]
    assert "underspecified" not in payload["additionalContext"]
    assert read_log(tmp_path)[0]["injected"] is True


def test_active_below_threshold_is_silent(monkeypatch, capsys, tmp_path):
    low = dict.fromkeys(triage.KEYS, 0.3)
    out = run_main(monkeypatch, capsys, tmp_path, judge=fake(low))
    assert out.out == ""
    [record] = read_log(tmp_path)
    assert record["fired"] == []
    assert record["injected"] is False


def test_threshold_override_applies(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("CLAUDE_KIT_JEV_T_NEW_FEATURE", "0.95")
    out = run_main(monkeypatch, capsys, tmp_path, judge=fake(HIGH))
    assert out.out == ""
    assert read_log(tmp_path)[0]["thresholds"]["new_feature"] == 0.95


@pytest.mark.parametrize("prompt", ["", "lgtm", "/ship docs/x.md now"])
def test_skipped_prompts_are_not_judged(monkeypatch, capsys, tmp_path, prompt):
    out = run_main(monkeypatch, capsys, tmp_path, prompt=prompt, judge=must_not_call)
    assert out.out == ""
    assert read_log(tmp_path) == []


@pytest.mark.parametrize("code", ["timeout", "api_error: RuntimeError: boom"])
def test_errors_fail_open(monkeypatch, capsys, tmp_path, code):
    out = run_main(monkeypatch, capsys, tmp_path, judge=failing(code))
    assert out.out == ""
    assert "[claude-kit] jev triage" in out.err
    [record] = read_log(tmp_path)
    assert record["error"] == code
    assert record["scores"] is None


def test_missing_key(monkeypatch, capsys, tmp_path):
    run_main(monkeypatch, capsys, tmp_path)
    assert read_log(tmp_path)[0]["error"] == "missing_key"


def test_missing_sdk(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "typesafe_sdk", None)
    run_main(monkeypatch, capsys, tmp_path)
    assert read_log(tmp_path)[0]["error"] == "missing_sdk"


def test_unwritable_log_still_injects(monkeypatch, capsys, tmp_path):
    blocker = tmp_path / "jev"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(triage, "jev_dir", lambda: blocker / "sub")
    monkeypatch.setenv("CLAUDE_KIT_JEV", "active")
    monkeypatch.setattr(triage, "judge", fake(HIGH))
    feed_stdin(monkeypatch, {"session_id": "s1", "cwd": "x", "prompt": PROMPT})
    assert triage.main() == 0
    out = capsys.readouterr()
    assert "pre-flight branch check" in out.out
    assert "cannot write log" in out.err


def fake_sdk(calls, result=None, exc=None):
    class Client:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def system_one(self, **kwargs):
            calls.append(("call", kwargs))
            if exc:
                raise exc
            return result

    return types.SimpleNamespace(
        Noul=lambda **kw: kw, RetryPolicy=lambda **kw: kw, TypeSafeClient=Client
    )


def test_judge_calls_sdk_with_pilot_settings(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    result = types.SimpleNamespace(
        nouls={k: types.SimpleNamespace(noul=0.5) for k in triage.KEYS},
        usage=types.SimpleNamespace(input_tokens=5, output_tokens=1),
        model="jev-x",
    )
    calls = []
    monkeypatch.setitem(sys.modules, "typesafe_sdk", fake_sdk(calls, result))
    judgment = triage.judge(PROMPT)
    assert judgment.scores == dict.fromkeys(triage.KEYS, 0.5)
    assert judgment.usage == {"input_tokens": 5, "output_tokens": 1, "model": "jev-x"}
    (_, init), (_, call) = calls
    assert init == {"timeout": 1.5, "retry": {"max_retries": 0}}
    assert call["state"] == PROMPT
    assert list(call["questions"]) == list(triage.KEYS)
    assert set(call["questions"]["new_feature"]["criteria"]) == {"true", "false"}


@pytest.mark.parametrize(
    "exc,code",
    [
        (TimeoutError("slow"), "timeout"),
        (RuntimeError("boom"), "api_error: RuntimeError: boom"),
    ],
)
def test_judge_maps_sdk_errors(monkeypatch, exc, code):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "typesafe_sdk", fake_sdk([], exc=exc))
    with pytest.raises(triage.JevError) as info:
        triage.judge(PROMPT)
    assert info.value.code == code


def test_unicode_prompt_survives_stdin(tmp_path):
    prompt = "ajoute un résumé 🚀 à la page d'accueil"
    event = json.dumps({"session_id": "s1", "cwd": "x", "prompt": prompt})
    env = clean_env(
        CLAUDE_KIT_JEV="shadow", HOME=str(tmp_path), USERPROFILE=str(tmp_path)
    )
    result = run_script(HOOK, stdin=event, env=env)
    assert result.returncode == 0
    assert result.stdout == ""
    log = tmp_path / ".claude" / "claude-kit" / "jev" / "log.jsonl"
    [record] = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert record["prompt"] == prompt
    assert record["error"] == "missing_key"


def test_flag_off_subprocess_creates_nothing(tmp_path):
    event = json.dumps({"session_id": "s1", "cwd": "x", "prompt": PROMPT})
    env = clean_env(HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    result = run_script(HOOK, stdin=event, env=env)
    assert result.returncode == 0
    assert result.stdout == ""
    assert not (tmp_path / ".claude").exists()
