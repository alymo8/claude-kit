import json
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "user-config-inventory.py"
inv = load_module(SCRIPT, "user_config_inventory")

TOP_KEYS = (
    "settings",
    "mcp_servers",
    "plugins",
    "skills",
    "scheduled_tasks",
    "instructions",
    "errors",
)

SETTINGS = {
    "env": {"API_TOKEN": "SECRET-ENV-VALUE-1"},
    "permissions": {
        "allow": ["Bash(git log:*)", "Read(./**)", "Read(./**)"],
        "ask": ["Bash(git push:*)"],
        "deny": ["Read(./.env)"],
        "defaultMode": "acceptEdits",
    },
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "python ~/hooks/guard.py"}],
            }
        ]
    },
    "enabledPlugins": {"demo@market": True, "off@market": False},
    "statusLine": {"type": "command", "command": "python ~/.claude/statusline.py"},
    "autoMode": {"environment": ["a"], "rules": ["b"]},
}

LOCAL_SETTINGS = {
    "env": {"LOCAL_KEY": "SECRET-LOCAL-ENV-4"},
    "enabledPlugins": {"off@market": True},
}


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def line_of(path: Path, needle: str) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    return next(i for i, line in enumerate(lines, 1) if needle in line)


def run(home: Path) -> dict:
    result = run_script(SCRIPT, "--home", str(home))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    write_json(home / ".claude" / "settings.json", SETTINGS)
    write_json(home / ".claude" / "settings.local.json", LOCAL_SETTINGS)
    return home


def settings_item(out: dict, file: str) -> dict:
    return next(item for item in out["settings"] if item["file"] == file)


def test_value_lines_nested_and_duplicates():
    text = '{\n "a": {\n  "b": [\n   "x",\n   "x"\n  ]\n },\n "a2": 1\n}'
    lines = inv.value_lines(text)
    assert lines[("a",)] == 2
    assert lines[("a", "b")] == 3
    assert lines[("a", "b", 0)] == 4
    assert lines[("a", "b", 1)] == 5
    assert lines[("a2",)] == 8
    assert inv.value_lines('{"k": 1,\n "k": 2}')[("k",)] == 2


def test_permissions_listed_with_file_and_line(home):
    settings = home / ".claude" / "settings.json"
    item = settings_item(run(home), ".claude/settings.json")
    perms = item["permissions"]
    assert len(perms) == 5
    assert all(p["file"] == ".claude/settings.json" for p in perms)
    git_log = next(p for p in perms if p["rule"] == "Bash(git log:*)")
    assert git_log["kind"] == "allow"
    assert git_log["line"] == line_of(settings, '"Bash(git log:*)"')
    reads = [p["line"] for p in perms if p["rule"] == "Read(./**)"]
    assert len(reads) == 2 and reads[0] != reads[1]
    assert item["defaultMode"] == {
        "value": "acceptEdits",
        "file": ".claude/settings.json",
        "line": line_of(settings, '"defaultMode"'),
    }


def test_settings_hooks_status_line_and_auto_mode(home):
    settings = home / ".claude" / "settings.json"
    item = settings_item(run(home), ".claude/settings.json")
    assert item["hooks"] == [
        {
            "event": "PreToolUse",
            "matcher": "Bash",
            "command": "python ~/hooks/guard.py",
            "file": ".claude/settings.json",
            "line": line_of(settings, "guard.py"),
        }
    ]
    assert item["statusLine"]["command"] == "python ~/.claude/statusline.py"
    assert item["statusLine"]["line"] == line_of(settings, "statusline.py")
    assert item["autoMode"]["keys"] == ["environment", "rules"]
    assert item["autoMode"]["line"] == line_of(settings, '"autoMode"')


def test_env_keys_and_enabled_plugins(home):
    settings = home / ".claude" / "settings.json"
    out = run(home)
    item = settings_item(out, ".claude/settings.json")
    assert item["env"] == [
        {
            "key": "API_TOKEN",
            "file": ".claude/settings.json",
            "line": line_of(settings, '"API_TOKEN"'),
        }
    ]
    local = settings_item(out, ".claude/settings.local.json")
    assert [e["key"] for e in local["env"]] == ["LOCAL_KEY"]
    assert local["env"][0]["file"] == ".claude/settings.local.json"
    enabled = {p["name"]: p["enabled"] for p in item["enabledPlugins"]}
    assert enabled == {"demo@market": True, "off@market": False}


def test_secret_values_absent_from_output(home):
    result = run_script(SCRIPT, "--home", str(home))
    assert result.returncode == 0
    assert "SECRET-" not in result.stdout


def test_malformed_settings_reports_error_and_continues(home):
    (home / ".claude" / "settings.json").write_text(
        '{"permissions": ', encoding="utf-8"
    )
    result = run_script(SCRIPT, "--home", str(home))
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert len(out["errors"]) == 1
    assert out["errors"][0]["file"] == ".claude/settings.json"
    assert out["errors"][0]["error"]
    assert settings_item(out, ".claude/settings.local.json")


def test_missing_home_exits_2(tmp_path):
    result = run_script(SCRIPT, "--home", str(tmp_path / "nope"))
    assert result.returncode == 2
    assert "not a directory" in result.stderr


def test_empty_home_yields_empty_lists(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    out = run(empty)
    for key in TOP_KEYS:
        assert out[key] == [], key


def test_rel_inside_and_outside_home(tmp_path):
    home = tmp_path / "home"
    assert inv.rel(home / ".claude" / "x.json", home) == ".claude/x.json"
    outside = tmp_path / "elsewhere" / "y.py"
    assert inv.rel(outside, home) == outside.as_posix()
