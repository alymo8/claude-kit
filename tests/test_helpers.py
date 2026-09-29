from helpers import clean_env


def test_clean_env_drops_kit_and_typesafe_settings(monkeypatch):
    monkeypatch.setenv("CLAUDE_KIT_NUDGE_AT", "1")
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setenv("KEEP_ME", "1")
    env = clean_env(EXTRA="x")
    assert "CLAUDE_KIT_NUDGE_AT" not in env
    assert "TYPESAFE_API_KEY" not in env
    assert env["KEEP_ME"] == "1"
    assert env["EXTRA"] == "x"
