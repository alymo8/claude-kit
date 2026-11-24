import json
import os
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module

INSTALL = PLUGIN / "install.py"
WRAPPER = PLUGIN / "install.ps1"
SUPERPOWERS = "superpowers@claude-plugins-official"


def env_without_config_dir():
    return {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}


def run_install(tmp_path, python=sys.executable, env=None, extra=()):
    return subprocess.run(
        [
            sys.executable,
            str(INSTALL),
            "--home",
            str(tmp_path / "home"),
            "--skills-dir",
            str(tmp_path / "skills"),
            "--settings",
            str(tmp_path / "settings.json"),
            "--python",
            python,
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env_without_config_dir() if env is None else env,
    )


def out(result):
    return result.stdout + result.stderr


def is_link(path):
    try:
        os.readlink(path)
    except (OSError, ValueError):
        return False
    return True


def make_dir_link(link, target):
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
        )
    else:
        os.symlink(target, link, target_is_directory=True)


def remove_link(link):
    # Only the link itself: a recursive delete would follow it into plugin/.
    if sys.platform == "win32":
        os.rmdir(link)
    else:
        os.unlink(link)


def drop_links(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for name in list(dirnames) + filenames:
            path = os.path.join(dirpath, name)
            if is_link(path):
                remove_link(path)
                if name in dirnames:
                    dirnames.remove(name)


@pytest.fixture(autouse=True)
def drop_kit_links(tmp_path):
    yield
    drop_links(tmp_path)


def test_creates_link_to_plugin(tmp_path):
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    link = tmp_path / "skills" / "agent-kit"
    assert (link / ".claude-plugin" / "plugin.json").exists()
    assert os.path.samefile(link, PLUGIN)
    assert "Installed" in result.stdout
    assert "Start a new Claude Code session" in result.stdout


def test_second_run_is_idempotent(tmp_path):
    assert run_install(tmp_path).returncode == 0
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert "already installed" in result.stdout
    assert "superpowers plugin is not enabled" in result.stdout
    assert "Start a new Claude Code session" not in result.stdout


def test_conflicting_directory_fails(tmp_path):
    folder = tmp_path / "skills" / "agent-kit"
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("x", encoding="utf-8")
    result = run_install(tmp_path)
    assert result.returncode == 1
    assert "already exists" in out(result)
    assert (folder / "keep.txt").read_text(encoding="utf-8") == "x"


def test_blocked_new_link_still_migrates(tmp_path):
    skills, settings = old_link_and_statusline(tmp_path)
    folder = skills / "agent-kit"
    folder.mkdir()
    (folder / "keep.txt").write_text("x", encoding="utf-8")
    result = run_install(tmp_path)
    assert result.returncode == 1
    assert "already exists" in out(result)
    assert (folder / "keep.txt").read_text(encoding="utf-8") == "x"
    assert not os.path.lexists(skills / "claude-kit")
    new = (skills / "agent-kit" / "scripts" / "statusline.py").as_posix()
    assert statusline_command(settings) == f'python "{new}"'


def test_dangling_link_fails_cleanly(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    link = skills / "agent-kit"
    make_dir_link(link, victim)
    victim.rmdir()  # the link now dangles
    result = run_install(tmp_path)
    assert result.returncode == 1
    assert "already exists" in out(result)
    assert os.path.lexists(link)


def test_install_adds_statusline_to_given_settings(tmp_path):
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert "statusLine added" in result.stdout
    text = (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert "statusLine" in json.loads(text)
    assert "statusline.py" in text


def test_install_survives_malformed_settings(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{oops", encoding="utf-8")
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert "Installed" in result.stdout
    assert settings.read_text(encoding="utf-8") == "{oops"
    assert "WARNING: status line not configured" in result.stdout
    assert "superpowers plugin is not enabled" in result.stdout


def test_superpowers_enabled_gives_no_warning(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"enabledPlugins": {SUPERPOWERS: True}}), encoding="utf-8"
    )
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert "superpowers plugin is not enabled" not in result.stdout


def test_superpowers_missing_warns_with_install_command(tmp_path):
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert f"/plugin install {SUPERPOWERS}" in result.stdout


def test_missing_python_changes_nothing(tmp_path):
    result = run_install(tmp_path, python="claude-kit-no-such-python")
    assert result.returncode == 1
    assert 'ERROR: hooks run "claude-kit-no-such-python"' in result.stdout
    assert "is not on PATH" in result.stdout
    assert not os.path.lexists(tmp_path / "skills" / "agent-kit")
    assert not (tmp_path / "settings.json").exists()


def test_missing_git_and_gh_only_warn(tmp_path):
    only_python = os.path.dirname(sys.executable)
    if shutil.which("git", path=only_python) or shutil.which("gh", path=only_python):
        pytest.skip("git or gh sits next to the Python interpreter")
    env = dict(os.environ, PATH=only_python)
    result = run_install(tmp_path, env=env)
    assert result.returncode == 0, out(result)
    assert "WARNING: git not found on PATH" in result.stdout
    assert "WARNING: gh not found on PATH" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell wrapper")
def test_powershell_wrapper_runs_installer(tmp_path):
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WRAPPER),
            "-SkillsDir",
            str(tmp_path / "skills"),
            "-Settings",
            str(tmp_path / "settings.json"),
            "-Home",
            str(tmp_path / "home"),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env_without_config_dir(),
    )
    assert result.returncode == 0, out(result)
    assert os.path.samefile(tmp_path / "skills" / "agent-kit", PLUGIN)


def write_record(config, copy):
    plugins = config / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    entry = {"scope": "user", "installPath": str(copy), "version": "1.0.0"}
    record = {"version": 2, "plugins": {"agent-kit@agent-kit": [entry]}}
    (plugins / "installed_plugins.json").write_text(json.dumps(record), "utf-8")


def fake_marketplace(home: Path) -> Path:
    config = home / ".claude"
    copy = config / "plugins" / "cache" / "agent-kit" / "agent-kit" / "1.0.0"
    copy.mkdir(parents=True)
    write_record(config, copy)
    return copy


def old_link_and_statusline(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    make_dir_link(skills / "claude-kit", PLUGIN)
    old = (skills / "claude-kit" / "scripts" / "statusline.py").as_posix()
    line = {"type": "command", "command": f'python "{old}"'}
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"statusLine": line}), encoding="utf-8")
    return skills, settings


def statusline_command(settings):
    return json.loads(settings.read_text(encoding="utf-8"))["statusLine"]["command"]


def test_replaces_legacy_link_and_statusline(tmp_path):
    skills, settings = old_link_and_statusline(tmp_path)
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert not os.path.lexists(skills / "claude-kit")
    assert is_link(skills / "agent-kit")
    assert os.path.samefile(skills / "agent-kit", PLUGIN)
    new = (skills / "agent-kit" / "scripts" / "statusline.py").as_posix()
    assert statusline_command(settings) == f'python "{new}"'


def test_marketplace_copy_present_creates_no_link(tmp_path):
    home = tmp_path / "home"
    fake_marketplace(home)
    skills, settings = old_link_and_statusline(tmp_path)
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert not os.path.lexists(skills / "claude-kit")
    assert not os.path.lexists(skills / "agent-kit")
    assert "marketplace" in result.stdout
    stable = home / ".claude" / "claude-kit" / "statusline.py"
    assert statusline_command(settings) == f'python "{stable.as_posix()}"'
    assert stable.is_file()


def test_marketplace_copy_removes_own_agent_kit_link(tmp_path):
    fake_marketplace(tmp_path / "home")
    skills = tmp_path / "skills"
    skills.mkdir()
    make_dir_link(skills / "agent-kit", PLUGIN)
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert not os.path.lexists(skills / "agent-kit")
    assert "Removed" in result.stdout
    assert PLUGIN.is_dir()


def test_marketplace_copy_keeps_foreign_agent_kit(tmp_path):
    fake_marketplace(tmp_path / "home")
    skills = tmp_path / "skills"
    folder = skills / "agent-kit"
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("x", encoding="utf-8")
    other = tmp_path / "other"
    other.mkdir()
    make_dir_link(skills / "claude-kit", other)
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert (folder / "keep.txt").is_file()
    assert is_link(skills / "claude-kit")


def test_dangling_old_link_is_left_with_a_note(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    link = skills / "claude-kit"
    make_dir_link(link, victim)
    victim.rmdir()
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert os.path.lexists(link)
    assert "points nowhere" in result.stdout
    assert str(link) in result.stdout


def test_config_dir_env_is_honoured(tmp_path):
    cfg = tmp_path / "cfg"
    copy = tmp_path / "copy"
    copy.mkdir()
    write_record(cfg, copy)
    env = dict(env_without_config_dir(), CLAUDE_CONFIG_DIR=str(cfg))
    result = run_install(tmp_path, env=env)
    assert result.returncode == 0, out(result)
    assert not os.path.lexists(tmp_path / "skills" / "agent-kit")
    stable = cfg / "claude-kit" / "statusline.py"
    command = statusline_command(tmp_path / "settings.json")
    assert command == f'python "{stable.as_posix()}"'


@pytest.mark.parametrize(
    "record", ["{oops", "[]", '{"plugins": {"agent-kit@agent-kit": 3}}']
)
def test_malformed_installed_plugins_links_normally(tmp_path, record):
    plugins = tmp_path / "home" / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "installed_plugins.json").write_text(record, encoding="utf-8")
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert os.path.samefile(tmp_path / "skills" / "agent-kit", PLUGIN)


def test_foreign_claude_kit_folder_left_alone(tmp_path):
    folder = tmp_path / "skills" / "claude-kit"
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("x", encoding="utf-8")
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert not is_link(folder)
    assert (folder / "keep.txt").read_text(encoding="utf-8") == "x"
    assert os.path.samefile(tmp_path / "skills" / "agent-kit", PLUGIN)


def installer():
    return load_module(INSTALL, "kit_install")


@pytest.mark.parametrize(
    ("platform", "name"),
    [
        ("win32", "Windows"),
        ("darwin", "macOS"),
        ("linux", "Linux"),
        ("freebsd14", "freebsd14"),
    ],
)
def test_os_name(platform, name):
    assert installer().os_name(platform) == name


def test_prints_detected_os(tmp_path):
    result = run_install(tmp_path)
    expected = installer().os_name(sys.platform)
    assert f"Detected: {expected}" in result.stdout


def test_mac_fix_points_at_brew_libexec_on_path(tmp_path):
    libexec = tmp_path / "opt" / "python@3" / "libexec" / "bin"
    libexec.mkdir(parents=True)
    (libexec / "python").write_text("")
    fix = installer().fix_for("darwin", "python", libexec_dirs=[libexec])
    assert str(libexec) in fix
    assert "~/.zprofile" in fix
    assert "alias" not in fix


def test_mac_fix_without_brew_python(tmp_path):
    fix = installer().fix_for("darwin", "python", libexec_dirs=[tmp_path / "none"])
    assert "brew install python@3" in fix
    assert "libexec/bin" in fix
    assert "alias" not in fix


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
def test_no_platform_fix_suggests_an_alias(platform, tmp_path):
    fix = installer().fix_for(platform, "python", libexec_dirs=[tmp_path / "none"])
    assert "alias" not in fix
    assert fix


def test_docs_do_not_suggest_a_python_alias():
    setup = (PLUGIN.parent / "docs" / "setup.md").read_text(encoding="utf-8")
    assert "alias of `python3`" not in setup
    assert "~/.zprofile" in setup


AGENTS = ("vibe", "codex", "cursor")
VENDOR = PLUGIN.parent / "vendor" / "superpowers" / "skills"


def run_agent(tmp_path, agent, *extra):
    home = tmp_path / "home"
    args = ["--agent", agent, "--home", str(home), "--python", sys.executable]
    return subprocess.run(
        [sys.executable, str(INSTALL), *args, *extra],
        capture_output=True,
        text=True,
        timeout=120,
    )


def skills(tmp_path):
    return tmp_path / "home" / ".agents" / "skills"


def snapshot(root):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in list(dirnames) + filenames:
            path = os.path.join(dirpath, name)
            if is_link(path):
                found[path] = "link:" + os.readlink(path)
                if name in dirnames:
                    dirnames.remove(name)
            elif name in filenames:
                with open(path, "rb") as handle:
                    found[path] = handle.read()
    return found


@pytest.mark.parametrize("agent", ("codex", "cursor"))
def test_agent_links_every_skill(tmp_path, agent):
    result = run_agent(tmp_path, agent)
    assert result.returncode == 0, out(result)
    expected = {
        "spec-gate": PLUGIN / "skills" / "spec-gate",
        "ship": PLUGIN / "agent-skills" / "ship",
        "brainstorming": VENDOR / "brainstorming",
    }
    for name, target in expected.items():
        link = skills(tmp_path) / name
        assert is_link(link) and os.path.samefile(link, target), name
    assert not (tmp_path / "home" / ".claude").exists()


def test_agent_skills_dir_override(tmp_path):
    other = tmp_path / "home" / "other-skills"
    result = run_agent(tmp_path, "codex", "--skills-dir", str(other))
    assert result.returncode == 0, out(result)
    assert os.path.samefile(other / "spec-gate", PLUGIN / "skills" / "spec-gate")
    assert not skills(tmp_path).exists()


def test_foreign_entry_left_alone(tmp_path):
    foreign = skills(tmp_path) / "spec-gate"
    foreign.mkdir(parents=True)
    (foreign / "keep.txt").write_text("mine", encoding="utf-8")
    result = run_agent(tmp_path, "codex")
    assert result.returncode == 0, out(result)
    assert not is_link(foreign) and (foreign / "keep.txt").is_file()
    assert "Skipped" in result.stdout and "spec-gate" in result.stdout


def test_dangling_kit_link_removed(tmp_path):
    skills(tmp_path).mkdir(parents=True)
    old = skills(tmp_path) / "old-skill"
    try:
        make_dir_link(old, PLUGIN / "skills" / "no-such-skill")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("cannot create a dangling link here")
    result = run_agent(tmp_path, "codex")
    assert result.returncode == 0, out(result)
    assert not os.path.lexists(old)


def test_codex_hooks_json(tmp_path):
    path = tmp_path / "home" / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True)
    mine = {"hooks": [{"type": "command", "command": "echo mine"}]}
    path.write_text(json.dumps({"hooks": {"SessionStart": [mine]}, "x": 1}), "utf-8")
    assert run_agent(tmp_path, "codex").returncode == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["x"] == 1
    start = data["hooks"]["SessionStart"]
    assert start[0] == mine and len(start) == 2
    command = start[1]["hooks"][0]["command"]
    assert command.endswith('run.py" --agent codex --event SessionStart')
    stop = data["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert stop.endswith('run.py" --agent codex --event Stop')


def test_cursor_hooks_json(tmp_path):
    path = tmp_path / "home" / ".cursor" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"version": 1, "hooks": {"stop": [{"command": "echo mine"}]}}),
        encoding="utf-8",
    )
    result = run_agent(tmp_path, "cursor")
    assert result.returncode == 0, out(result)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["hooks"]["stop"][0] == {"command": "echo mine"}
    assert data["hooks"]["stop"][1]["command"].endswith("--event Stop")
    start = data["hooks"]["sessionStart"][0]["command"]
    assert start.endswith('run.py" --agent cursor --event SessionStart')
    assert "user rules" in result.stdout and "run.py" in result.stdout
    assert not (tmp_path / "home" / ".cursor" / "AGENTS.md").exists()


@pytest.mark.parametrize("agent", ["vibe", "codex"])
def test_agents_md_block(tmp_path, agent):
    path = tmp_path / "home" / f".{agent}" / "AGENTS.md"
    path.parent.mkdir(parents=True)
    path.write_text("my rules\n", encoding="utf-8")
    run_agent(tmp_path, agent)
    run_agent(tmp_path, agent)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("my rules\n")
    assert text.count("<!-- agent-kit:begin") == 1
    assert "Kit map (agent-kit)" in text
    assert f'run.py" --agent {agent} --event SessionStart' in text


@pytest.mark.parametrize("agent", AGENTS)
def test_second_run_changes_no_byte(tmp_path, agent):
    assert run_agent(tmp_path, agent).returncode == 0
    before = snapshot(tmp_path / "home")
    assert run_agent(tmp_path, agent).returncode == 0
    assert snapshot(tmp_path / "home") == before


def test_malformed_hook_file_changes_nothing(tmp_path):
    path = tmp_path / "home" / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text("{oops", encoding="utf-8")
    result = run_agent(tmp_path, "codex")
    assert result.returncode == 1 and "ERROR" in result.stdout
    assert path.read_text(encoding="utf-8") == "{oops"
    assert not skills(tmp_path).exists()


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("hooks.toml", "a = 1\n# >>> {kit} hooks (managed by x) >>>\nold\n"),
        ("hooks.toml", "# <<< {kit} hooks <<<\nmine = 2\n"),
        ("AGENTS.md", "mine\n<!-- {kit}:begin (managed by x) -->\nold\n"),
    ],
)
def test_damaged_block_markers_change_nothing(tmp_path, name, text, legacy):
    mod = installer()
    text = text.format(kit="claude-kit" if legacy else "agent-kit")
    if legacy:
        begin = mod.LEGACY_TOML_BEGIN if "toml" in name else mod.LEGACY_MD_BEGIN
    else:
        begin = mod.TOML_BEGIN if "toml" in name else mod.MD_BEGIN
    text = text.replace(begin.split("(")[0] + "(managed by x)", begin)
    path = tmp_path / "home" / ".vibe" / name
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 1 and "markers are damaged" in result.stdout
    assert path.read_text(encoding="utf-8") == text
    assert not skills(tmp_path).exists()
    assert not (tmp_path / "home" / ".vibe" / "plugins").exists()


def test_kit_link_to_moved_skill_relinked(tmp_path):
    skills(tmp_path).mkdir(parents=True)
    link = skills(tmp_path) / "ship"
    make_dir_link(link, PLUGIN / "skills" / "spec-gate")
    result = run_agent(tmp_path, "codex")
    assert result.returncode == 0, out(result)
    assert "Relinked ship" in result.stdout
    assert os.path.samefile(link, PLUGIN / "agent-skills" / "ship")


@pytest.mark.parametrize(
    ("agent", "step"),
    [
        ("codex", "/hooks"),
        ("vibe", "new Vibe session"),
        ("cursor", "new Cursor agent chat"),
    ],
)
def test_report_names_next_step(tmp_path, agent, step):
    assert step in run_agent(tmp_path, agent).stdout


# The existing test_install.py cases stay unedited (apart from the fixture and
# run_install's extra parameter): they are the guard for today's behaviour.
def test_agent_claude_matches_default(tmp_path):
    results = []
    for name, extra in (("a", ()), ("b", ("--agent", "claude"))):
        root = tmp_path / name
        result = run_install(root, extra=extra)
        assert result.returncode == 0, out(result)
        results.append((result.stdout.replace(str(root), "<t>"), root))
    assert results[0][0] == results[1][0]
    assert sorted(os.listdir(results[0][1])) == sorted(os.listdir(results[1][1]))


POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell not on PATH")
def test_powershell_wrapper_agent_vibe(tmp_path):
    env = dict(os.environ, HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    command = [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass"]
    command += ["-File", str(WRAPPER), "-Agent", "vibe", "-Home", str(tmp_path)]
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=120, env=env
    )
    assert result.returncode == 0, out(result)
    plugins = tmp_path / ".vibe" / "plugins"
    for name in ("agent-kit", "superpowers"):
        assert (plugins / name / "plugin.json").is_file(), name
    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / ".claude" / "skills").exists()
    written = {
        Path(line.split(" ", 1)[1]).resolve()
        for line in result.stdout.splitlines()
        if line.startswith(("Wrote ", "Unchanged "))
    }
    assert (tmp_path / ".vibe").resolve() / "AGENTS.md" in written
    for path in written:
        assert path.is_relative_to(tmp_path.resolve()), path


def legacy_files(agent):
    mod = installer()
    md = ("AGENTS.md", mod.LEGACY_MD_BEGIN, mod.LEGACY_MD_END, mod.MD_BEGIN)
    return [md]


@pytest.mark.parametrize("agent", ["vibe", "codex"])
def test_legacy_blocks_replaced(tmp_path, agent):
    base = tmp_path / "home" / f".{agent}"
    base.mkdir(parents=True)
    files = legacy_files(agent)
    for name, begin, end, _ in files:
        text = f"mine\n\n{begin}\nold line\n{end}\n"
        (base / name).write_text(text, encoding="utf-8")
    result = run_agent(tmp_path, agent)
    assert result.returncode == 0, out(result)
    for name, begin, end, new_begin in files:
        text = (base / name).read_text(encoding="utf-8")
        assert text.startswith("mine\n"), name
        assert begin not in text and end not in text, name
        assert "old line" not in text, name
        assert text.count(new_begin) == 1, name


def test_old_and_new_blocks_collapse_to_one(tmp_path):
    mod = installer()
    path = tmp_path / "home" / ".codex" / "AGENTS.md"
    path.parent.mkdir(parents=True)
    old = f"{mod.LEGACY_MD_BEGIN}\nold\n{mod.LEGACY_MD_END}\n"
    new = f"{mod.MD_BEGIN}\nnew\n{mod.MD_END}\n"
    path.write_text(f"mine\n\n{old}\n{new}", encoding="utf-8")
    result = run_agent(tmp_path, "codex")
    assert result.returncode == 0, out(result)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("mine\n")
    assert mod.LEGACY_MD_BEGIN not in text
    assert text.count(mod.MD_BEGIN) == 1 and text.count(mod.MD_END) == 1


def test_cursor_old_entry_replaced(tmp_path):
    path = tmp_path / "home" / ".cursor" / "hooks.json"
    path.parent.mkdir(parents=True)
    old = 'python3 "/old/checkout/plugin/hooks/run.py" --agent cursor'
    old += " --event SessionStart"
    data = {"version": 1, "hooks": {"sessionStart": [{"command": old}]}}
    path.write_text(json.dumps(data), encoding="utf-8")
    result = run_agent(tmp_path, "cursor")
    assert result.returncode == 0, out(result)
    start = json.loads(path.read_text(encoding="utf-8"))["hooks"]["sessionStart"]
    expected = installer().hook_command(sys.executable, "cursor", "SessionStart")
    assert start == [{"command": expected}]


def vibe(tmp_path):
    return tmp_path / "home" / ".vibe"


def kit_link(tmp_path, name, target):
    skills(tmp_path).mkdir(parents=True, exist_ok=True)
    make_dir_link(skills(tmp_path) / name, target)


def test_vibe_installs_two_plugins(tmp_path):
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    for name in ("agent-kit", "superpowers"):
        folder = vibe(tmp_path) / "plugins" / name
        assert (folder / "plugin.json").is_file(), name
        assert (folder / ".agent-kit-build").is_file(), name
    assert not skills(tmp_path).exists()
    assert not (vibe(tmp_path) / "hooks.toml").exists()
    assert not (vibe(tmp_path) / ".agent-kit-staging").exists()
    step = "Next: start a new Vibe session (or run /reload-plugins)."
    assert step in result.stdout


def test_vibe_removes_kit_block_keeps_user_hook(tmp_path):
    mod = installer()
    path = vibe(tmp_path) / "hooks.toml"
    path.parent.mkdir(parents=True)
    mine = '[[hooks]]\nname = "mine"\ntype = "session_start"\ncommand = "echo"\n'
    block = f"{mod.TOML_BEGIN}\nold = 1\n{mod.TOML_END}\n"
    path.write_text(f"{mine}\n{block}", encoding="utf-8")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    text = path.read_text(encoding="utf-8")
    assert mod.TOML_BEGIN not in text and "old = 1" not in text
    assert [h["name"] for h in tomllib.loads(text)["hooks"]] == ["mine"]


def test_vibe_removes_legacy_block_keeps_user_text(tmp_path):
    mod = installer()
    path = vibe(tmp_path) / "hooks.toml"
    path.parent.mkdir(parents=True)
    old = f"{mod.LEGACY_TOML_BEGIN}\nold = 1\n{mod.LEGACY_TOML_END}\n"
    path.write_text(f"mine = 1\n\n{old}", encoding="utf-8")
    assert run_agent(tmp_path, "vibe").returncode == 0
    assert path.read_text(encoding="utf-8") == "mine = 1\n"


def test_vibe_removes_legacy_block_and_deletes_empty_file(tmp_path):
    mod = installer()
    path = vibe(tmp_path) / "hooks.toml"
    path.parent.mkdir(parents=True)
    old = f"{mod.LEGACY_TOML_BEGIN}\nold = 1\n{mod.LEGACY_TOML_END}\n"
    new = f"{mod.TOML_BEGIN}\nnew = 1\n{mod.TOML_END}\n"
    path.write_text(f"\n{old}\n{new}", encoding="utf-8")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert not path.exists()


def test_vibe_agents_md_names_the_copy(tmp_path):
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    text = (vibe(tmp_path) / "AGENTS.md").read_text(encoding="utf-8")
    runner = vibe(tmp_path) / "plugins" / "agent-kit" / "hooks" / "run.py"
    expected = f'"{runner.resolve().as_posix()}" --agent vibe --event SessionStart'
    assert expected in text


def test_vibe_removes_old_kit_links_keeps_foreign(tmp_path):
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    kit_link(tmp_path, "ship", PLUGIN / "agent-skills" / "ship")
    kit_link(tmp_path, "brainstorming", VENDOR / "brainstorming")
    mine = tmp_path / "mine"
    mine.mkdir()
    kit_link(tmp_path, "mine", mine)
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert sorted(os.listdir(skills(tmp_path))) == ["mine"]
    assert is_link(skills(tmp_path) / "mine")


def test_vibe_removes_dangling_kit_link(tmp_path):
    skills(tmp_path).mkdir(parents=True)
    gone = skills(tmp_path) / "gone"
    try:
        make_dir_link(gone, PLUGIN / "skills" / "no-such-skill")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("cannot create a dangling link here")
    assert run_agent(tmp_path, "vibe").returncode == 0
    assert not os.path.lexists(gone)


@pytest.mark.parametrize("agent", ["codex", "cursor"])
def test_vibe_keeps_links_while_other_agent_uses_them(tmp_path, agent):
    path = tmp_path / "home" / f".{agent}" / "hooks.json"
    path.parent.mkdir(parents=True)
    text = installer().json_hooks("", agent, sys.executable)
    path.write_text(text, encoding="utf-8")
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert is_link(skills(tmp_path) / "spec-gate")
    assert "WARNING" in result.stdout and "twice" in result.stdout


def test_vibe_unreadable_other_hook_file_counts_as_in_use(tmp_path):
    path = tmp_path / "home" / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text("{oops", encoding="utf-8")
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert is_link(skills(tmp_path) / "spec-gate")
    assert "WARNING" in result.stdout and "twice" in result.stdout


@pytest.mark.parametrize("name", ["agent-kit", "superpowers"])
def test_vibe_foreign_plugin_folder_changes_nothing(tmp_path, name):
    mod = installer()
    base = vibe(tmp_path)
    (base / "plugins" / name).mkdir(parents=True)
    (base / "plugins" / name / "plugin.json").write_text("{}", encoding="utf-8")
    block = f"{mod.TOML_BEGIN}\nold = 1\n{mod.TOML_END}\n"
    (base / "hooks.toml").write_text(block, encoding="utf-8")
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    before = snapshot(tmp_path / "home")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 1 and "ERROR" in result.stdout
    assert f"plugins{os.sep}{name}" in result.stdout
    assert snapshot(tmp_path / "home") == before


PATHS = [
    "python",
    "C:/Python311/python.exe",
    "C:/Program Files/python.exe",
    "C:/Users/O'Neil/python.exe",
    "C:/a&b/python.exe",
    "C:/py(3)/python.exe",
    "C:/Users/José/python.exe",
]
UNCHANGED = ["python", "C:/Python311/python.exe", "C:/Users/José/python.exe"]
BAD = [
    'C:/a"b/python.exe',
    "C:/a$b/python.exe",
    "C:/a`b/python.exe",
    "C:/a%b/python.exe",
]


def test_vibe_runner_command_matches_hook_command(tmp_path):
    builder = load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")
    runner = tmp_path / "run.py"
    for python in [*PATHS, "C:\\Python311\\python.exe"]:
        expected = installer().hook_command(python, "vibe", "Stop", runner=runner)
        assert builder.runner_command(python, runner, "Stop") == expected


def refusal_line(python):
    char = next(c for c in python if c in '"$`%')
    return (
        f"ERROR: --python {python} contains {char}, which a hook command "
        "cannot quote safely; nothing changed."
    )


@pytest.mark.parametrize("python", PATHS)
def test_hook_command_splits_back_to_python(tmp_path, python):
    runner = tmp_path / "run.py"
    command = installer().hook_command(python, "codex", "Stop", runner=runner)
    assert shlex.split(command)[:2] == [python, runner.as_posix()]


@pytest.mark.parametrize("python", UNCHANGED)
def test_hook_command_unchanged_for_plain_paths(tmp_path, python):
    runner = tmp_path / "run.py"
    command = installer().hook_command(python, "codex", "Stop", runner=runner)
    assert command == f'{python} "{runner.as_posix()}" --agent codex --event Stop'


def test_hook_command_keeps_backslash_path_bare(tmp_path):
    python = "C:\\Python311\\python.exe"
    runner = tmp_path / "run.py"
    command = installer().hook_command(python, "codex", "Stop", runner=runner)
    assert command.startswith(python + " ")


def test_codex_hooks_rerun_with_quoted_python_is_stable():
    mod = installer()
    python = "C:/Users/O'Neil/python.exe"
    once = mod.json_hooks("", "codex", python)
    assert mod.json_hooks(once, "codex", python) == once
    assert len(json.loads(once)["hooks"]["Stop"]) == 1


@pytest.mark.parametrize("agent", ["vibe", "codex"])
@pytest.mark.parametrize("python", BAD)
def test_unquotable_python_refused(tmp_path, agent, python):
    mod = installer()
    base = vibe(tmp_path)
    base.mkdir(parents=True)
    block = f"{mod.TOML_BEGIN}\nold = 1\n{mod.TOML_END}\n"
    (base / "hooks.toml").write_text(block, encoding="utf-8")
    before = snapshot(tmp_path)
    result = run_agent(tmp_path, agent, "--python", python)
    assert result.returncode == 1, out(result)
    assert refusal_line(python) in result.stdout
    assert "is not on PATH" not in result.stdout
    assert snapshot(tmp_path) == before


def test_claude_install_does_not_refuse_python_path(tmp_path):
    result = run_install(tmp_path, python="C:/a%b/python.exe")
    assert result.returncode == 1
    assert "cannot quote safely" not in result.stdout
    assert "is not on PATH" in result.stdout


def test_refusal_text_matches_builder():
    builder = load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")
    for python in BAD:
        char = installer().unquotable(python)
        assert char == builder.unquotable(python)
        assert installer().refusal(python, char) == builder.refusal(python, char)


def test_vibe_build_turns_stuck_staging_into_build_error(tmp_path, monkeypatch):
    vibe = load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")
    out = tmp_path / "plugins"
    (tmp_path / ".agent-kit-staging" / "agent-kit").mkdir(parents=True)

    def stuck(path, ignore_errors=False, **kwargs):
        if not ignore_errors:
            raise PermissionError(f"in use: {path}")

    monkeypatch.setattr(vibe.shutil, "rmtree", stuck)
    with pytest.raises(vibe.BuildError):
        vibe.build(out, python="python")
    assert not out.exists()


def test_vibe_restore_error_keeps_staging_message(tmp_path, monkeypatch, capsys):
    vp = load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")
    home = tmp_path / "home"
    plugins = (home / ".vibe" / "plugins").resolve()
    vp.build(plugins, sys.executable)
    real = os.rename

    def flaky(src, dst):
        src, dst = Path(src), Path(dst)
        if src.name == "superpowers" and src.parent.name == ".agent-kit-staging":
            raise OSError("locked")
        if src.name == "agent-kit.old" and dst.parent == plugins:
            raise OSError("restore blocked")
        return real(src, dst)

    monkeypatch.setattr(vp.os, "rename", flaky)
    code = installer().install_vibe(home, skills(tmp_path), sys.executable)
    printed = capsys.readouterr().out
    assert code == 1
    assert str(plugins.parent / ".agent-kit-staging") in printed
    assert "nothing changed" not in printed
