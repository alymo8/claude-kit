import json
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "install-statusline.py"


def test_adds_statusline_and_preserves_everything_else(tmp_path: Path):
    settings = tmp_path / "settings.json"
    original = {
        "model": "x",
        "permissions": {"allow": ["WebSearch"]},
        "nested": {"deep": [1, {"a": "b"}]},
        "unicode": "عربي",
    }
    settings.write_text(json.dumps(original), encoding="utf-8")
    mod = load_module(SCRIPT, "install_statusline")
    assert mod.install(settings, tmp_path / "skills") == "added"
    data = json.loads(settings.read_text(encoding="utf-8"))
    for key, value in original.items():
        assert data[key] == value
    assert data["statusLine"]["type"] == "command"
    command = data["statusLine"]["command"]
    assert command.startswith('python "')
    assert command.endswith('/claude-kit/scripts/statusline.py"')
    assert "\\" not in command
    assert "عربي" in settings.read_text(encoding="utf-8")  # ensure_ascii=False


def test_existing_statusline_is_left_untouched(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text('{"statusLine": {"type": "command", "command": "mine"}}')
    before = settings.read_bytes()
    mod = load_module(SCRIPT, "install_statusline")
    assert mod.install(settings, tmp_path / "skills") == "unchanged"
    assert settings.read_bytes() == before


def test_creates_missing_settings_file(tmp_path: Path):
    settings = tmp_path / "sub" / "settings.json"
    result = run_script(
        SCRIPT, "--settings", str(settings), "--skills-dir", str(tmp_path / "skills")
    )
    assert result.returncode == 0, result.stderr
    assert "statusLine added" in result.stdout
    assert "statusLine" in json.loads(settings.read_text(encoding="utf-8"))


def test_unparseable_settings_is_refused_without_writing(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text("{oops", encoding="utf-8")
    result = run_script(SCRIPT, "--settings", str(settings))
    assert result.returncode == 1
    assert settings.read_text(encoding="utf-8") == "{oops"
