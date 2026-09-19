import subprocess
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "handoff.py"


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout.strip()


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


@pytest.fixture
def mod():
    return load_module(SCRIPT, "handoff")


def test_safe_name_replaces_slashes_and_odd_chars(mod):
    assert mod.safe_name("feature/foo") == "feature_foo"
    assert mod.safe_name("a b:c") == "a_b_c"
    assert mod.safe_name("v1.2-rc") == "v1.2-rc"


def test_path_is_under_dot_claude_handoffs(repo, mod):
    git("checkout", "-q", "-b", "feature/foo", cwd=repo)
    expected = repo / ".claude" / "handoffs" / "feature_foo.md"
    assert mod.handoff_path(repo).resolve() == expected.resolve()


def test_detached_head_gets_sha_name(repo, mod):
    sha = git("rev-parse", "--short=7", "HEAD", cwd=repo)
    git("checkout", "-q", "--detach", cwd=repo)
    assert mod.branch_name(repo) == f"detached-{sha}"


def test_state_lists_dirty_files_and_commits(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    state = mod.state_section(repo)
    assert state.startswith("## State\n<!-- generated; do not edit -->\n")
    assert "- branch: main" in state
    assert "- dirty: b.txt" in state
    assert "init" in state  # last commit subject
    assert "- upstream: none" in state
    assert "- PR: none" in state
    assert state.endswith("\n")


def test_state_reports_ahead_behind_when_upstream_exists(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    git("branch", "base", cwd=repo)
    git("checkout", "-q", "-b", "feat", cwd=repo)
    git("branch", "--set-upstream-to=base", cwd=repo)
    (repo / "c.txt").write_text("c\n", encoding="utf-8")
    git("add", "c.txt", cwd=repo)
    git("commit", "-q", "-m", "c", cwd=repo)
    assert "- upstream: base, ahead 1, behind 0" in mod.state_section(repo)


def test_replace_state_keeps_every_other_byte(mod):
    before = (
        "# Handoff: x\n\n- **Written:** 2026-09-18T10:00 by /handoff\n\n"
        "## Task\nBuild it.\n\n## State\n<!-- generated; do not edit -->\n"
        "- branch: old\n\n## Done this session\n- a\n"
    )
    new_state = "## State\n<!-- generated; do not edit -->\n- branch: new\n"
    after = mod.replace_state(before, new_state)
    assert after == (
        "# Handoff: x\n\n- **Written:** 2026-09-18T10:00 by /handoff\n\n"
        "## Task\nBuild it.\n\n## State\n<!-- generated; do not edit -->\n"
        "- branch: new\n\n## Done this session\n- a\n"
    )


def test_replace_state_when_state_is_last_section(mod):
    before = "# H\n\n## State\n- branch: old\n"
    assert mod.replace_state(before, "## State\n- branch: new\n") == (
        "# H\n\n## State\n- branch: new\n"
    )


def test_snapshot_creates_file_with_state_and_prompts(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    path = mod.snapshot(repo, ["first prompt", "second prompt"])
    text = path.read_text(encoding="utf-8")
    assert path.resolve() == (repo / ".claude" / "handoffs" / "main.md").resolve()
    assert text.startswith("# Handoff: main\n\n- **Written:** ")
    assert "by session-end snapshot" in text
    assert "## State\n" in text
    assert "## Recent prompts\n- first prompt\n- second prompt\n" in text
    assert b"\r\n" not in path.read_bytes()


def test_snapshot_refreshes_only_state_and_written(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    path = mod.handoff_path(repo)
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Handoff: main\n\n- **Written:** 2026-01-01T00:00 by /handoff\n"
        "- **Spec / plan:** none\n\n## Task\nKeep me.\n\n"
        "## State\n- branch: stale\n\n## Next\n1. Keep me too.\n",
        encoding="utf-8",
    )
    mod.snapshot(repo, ["ignored when file exists"])
    text = path.read_text(encoding="utf-8")
    assert "Keep me." in text and "Keep me too." in text
    assert "- branch: stale" not in text
    assert "- branch: main" in text
    assert "2026-01-01T00:00" not in text
    assert "by session-end snapshot" in text
    assert "ignored when file exists" not in text


def test_cli_path_and_state(repo):
    out = run_script(SCRIPT, "path", "--cwd", str(repo))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("main.md")
    out = run_script(SCRIPT, "state", "--cwd", str(repo))
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("## State")


def test_cli_snapshot_reads_prompts_file(repo, tmp_path):
    prompts = tmp_path / "p.txt"
    prompts.write_text("one\ntwo\n", encoding="utf-8")
    out = run_script(SCRIPT, "snapshot", "--cwd", str(repo), "--prompts", str(prompts))
    assert out.returncode == 0, out.stderr
    text = (repo / ".claude" / "handoffs" / "main.md").read_text(encoding="utf-8")
    assert "- one\n- two\n" in text


def test_snapshot_makes_handoffs_dir_self_ignoring(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    mod.snapshot(repo, [])
    ignore = repo / ".claude" / "handoffs" / ".gitignore"
    assert ignore.read_text(encoding="utf-8") == "*\n"
    assert git("status", "--porcelain", cwd=repo) == ""
    ignore.write_text("custom\n", encoding="utf-8", newline="\n")
    mod.snapshot(repo, [])
    assert ignore.read_text(encoding="utf-8") == "custom\n"


def test_cli_outside_git_exits_1_and_writes_nothing(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    for sub in ("path", "state", "snapshot"):
        out = run_script(SCRIPT, sub, "--cwd", str(plain))
        assert out.returncode == 1, sub
        assert "git" in out.stderr
    assert not (plain / ".claude").exists()
