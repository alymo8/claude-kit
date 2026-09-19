import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "handoff_inject.py"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@example.com", cwd=root)
    git("config", "user.name", "t", cwd=root)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    git("add", "a.txt", cwd=root)
    git("commit", "-q", "-m", "init", cwd=root)
    return root


def write_handoff(repo: Path, name: str, written: datetime, body: str = "") -> Path:
    path = repo / ".claude" / "handoffs" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Handoff: {name}\n\n- **Written:** {written:%Y-%m-%dT%H:%M} by /handoff\n\n"
        f"## Task\n{body or 'Do the thing.'}\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


NOW = datetime(2026, 9, 18, 12, 0)


def test_injects_fresh_handoff_for_current_branch(repo):
    write_handoff(repo, "main", NOW - timedelta(hours=3), "Resume here.")
    text = load_module(HOOK, "inject").render(repo, NOW)
    assert text.startswith('<handoff age="3h" path=".claude/handoffs/main.md">')
    assert "verify it against git" in text
    assert "Resume here." in text
    assert text.rstrip().endswith("</handoff>")


def test_skips_stale_handoff(repo):
    write_handoff(repo, "main", NOW - timedelta(days=8))
    assert load_module(HOOK, "inject").render(repo, NOW) == ""


def test_mentions_other_branch_handoffs_in_one_line(repo):
    write_handoff(repo, "feature_bar", NOW - timedelta(days=2))
    text = load_module(HOOK, "inject").render(repo, NOW)
    assert text == "[claude-kit] Handoffs exist for other branches: feature_bar (2d)"


def test_other_branch_stale_handoff_is_not_mentioned(repo):
    write_handoff(repo, "feature_old", NOW - timedelta(days=30))
    assert load_module(HOOK, "inject").render(repo, NOW) == ""


def test_age_falls_back_to_mtime_without_written_line(repo):
    path = repo / ".claude" / "handoffs" / "main.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Handoff: main\n\n## Task\nNo written line.\n",
        encoding="utf-8",
        newline="\n",
    )
    text = load_module(HOOK, "inject").render(repo, datetime.now())
    assert "No written line." in text


def test_non_git_dir_renders_nothing(tmp_path):
    assert load_module(HOOK, "inject").render(tmp_path, NOW) == ""


def test_script_exit_zero_and_prints_to_stdout(repo, tmp_path):
    write_handoff(repo, "main", datetime.now() - timedelta(minutes=5))
    event = json.dumps({"hook_event_name": "SessionStart", "cwd": str(repo)})
    result = run_script(HOOK, stdin=event, cwd=repo)
    assert result.returncode == 0, result.stderr
    assert "<handoff " in result.stdout
    assert run_script(HOOK, stdin="{bad", cwd=tmp_path).returncode == 0
