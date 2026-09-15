import subprocess
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "worktree_audit.py"


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


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


def report(cwd: Path) -> str:
    return load_module(HOOK, "worktree_audit").report(cwd)


def test_clean_repo_reports_nothing(repo):
    assert report(repo) == ""


def test_non_git_dir_reports_nothing(tmp_path):
    assert report(tmp_path) == ""


def test_leftover_worktree_is_listed(repo, tmp_path):
    wt = tmp_path / "wt-feature"
    git("worktree", "add", "-q", "-b", "feat/x", str(wt), cwd=repo)
    text = report(repo)
    assert "worktrees:" in text
    assert "feat/x" in text
    assert "wt-feature" in text


def test_merged_branch_is_listed_as_merged(repo):
    git("branch", "done-branch", cwd=repo)  # points at main => merged
    text = report(repo)
    assert "done-branch (merged)" in text


def test_current_branch_is_never_listed(repo):
    git("checkout", "-q", "-b", "wip", cwd=repo)
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    git("add", "b.txt", cwd=repo)
    git("commit", "-q", "-m", "wip", cwd=repo)
    assert "wip" not in report(repo)


def test_unmerged_branch_with_upstream_is_not_listed(repo):
    git("checkout", "-q", "-b", "tracked", cwd=repo)
    (repo / "c.txt").write_text("c\n", encoding="utf-8")
    git("add", "c.txt", cwd=repo)
    git("commit", "-q", "-m", "c", cwd=repo)
    git("checkout", "-q", "main", cwd=repo)
    git("branch", "--set-upstream-to=main", "tracked", cwd=repo)
    assert report(repo) == ""


def test_script_exit_code_is_zero_everywhere(repo, tmp_path):
    assert run_script(HOOK, cwd=repo).returncode == 0
    assert run_script(HOOK, cwd=tmp_path).returncode == 0


def test_script_prints_report_to_stdout(repo):
    git("branch", "old", cwd=repo)
    result = run_script(HOOK, cwd=repo)
    assert result.stdout.startswith("[claude-kit] Leftover")
    assert "old (merged)" in result.stdout
