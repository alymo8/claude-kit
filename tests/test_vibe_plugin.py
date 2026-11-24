import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from helpers import PLUGIN, REPO, clean_env, load_module

BUILDER = PLUGIN / "vibe_plugin.py"
VENDOR = REPO / "vendor" / "superpowers"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
NAME_RE = re.compile(r"[a-z0-9.-]+")
NAMES = ("agent-kit", "superpowers")
STAGING = ".agent-kit-staging"


def builder():
    return load_module(BUILDER, "vibe_plugin")


def claude_manifest():
    path = PLUGIN / ".claude-plugin" / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run_builder(out, *extra):
    command = [sys.executable, str(BUILDER), "--out", str(out)]
    command += ["--python", sys.executable, *extra]
    return subprocess.run(command, capture_output=True, text=True, timeout=120)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("vibe") / "plugins"
    result = run_builder(out)
    assert result.returncode == 0, result.stdout + result.stderr
    return out


def manifest(root, name):
    return json.loads((root / name / "plugin.json").read_text(encoding="utf-8"))


def skill_names(root):
    return {d.name for d in root.iterdir() if (d / "SKILL.md").is_file()}


def is_link(path):
    try:
        os.readlink(path)
    except (OSError, ValueError):
        return False
    return True


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.mark.parametrize("name", NAMES)
def test_manifest_shape(built, name):
    data = manifest(built, name)
    assert data["$schema"] == SCHEMA
    assert data["name"] == name and NAME_RE.fullmatch(data["name"])
    assert data["extensions"]["ai.mistral.vibe"]["schemaVersion"] == 1


def test_agent_kit_manifest_follows_claude_manifest(built):
    data = manifest(built, "agent-kit")
    claude = claude_manifest()
    for key in ("version", "description", "author", "license"):
        assert data[key] == claude[key], key
    assert data["repository"] == "https://github.com/alymo8/claude-kit"
    assert data["extensions"]["ai.mistral.vibe"]["displayName"] == "agent-kit"


def test_superpowers_manifest_follows_version_file(built):
    version, source = builder().read_version_file(VENDOR / "VERSION")
    data = manifest(built, "superpowers")
    assert data["version"] == version and data["repository"] == source
    assert data["license"] == "MIT"
    assert "agent-kit" in data["description"]


def test_skill_sets(built):
    kit = skill_names(PLUGIN / "skills") | skill_names(PLUGIN / "agent-skills")
    assert skill_names(built / "agent-kit" / "skills") == kit
    assert len(kit) == 20
    vendored = skill_names(VENDOR / "skills")
    assert skill_names(built / "superpowers" / "skills") == vendored
    assert len(vendored) == 12


@pytest.mark.parametrize("name", NAMES)
def test_skill_names_match_folders(built, name):
    for skill in sorted((built / name / "skills").iterdir()):
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---", 2)[1]
        found = re.search(r"^name:\s*(\S+)\s*$", front, re.M)
        assert found and found.group(1) == skill.name, skill.name


def test_hooks_toml(built):
    path = built / "agent-kit" / "ai.mistral.vibe" / "hooks.toml"
    hooks = tomllib.loads(path.read_text(encoding="utf-8"))["hooks"]
    runner = (built / "agent-kit" / "hooks" / "run.py").resolve().as_posix()
    names = [h["name"] for h in hooks]
    assert names == ["agent-kit-session-start", "agent-kit-stop"]
    assert hooks[0]["type"] == "session_start" and "match" not in hooks[0]
    assert hooks[1]["type"] == "post_agent" and hooks[1]["match"] == "main"
    for hook, event in zip(hooks, ("SessionStart", "Stop"), strict=True):
        argv = shlex.split(hook["command"])
        assert argv[1] == runner
        assert argv[2:] == ["--agent", "vibe", "--event", event]


@pytest.mark.parametrize("name", NAMES)
def test_plain_files_only(built, name):
    root = built / name
    for dirpath, dirnames, filenames in os.walk(root):
        for entry in dirnames + filenames:
            assert not is_link(os.path.join(dirpath, entry)), entry
    assert not (root / ".claude-plugin").exists()
    marker = (root / ".agent-kit-build").read_text(encoding="utf-8")
    assert marker == claude_manifest()["version"] + "\n"


def test_agent_kit_copy_leaves_out_installer_files(built):
    root = built / "agent-kit"
    for name in ("agent-skills", "install.py", "install.ps1", "vibe_plugin.py"):
        assert not (root / name).exists(), name
    assert not list(root.rglob("__pycache__")) and not list(root.rglob("*.pyc"))
    for name in ("rules.md", "hooks/hooks.json", "conventions/README.md"):
        assert (root / name).is_file(), name


def test_superpowers_carries_license_and_version(built):
    for name in ("LICENSE", "VERSION"):
        copied = (built / "superpowers" / name).read_bytes()
        assert copied == (VENDOR / name).read_bytes(), name


def test_built_runner_prints_kit_map(tmp_path):
    out = tmp_path / "plugins"
    assert run_builder(out).returncode == 0
    runner = out / "agent-kit" / "hooks" / "run.py"
    project = tmp_path / "proj"
    project.mkdir()
    result = subprocess.run(
        [sys.executable, str(runner), "--agent", "vibe", "--event", "SessionStart"],
        input=json.dumps({"cwd": str(project), "source": "startup"}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=project,
        env=clean_env(),
        timeout=120,
    )
    data = json.loads(result.stdout)
    text = data["hook_specific_output"]["additional_context"]
    assert "Kit map (agent-kit)" in text
    root = (out / "agent-kit").resolve().as_posix()
    assert f"Plugin root: {root}" in text


def test_rebuild_is_byte_identical_and_drops_runtime_files(tmp_path):
    out = tmp_path / "plugins"
    assert run_builder(out).returncode == 0
    before = snapshot(out)
    cache = out / "agent-kit" / "hooks" / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"0")
    assert run_builder(out).returncode == 0
    assert snapshot(out) == before
    assert not (tmp_path / STAGING).exists()


@pytest.mark.parametrize("name", NAMES)
def test_foreign_folder_refused(tmp_path, name):
    out = tmp_path / "plugins"
    (out / name).mkdir(parents=True)
    (out / name / "mine.txt").write_text("mine", encoding="utf-8")
    result = run_builder(out)
    assert result.returncode == 1 and "ERROR" in result.stdout
    assert f"plugins{os.sep}{name}" in result.stdout
    assert sorted(p.name for p in out.iterdir()) == [name]
    assert (out / name / "mine.txt").read_text(encoding="utf-8") == "mine"
    assert not (tmp_path / STAGING).exists()


def test_stale_staging_removed(tmp_path):
    stale = tmp_path / STAGING / "agent-kit"
    stale.mkdir(parents=True)
    (stale / "junk.txt").write_text("x", encoding="utf-8")
    assert run_builder(tmp_path / "plugins").returncode == 0
    assert not (tmp_path / STAGING).exists()


def fake_kit(tmp_path):
    kit = tmp_path / "kit"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(PLUGIN, kit / "plugin", ignore=ignore)
    shutil.copytree(VENDOR, kit / "vendor" / "superpowers", ignore=ignore)
    return kit


def test_failed_build_keeps_previous_copy(tmp_path):
    out = tmp_path / "plugins"
    assert run_builder(out).returncode == 0
    before = snapshot(out)
    kit = fake_kit(tmp_path)
    version_file = kit / "vendor" / "superpowers" / "VERSION"
    version_file.write_text("version: 1.0.0\n", encoding="utf-8")
    mod = builder()
    with pytest.raises(mod.BuildError, match="source"):
        mod.build(out, sys.executable, kit=kit)
    assert snapshot(out) == before
    assert not (tmp_path / STAGING).exists()


def test_failed_swap_restores_both_copies(tmp_path, monkeypatch):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    before = snapshot(out)
    real = os.rename

    def flaky(src, dst):
        src = Path(src)
        if src.name == "superpowers" and src.parent.name == STAGING:
            raise OSError("locked")
        return real(src, dst)

    monkeypatch.setattr(mod.os, "rename", flaky)
    with pytest.raises(mod.BuildError, match="locked"):
        mod.build(out, sys.executable)
    assert snapshot(out) == before
    assert not (tmp_path / STAGING).exists()


def test_version_file_needs_both_lines(tmp_path):
    mod = builder()
    path = tmp_path / "VERSION"
    path.write_text("version: 7.0.2\nsource: https://x.test/sp\n", encoding="utf-8")
    assert mod.read_version_file(path) == ("7.0.2", "https://x.test/sp")
    for text in ("version: 7.0.2\n", "source: https://x.test/sp\n", "version:\n"):
        path.write_text(text, encoding="utf-8")
        with pytest.raises(mod.BuildError):
            mod.read_version_file(path)


def test_duplicate_skill_name_is_a_build_error(tmp_path):
    mod = builder()
    for root in ("a", "b"):
        (tmp_path / root / "same").mkdir(parents=True)
        (tmp_path / root / "same" / "SKILL.md").write_text("x", encoding="utf-8")
    with pytest.raises(mod.BuildError, match="same"):
        mod.merge_skills([tmp_path / "a", tmp_path / "b"], tmp_path / "out")


def test_hooks_toml_quotes_spaces(tmp_path):
    python = "C:/Program Files/Python/python.exe"
    runner = tmp_path / "dir with space" / "run.py"
    hooks = tomllib.loads(builder().hooks_toml(python, runner))["hooks"]
    argv = shlex.split(hooks[0]["command"])
    assert argv[:2] == [python, runner.as_posix()]


def test_hooks_toml_survives_quote_in_python_path(tmp_path):
    python = "C:/Users/O'Neil/python.exe"
    runner = tmp_path / "run.py"
    hooks = tomllib.loads(builder().hooks_toml(python, runner))["hooks"]
    for hook in hooks:
        assert shlex.split(hook["command"])[:2] == [python, runner.as_posix()]


PATHS = [
    "python",
    "C:/Python311/python.exe",
    "C:/Program Files/python.exe",
    "C:/Users/O'Neil/python.exe",
    "C:/a&b/python.exe",
    "C:/py(3)/python.exe",
    "C:/Users/José/python.exe",
]
BAD = [
    'C:/a"b/python.exe',
    "C:/a$b/python.exe",
    "C:/a`b/python.exe",
    "C:/a%b/python.exe",
]


@pytest.mark.parametrize("python", PATHS)
def test_runner_command_splits_back_to_python(tmp_path, python):
    runner = tmp_path / "run.py"
    command = builder().runner_command(python, runner, "Stop")
    assert shlex.split(command)[:2] == [python, runner.as_posix()]


@pytest.mark.parametrize("python", BAD)
def test_builder_refuses_unquotable_python(tmp_path, python):
    out = tmp_path / "plugins"
    char = next(c for c in python if c in '"$`%')
    result = run_builder(out, "--python", python)
    assert result.returncode == 1
    expected = (
        f"ERROR: --python {python} contains {char}, which a hook command "
        "cannot quote safely; nothing changed."
    )
    assert expected in result.stdout
    assert not out.exists() and not (tmp_path / STAGING).exists()
    mod = builder()
    with pytest.raises(mod.BuildError, match="cannot quote safely"):
        mod.build(out, python)


def fail_restore(mod, monkeypatch, out):
    """Make the superpowers swap fail and the agent-kit restore fail too."""
    real = os.rename

    def flaky(src, dst):
        src, dst = Path(src), Path(dst)
        if src.name == "superpowers" and src.parent.name == STAGING:
            raise OSError("locked")
        if src.name == "agent-kit.old" and dst.parent == out.resolve():
            raise OSError("restore blocked")
        return real(src, dst)

    monkeypatch.setattr(mod.os, "rename", flaky)


def test_failed_restore_keeps_staging_with_backup(tmp_path, monkeypatch):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    fail_restore(mod, monkeypatch, out)
    with pytest.raises(mod.RestoreError) as info:
        mod.build(out, sys.executable)
    staging = (tmp_path / STAGING).resolve()
    assert info.value.staging == staging
    assert str(staging) in str(info.value) and "agent-kit" in str(info.value)
    assert "nothing changed" not in str(info.value)
    assert (staging / "agent-kit.old" / ".agent-kit-build").is_file()
    assert not (out / "agent-kit").exists()


def test_builder_cli_restore_error_drops_nothing_changed(tmp_path, monkeypatch, capsys):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    fail_restore(mod, monkeypatch, out)
    code = mod.main(["--out", str(out), "--python", sys.executable])
    printed = capsys.readouterr().out
    assert code == 1
    assert str((tmp_path / STAGING).resolve()) in printed
    assert "nothing changed" not in printed


def test_rerun_moves_backup_back_before_removing_staging(tmp_path):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    before = snapshot(out / "agent-kit")
    staging = tmp_path / STAGING
    staging.mkdir()
    os.rename(out / "agent-kit", staging / "agent-kit.old")
    kit = fake_kit(tmp_path)
    version_file = kit / "vendor" / "superpowers" / "VERSION"
    version_file.write_text("version: 1.0.0\n", encoding="utf-8")
    with pytest.raises(mod.ChangedError, match="source") as info:
        mod.build(out, sys.executable, kit=kit)
    assert "previous copy of agent-kit was moved back" in str(info.value)
    assert snapshot(out / "agent-kit") == before
    assert not staging.exists()
    assert mod.main(["--out", str(out), "--python", sys.executable]) == 0


def test_restore_backups_creates_missing_out(tmp_path):
    staging = tmp_path / STAGING
    (staging / "agent-kit.old").mkdir(parents=True)
    (staging / "agent-kit.old" / ".agent-kit-build").write_text("1\n")
    out = tmp_path / "plugins"
    builder().restore_backups(out, staging)
    assert (out / "agent-kit" / ".agent-kit-build").is_file()
    assert not (staging / "agent-kit.old").exists()


def test_failed_rerun_restore_keeps_staging(tmp_path, monkeypatch):
    staging = tmp_path / STAGING
    (staging / "agent-kit.old").mkdir(parents=True)
    mod = builder()

    def blocked(src, dst):
        raise OSError("blocked")

    monkeypatch.setattr(mod.os, "rename", blocked)
    with pytest.raises(mod.RestoreError, match="blocked"):
        mod.build(tmp_path / "plugins", sys.executable)
    assert (staging / "agent-kit.old").is_dir()


def test_interrupt_mid_swap_keeps_backup(tmp_path, monkeypatch):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    real = os.rename

    def interrupted(src, dst):
        src = Path(src)
        if src.name == "agent-kit" and src.parent.name == STAGING:
            raise KeyboardInterrupt
        return real(src, dst)

    monkeypatch.setattr(mod.os, "rename", interrupted)
    with pytest.raises(KeyboardInterrupt):
        mod.build(out, sys.executable)
    staging = tmp_path / STAGING
    assert (staging / "agent-kit.old" / ".agent-kit-build").is_file()
    monkeypatch.setattr(mod.os, "rename", real)
    mod.build(out, sys.executable)
    assert (out / "agent-kit" / ".agent-kit-build").is_file()
    assert not staging.exists()


def test_stale_backup_next_to_existing_copy_is_dropped(tmp_path):
    out = tmp_path / "plugins"
    assert run_builder(out).returncode == 0
    junk = tmp_path / STAGING / "agent-kit.old"
    junk.mkdir(parents=True)
    (junk / "junk.txt").write_text("x", encoding="utf-8")
    assert run_builder(out).returncode == 0
    assert not (tmp_path / STAGING).exists()
    assert not (out / "agent-kit" / "junk.txt").exists()
