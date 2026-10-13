import json
import os
import shutil
import subprocess
import sys

import pytest
from helpers import PLUGIN

INSTALL = PLUGIN / "install.py"
WRAPPER = PLUGIN / "install.ps1"
SUPERPOWERS = "superpowers@claude-plugins-official"


def run_install(tmp_path, python=sys.executable, env=None):
    return subprocess.run(
        [
            sys.executable,
            str(INSTALL),
            "--skills-dir",
            str(tmp_path / "skills"),
            "--settings",
            str(tmp_path / "settings.json"),
            "--python",
            python,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
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


@pytest.fixture(autouse=True)
def drop_kit_link(tmp_path):
    yield
    link = tmp_path / "skills" / "claude-kit"
    if os.path.lexists(link) and is_link(link):
        remove_link(link)


def test_creates_link_to_plugin(tmp_path):
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    link = tmp_path / "skills" / "claude-kit"
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
    folder = tmp_path / "skills" / "claude-kit"
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("x", encoding="utf-8")
    result = run_install(tmp_path)
    assert result.returncode == 1
    assert "already exists" in out(result)
    assert (folder / "keep.txt").read_text(encoding="utf-8") == "x"


def test_dangling_link_fails_cleanly(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    link = skills / "claude-kit"
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
    assert not os.path.lexists(tmp_path / "skills" / "claude-kit")
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
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, out(result)
    assert os.path.samefile(tmp_path / "skills" / "claude-kit", PLUGIN)
