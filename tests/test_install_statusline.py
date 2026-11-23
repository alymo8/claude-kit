import json
import re
import shutil
import subprocess
import sys
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
    assert command.endswith('/agent-kit/scripts/statusline.py"')
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


def command_of(settings: Path) -> str:
    return json.loads(settings.read_text(encoding="utf-8"))["statusLine"]["command"]


def test_stable_copy_added_when_none_set(tmp_path: Path):
    settings = tmp_path / "settings.json"
    cfg = tmp_path / "cfg"
    mod = load_module(SCRIPT, "install_statusline")
    assert mod.install(settings, tmp_path / "skills", stable=cfg) == "added"
    assert command_of(settings) == mod.stable_command(cfg)
    copy = cfg / "claude-kit" / "statusline.py"
    assert copy.read_bytes() == (PLUGIN / "scripts" / "statusline.py").read_bytes()


def test_stable_copy_leaves_unrelated_line(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text('{"statusLine": {"type": "command", "command": "mine"}}')
    before = settings.read_bytes()
    cfg = tmp_path / "cfg"
    mod = load_module(SCRIPT, "install_statusline")
    assert mod.install(settings, tmp_path / "skills", stable=cfg) == "unchanged"
    assert settings.read_bytes() == before
    assert not (cfg / "claude-kit" / "statusline.py").exists()


def test_rerun_refreshes_stable_copy(tmp_path: Path):
    settings = tmp_path / "settings.json"
    cfg = tmp_path / "cfg"
    mod = load_module(SCRIPT, "install_statusline")
    assert mod.install(settings, tmp_path / "skills", stable=cfg) == "added"
    copy = cfg / "claude-kit" / "statusline.py"
    copy.write_bytes(b"")
    assert mod.install(settings, tmp_path / "skills", stable=cfg) == "refreshed"
    assert copy.read_bytes() == (PLUGIN / "scripts" / "statusline.py").read_bytes()


def test_legacy_statusline_with_backslashes_migrates(tmp_path: Path):
    skills = tmp_path / "skills"
    old = str(skills / "claude-kit" / "scripts" / "statusline.py")
    old = old.replace("/", "\\").replace("skills", "SKILLS")
    settings = tmp_path / "settings.json"
    line = {"type": "command", "command": f'python "{old}"'}
    settings.write_text(json.dumps({"statusLine": line}), encoding="utf-8")
    mod = load_module(SCRIPT, "install_statusline")
    assert mod.install(settings, skills) == "migrated"
    assert command_of(settings) == mod.link_command(skills)


def test_stable_line_survives_cache_version_change(tmp_path: Path):
    version = tmp_path / "plugin cache" / "agent-kit" / "1.0.0"
    scripts = version / "scripts"
    scripts.mkdir(parents=True)
    for name in ("install-statusline.py", "statusline.py"):
        shutil.copy2(PLUGIN / "scripts" / name, scripts / name)
    cfg = tmp_path / "cfg"
    settings = cfg / "settings.json"
    result = run_script(
        scripts / "install-statusline.py",
        "--stable-copy",
        "--config-dir",
        str(cfg),
        "--settings",
        str(settings),
    )
    assert result.returncode == 0, result.stderr
    version.rename(version.with_name("1.0.1"))
    match = re.fullmatch(r'python "(.+)"', command_of(settings))
    assert match
    stdin = json.dumps(
        {
            "context_window": {
                "total_input_tokens": 1000,
                "context_window_size": 200000,
                "used_percentage": 1,
            },
            "cost": {"total_cost_usd": 0.5},
        }
    )
    done = subprocess.run(
        [sys.executable, match.group(1)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    assert "ctx 1k/200k" in done.stdout
    assert "$0.50" in done.stdout
