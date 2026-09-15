import subprocess
from pathlib import Path

import pytest
from helpers import PLUGIN, broken_links, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "scaffold.py"
EXPECTED = [
    "CLAUDE.md",
    "README.md",
    ".gitignore",
    ".github/workflows/ci.yml",
    ".github/workflows/claude-review.yml",
    ".github/workflows/secret-scan.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "knowledge/README.md",
    "knowledge/decisions/README.md",
    "knowledge/decisions/0000-template.md",
    "knowledge/archive/.gitkeep",
    "docs/superpowers/README.md",
    "docs/superpowers/specs/.gitkeep",
    "docs/superpowers/plans/.gitkeep",
]


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout.strip()


def files_under(root: Path) -> list[str]:
    """Project-relative POSIX paths of every file, excluding the .git directory."""
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.relative_to(root).parts[0] != ".git"
    )


@pytest.mark.parametrize("stack,marker", [("node", "pnpm"), ("python", "uv ")])
def test_new_project_has_every_file_and_one_commit(tmp_path, stack, marker):
    result = run_script(
        SCRIPT, "--name", "demo", "--stack", stack, "--parent", str(tmp_path)
    )
    assert result.returncode == 0, result.stderr
    dest = tmp_path / "demo"
    assert files_under(dest) == sorted(EXPECTED)
    assert git("branch", "--show-current", cwd=dest) == "main"
    assert git("rev-list", "--count", "HEAD", cwd=dest) == "1"
    assert git("status", "--porcelain", cwd=dest) == ""
    assert marker in (dest / ".github/workflows/ci.yml").read_text("utf-8")
    assert marker in (dest / "CLAUDE.md").read_text("utf-8")
    assert "demo" in (dest / "README.md").read_text("utf-8")
    assert f"created: {len(EXPECTED)} files" in result.stdout


def test_no_placeholders_remain_and_links_resolve(tmp_path):
    run_script(SCRIPT, "--name", "demo", "--stack", "python", "--parent", str(tmp_path))
    dest = tmp_path / "demo"
    mod = load_module(SCRIPT, "scaffold")
    for rel in files_under(dest):
        text = (dest / rel).read_text("utf-8")
        assert not mod.PLACEHOLDER_RE.search(text), rel
    assert not broken_links(dest.rglob("*.md"))


def test_refuses_non_empty_destination(tmp_path):
    dest = tmp_path / "demo"
    dest.mkdir()
    (dest / "keep.txt").write_text("x", encoding="utf-8")
    result = run_script(
        SCRIPT, "--name", "demo", "--stack", "node", "--parent", str(tmp_path)
    )
    assert result.returncode == 1
    assert "already exists" in result.stderr
    assert files_under(dest) == ["keep.txt"]


def test_refuses_destination_that_is_a_file(tmp_path):
    (tmp_path / "demo").write_text("x", encoding="utf-8")
    result = run_script(
        SCRIPT, "--name", "demo", "--stack", "node", "--parent", str(tmp_path)
    )
    assert result.returncode == 1
    assert "already exists" in result.stderr
    assert (tmp_path / "demo").read_text("utf-8") == "x"


def test_git_failure_removes_freshly_created_directory(tmp_path, monkeypatch):
    mod = load_module(SCRIPT, "scaffold_gitfail")

    def failing_git(*args, cwd):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="boom")

    monkeypatch.setattr(mod, "git", failing_git)
    with pytest.raises(SystemExit):
        mod.scaffold_new("demo", "python", tmp_path)
    assert not (tmp_path / "demo").exists()


def test_unknown_stack_is_a_usage_error(tmp_path):
    result = run_script(
        SCRIPT, "--name", "demo", "--stack", "rust", "--parent", str(tmp_path)
    )
    assert result.returncode == 2


def test_render_files_rejects_unresolved_placeholder(tmp_path, monkeypatch):
    mod = load_module(SCRIPT, "scaffold_bad")
    bad_root = tmp_path / "templates"
    (bad_root / "project").mkdir(parents=True)
    (bad_root / "stacks" / "node").mkdir(parents=True)
    for name in ("ci.yml", "commands.part", "gitignore.part"):
        (bad_root / "stacks" / "node" / name).write_text("x\n", encoding="utf-8")
    (bad_root / "project" / "README.md").write_text("{{nope}}\n", encoding="utf-8")
    monkeypatch.setattr(mod, "TEMPLATES", bad_root)
    with pytest.raises(ValueError, match="nope"):
        mod.render_files("demo", "node", "2026-01-01")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "existing"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@example.com", cwd=root)
    git("config", "user.name", "t", cwd=root)
    (root / "CLAUDE.md").write_text("# mine\n", encoding="utf-8")
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    specs = root / "docs" / "superpowers" / "specs"
    specs.mkdir(parents=True)
    (specs / "2026-01-01-x-design.md").write_text("# X\n", encoding="utf-8")
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "init", cwd=root)
    return root


def test_adopt_creates_only_missing_files_and_never_commits(repo):
    result = run_script(SCRIPT, "--adopt", "--stack", "node", "--dest", str(repo))
    assert result.returncode == 0, result.stderr
    assert (repo / "CLAUDE.md").read_text("utf-8") == "# mine\n"
    assert (repo / ".gitignore").read_text("utf-8") == "node_modules/\n"
    assert (repo / ".github/workflows/ci.yml").exists()
    assert (repo / "knowledge/decisions/0000-template.md").exists()
    assert not (repo / "docs/superpowers/specs/.gitkeep").exists()
    assert (repo / "docs/superpowers/plans/.gitkeep").exists()
    assert git("rev-list", "--count", "HEAD", cwd=repo) == "1"
    assert "skipped (already present):" in result.stdout
    assert "CLAUDE.md" in result.stdout.split("skipped (already present):")[1]
    assert "docs/superpowers/**/*.html" in result.stdout
    assert "existing" in (repo / "README.md").read_text("utf-8")
    index = (repo / "docs/superpowers/README.md").read_text("utf-8")
    assert "[X](specs/2026-01-01-x-design.md)" in index, "index regenerated on adopt"


def test_adopt_outside_git_is_refused(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    result = run_script(SCRIPT, "--adopt", "--stack", "python", "--dest", str(plain))
    assert result.returncode == 1
    assert "git" in result.stderr
    assert files_under(plain) == []


def test_adopt_defaults_to_cwd(repo):
    result = run_script(SCRIPT, "--adopt", "--stack", "python", cwd=repo)
    assert result.returncode == 0, result.stderr
    assert (repo / ".github/workflows/secret-scan.yml").exists()


def test_adopt_keeps_a_hand_written_index(repo):
    index = repo / "docs" / "superpowers" / "README.md"
    index.write_text("# My own index\n", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "-q", "-m", "index", cwd=repo)
    result = run_script(SCRIPT, "--adopt", "--stack", "python", "--dest", str(repo))
    assert result.returncode == 0, result.stderr
    assert index.read_text("utf-8") == "# My own index\n"
    assert (
        git("status", "--porcelain", "--", "docs/superpowers/README.md", cwd=repo) == ""
    )
    assert "left as-is" in result.stdout


def test_scaffolded_files_use_lf_newlines(tmp_path):
    run_script(SCRIPT, "--name", "demo", "--stack", "node", "--parent", str(tmp_path))
    assert b"\r\n" not in (tmp_path / "demo" / "CLAUDE.md").read_bytes()


def test_adopted_files_use_lf_newlines(repo):
    run_script(SCRIPT, "--adopt", "--stack", "python", "--dest", str(repo))
    assert b"\r\n" not in (repo / ".github" / "workflows" / "ci.yml").read_bytes()


def test_git_binary_missing_removes_freshly_created_directory(tmp_path, monkeypatch):
    mod = load_module(SCRIPT, "scaffold_nogit")

    def missing_git(*args, cwd):
        raise FileNotFoundError("git")

    monkeypatch.setattr(mod, "git", missing_git)
    with pytest.raises(SystemExit):
        mod.scaffold_new("demo", "python", tmp_path)
    assert not (tmp_path / "demo").exists()
