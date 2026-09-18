import subprocess
import sys

import pytest
from helpers import PLUGIN

INSTALL = PLUGIN / "install.ps1"
pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="junctions are Windows-only"
)


def run_install(skills_dir):
    settings = skills_dir.parent / "settings.json"
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INSTALL),
            "-SkillsDir",
            str(skills_dir),
            "-Settings",
            str(settings),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_creates_junction_to_plugin(tmp_path):
    skills = tmp_path / "skills"
    result = run_install(skills)
    assert result.returncode == 0, result.stdout + result.stderr
    link = skills / "claude-kit"
    assert link.is_dir()
    assert (link / ".claude-plugin" / "plugin.json").exists()
    assert "Installed" in result.stdout


def test_second_run_is_idempotent(tmp_path):
    skills = tmp_path / "skills"
    assert run_install(skills).returncode == 0
    result = run_install(skills)
    assert result.returncode == 0
    assert "already installed" in result.stdout


def test_conflicting_directory_fails(tmp_path):
    skills = tmp_path / "skills"
    (skills / "claude-kit").mkdir(parents=True)  # a plain folder, not our junction
    result = run_install(skills)
    assert result.returncode == 1
    assert "already exists" in result.stdout + result.stderr


def test_dangling_junction_fails_cleanly(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    link = skills / "claude-kit"
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"New-Item -ItemType Junction -Path '{link}' -Target '{victim}' | Out-Null",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    victim.rmdir()  # the junction now dangles
    result = run_install(skills)
    assert result.returncode == 1
    assert "already exists" in result.stdout + result.stderr


def test_install_adds_statusline_to_given_settings(tmp_path):
    skills = tmp_path / "skills"
    result = run_install(skills)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "statusLine added" in result.stdout
    text = (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert "statusline.py" in text


def test_install_survives_malformed_settings(tmp_path):
    skills = tmp_path / "skills"
    skills.parent.mkdir(parents=True, exist_ok=True)
    settings = skills.parent / "settings.json"
    settings.write_text("{oops", encoding="utf-8")
    result = run_install(skills)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Installed" in result.stdout
    assert settings.read_text(encoding="utf-8") == "{oops"
    assert "WARNING: status line not configured" in result.stdout
