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
    assert "not empty" in result.stderr
    assert files_under(dest) == ["keep.txt"]


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
