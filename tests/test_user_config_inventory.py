import json
import os
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


CLAUDE_JSON = {
    "mcpServers": {
        "web": {
            "command": "npx",
            "args": ["-y", "some-mcp"],
            "env": {"WEB_KEY": "SECRET-MCP-ENV-2"},
        }
    },
    "projects": {
        "/work/app": {
            "mcpServers": {
                "api": {
                    "type": "http",
                    "url": "https://mcp.example.com",
                    "headers": {"Authorization": "SECRET-HEADER-3"},
                    "env": {"P": "SECRET-PROJECT-ENV-5"},
                }
            }
        }
    },
}

DEMO_HOOK = "SessionStart", "node ${CLAUDE_PLUGIN_ROOT}/hooks/start.js"


def hooks_file(event: str, command: str) -> dict:
    return {"hooks": {event: [{"hooks": [{"type": "command", "command": command}]}]}}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    write_json(home / ".claude.json", CLAUDE_JSON)
    cache = home / ".claude" / "plugins" / "cache" / "market" / "demo"
    write_json(
        home / ".claude" / "plugins" / "installed_plugins.json",
        {
            "version": 2,
            "plugins": {
                "demo@market": [
                    {
                        "scope": "user",
                        "installPath": str(cache / "1.0.0"),
                        "version": "1.0.0",
                        "gitCommitSha": "abc1234",
                    },
                    {
                        "scope": "project",
                        "projectPath": "/work/app",
                        "installPath": str(cache / "0.9.0"),
                        "version": "0.9.0",
                    },
                ]
            },
        },
    )
    write_json(cache / "1.0.0" / "hooks" / "hooks.json", hooks_file(*DEMO_HOOK))
    write_json(
        cache / "1.0.0" / ".claude-plugin" / "plugin.json",
        {"name": "demo", "hooks": "./extra.json"},
    )
    skills = home / ".claude" / "skills"
    write_json(
        skills / "kitplug" / ".claude-plugin" / "plugin.json", {"name": "kitplug"}
    )
    write_json(
        skills / "kitplug" / "hooks" / "hooks.json",
        hooks_file("UserPromptSubmit", "python ${CLAUDE_PLUGIN_ROOT}/hooks/nudge.py"),
    )
    write_text(skills / "plain" / "SKILL.md", "plain skill")
    tasks = home / ".claude" / "scheduled-tasks" / "daily"
    write_text(tasks / "SKILL.md", "task")
    write_text(tasks / "notes.txt", "notes")
    write_text(home / ".claude" / "CLAUDE.md", "rules")
    write_text(home / ".claude" / "agents" / "rev.md", "agent")
    write_text(home / ".claude" / "commands" / "go.md", "command")
    write_text(home / ".claude" / "output-styles" / "terse.md", "style")
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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("TOKEN=abc node x.js", "TOKEN=*** node x.js"),
        ("A=\"b c\" B='d' run", "A=*** B=*** run"),
        ("--api-key=abc", "--api-key=***"),
        ("-e", "-e"),
        ("GITHUB_TOKEN=ghp_1", "GITHUB_TOKEN=***"),
        ("https://u:pw@h.io/p?k=v&t=x", "https://u:***@h.io/p?k=***&t=***"),
        ("https://tok@h.io", "https://***@h.io"),
        ("https://mcp.example.com", "https://mcp.example.com"),
        ("node ${CLAUDE_PLUGIN_ROOT}/a.js --x", "node ${CLAUDE_PLUGIN_ROOT}/a.js --x"),
        ("a == b", "a == b"),
        ("FOO= cmd", "FOO= cmd"),
    ],
)
def test_redact(text, expected):
    assert inv.redact(text) == expected


def test_secrets_in_args_url_and_commands_are_masked(tmp_path):
    home = tmp_path / "home"
    write_json(
        home / ".claude" / "settings.json",
        {
            "hooks": hooks_file("Stop", "API_KEY=SECRET-HOOK-1 python ~/h.py")["hooks"],
            "statusLine": {"command": "TOKEN='SECRET-STATUS-2' node ~/s.js"},
        },
    )
    write_json(
        home / ".claude.json",
        {
            "mcpServers": {
                "gh": {"command": "docker", "args": ["-e", "GH=SECRET-ARG-3"]},
                "web": {"url": "https://me:SECRET-PW-4@x.io/m?key=SECRET-Q-5"},
            }
        },
    )
    plugin = home / ".claude" / "skills" / "kp"
    write_json(plugin / ".claude-plugin" / "plugin.json", {"name": "kp"})
    write_json(
        plugin / "hooks" / "hooks.json",
        hooks_file("Stop", "X=SECRET-PLUGIN-6 sh run.sh"),
    )
    install = home / ".claude" / "plugins" / "cache" / "m" / "ip" / "1"
    write_json(
        home / ".claude" / "plugins" / "installed_plugins.json",
        {"plugins": {"ip@m": [{"scope": "user", "installPath": str(install)}]}},
    )
    write_json(
        install / "hooks" / "hooks.json",
        hooks_file("Stop", "Y=SECRET-INSTALLED-7 node x.js"),
    )
    result = run_script(SCRIPT, "--home", str(home))
    assert result.returncode == 0, result.stderr
    assert "SECRET-" not in result.stdout
    out = json.loads(result.stdout)
    assert by_name(out["skills"], "kp")["hooks"][0]["command"] == "X=*** sh run.sh"
    assert by_name(out["plugins"], "ip@m")["hooks"][0]["command"] == "Y=*** node x.js"
    item = settings_item(out, ".claude/settings.json")
    assert item["hooks"][0]["command"] == "API_KEY=*** python ~/h.py"
    assert item["statusLine"]["command"] == "TOKEN=*** node ~/s.js"
    servers = out["mcp_servers"]
    assert by_name(servers, "gh")["args"] == ["-e", "GH=***"]
    assert by_name(servers, "web")["url"] == "https://me:***@x.io/m?key=***"


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


def by_name(items: list[dict], name: str) -> dict:
    return next(item for item in items if item["name"] == name)


def test_mcp_servers_user_and_local(home):
    claude_json = home / ".claude.json"
    servers = run(home)["mcp_servers"]
    assert len(servers) == 2
    web = by_name(servers, "web")
    assert (web["scope"], web["project"], web["type"]) == ("user", None, "stdio")
    assert web["command"] == "npx"
    assert web["args"] == ["-y", "some-mcp"]
    assert web["url"] is None
    assert web["env_keys"] == ["WEB_KEY"]
    assert web["header_keys"] == []
    assert web["file"] == ".claude.json"
    assert web["line"] == line_of(claude_json, '"web"')
    api = by_name(servers, "api")
    assert (api["scope"], api["project"]) == ("local", "/work/app")
    assert api["type"] == "http"
    assert api["url"] == "https://mcp.example.com"
    assert api["command"] is None and api["args"] == []
    assert api["header_keys"] == ["Authorization"]
    assert api["env_keys"] == ["P"]
    assert api["line"] == line_of(claude_json, '"api"')


def test_installed_plugin_entries_hooks_and_enabled(home):
    plugins = run(home)["plugins"]
    assert [p["name"] for p in plugins] == ["demo@market", "demo@market"]
    user, project = plugins
    hooks_json = home / ".claude/plugins/cache/market/demo/1.0.0/hooks/hooks.json"
    assert user["git_commit_sha"] == "abc1234"
    assert user["install_path"] == ".claude/plugins/cache/market/demo/1.0.0"
    assert user["root"] == user["install_path"]
    assert user["enabled"] is True
    assert user["manifest_hooks"] is True
    assert user["file"] == ".claude/plugins/installed_plugins.json"
    assert user["hooks"] == [
        {
            "event": "SessionStart",
            "matcher": None,
            "command": "node ${CLAUDE_PLUGIN_ROOT}/hooks/start.js",
            "file": ".claude/plugins/cache/market/demo/1.0.0/hooks/hooks.json",
            "line": line_of(hooks_json, "start.js"),
        }
    ]
    assert project["scope"] == "project"
    assert project["project_path"] == "/work/app"
    assert project["git_commit_sha"] is None
    assert project["manifest_hooks"] is False
    assert project["hooks"] == []
    assert user["line"] != project["line"]


def test_enabled_local_overrides_settings(home):
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for name in ("off@market", "other@market"):
        data["plugins"][name] = [
            {"scope": "user", "installPath": str(home / "x" / name), "version": "1"}
        ]
    write_json(path, data)
    plugins = run(home)["plugins"]
    assert by_name(plugins, "off@market")["enabled"] is True
    assert by_name(plugins, "other@market")["enabled"] is None


def test_skills_dir_plugin_marked_with_hooks(home):
    nudge = home / ".claude/skills/kitplug/hooks/hooks.json"
    skills = run(home)["skills"]
    assert [s["name"] for s in skills] == ["kitplug", "plain"]
    kitplug = by_name(skills, "kitplug")
    assert kitplug["plugin"] is True
    assert kitplug["root"] == ".claude/skills/kitplug"
    assert kitplug["link"] is None and kitplug["target"] is None
    assert kitplug["hooks"] == [
        {
            "event": "UserPromptSubmit",
            "matcher": None,
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/nudge.py",
            "file": ".claude/skills/kitplug/hooks/hooks.json",
            "line": line_of(nudge, "nudge.py"),
        }
    ]
    plain = by_name(skills, "plain")
    assert plain["plugin"] is False
    assert plain["hooks"] == []


def test_linked_skill_reports_link_and_target(home, tmp_path):
    target = tmp_path / "checkout"
    write_json(target / ".claude-plugin" / "plugin.json", {"name": "linked"})
    write_json(target / "hooks" / "hooks.json", hooks_file("Stop", "python stop.py"))
    link = home / ".claude" / "skills" / "linked"
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
    item = by_name(run(home)["skills"], "linked")
    assert item["link"] in {"symlink", "junction"}
    assert item["target"] == target.as_posix()
    assert item["plugin"] is True
    assert item["hooks"][0]["file"] == ".claude/skills/linked/hooks/hooks.json"


def test_relative_symlink_target_resolves_from_link_folder(home):
    target = home / "repo" / "plug"
    target.mkdir(parents=True)
    link = home / ".claude" / "skills" / "rel"
    try:
        os.symlink(Path("../../repo/plug"), link, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks need privileges on this machine")
    item = by_name(run(home)["skills"], "rel")
    assert item["link"] == "symlink"
    assert item["target"] == "repo/plug"


def test_install_path_outside_home_is_absolute(home, tmp_path):
    outside = tmp_path / "outside" / "p"
    write_json(outside / "hooks" / "hooks.json", hooks_file("Stop", "python s.py"))
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["plugins"]["far@market"] = [{"scope": "user", "installPath": str(outside)}]
    write_json(path, data)
    far = by_name(run(home)["plugins"], "far@market")
    prefix = (tmp_path / "outside").as_posix()
    assert far["install_path"].startswith(prefix)
    assert far["root"].startswith(prefix)
    assert far["hooks"][0]["file"].startswith(prefix)


def test_scheduled_task_files_listed(home):
    tasks = run(home)["scheduled_tasks"]
    assert [t["name"] for t in tasks] == ["daily"]
    assert tasks[0]["file"] == ".claude/scheduled-tasks/daily"
    assert tasks[0]["files"] == [
        ".claude/scheduled-tasks/daily/SKILL.md",
        ".claude/scheduled-tasks/daily/notes.txt",
    ]


def test_instructions_listed(home):
    assert [i["file"] for i in run(home)["instructions"]] == [
        ".claude/CLAUDE.md",
        ".claude/agents/rev.md",
        ".claude/commands/go.md",
        ".claude/output-styles/terse.md",
    ]


def test_wrong_types_do_not_crash(tmp_path):
    fresh = tmp_path / "fresh"
    write_json(
        fresh / ".claude" / "settings.json",
        {"permissions": {"allow": "Bash"}, "hooks": [], "env": "x"},
    )
    write_json(fresh / ".claude.json", {"mcpServers": []})
    out = run(fresh)
    item = out["settings"][0]
    assert item["permissions"] == [] and item["hooks"] == [] and item["env"] == []
    assert out["mcp_servers"] == []
    assert out["errors"] == []
