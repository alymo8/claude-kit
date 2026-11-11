"""Tests for plugin/scripts/vault-init.py."""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

import pytest
from helpers import PLUGIN, clean_env, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "vault-init.py"
TREE = sorted(
    [
        "CLAUDE.md",
        "README.md",
        "vault.toml",
        ".gitignore",
        ".gitattributes",
        "raw/web/.gitkeep",
        "raw/transcripts/.gitkeep",
        "raw/docs/.gitkeep",
        "raw/notes/.gitkeep",
        "wiki/index.md",
        "wiki/people/.gitkeep",
        "wiki/topics/.gitkeep",
        "wiki/sources/.gitkeep",
        "wiki/_templates/person.md",
        "wiki/_templates/topic.md",
        "wiki/_templates/source.md",
        "wiki/_templates/call.md",
        "wiki/_templates/task.md",
        "tasks/.gitkeep",
        ".obsidian/app.json",
        ".obsidian/templates.json",
    ]
)
FRONTMATTER = {
    "person": ["type", "role", "organization", "aliases", "topics", "last_interaction"],
    "topic": ["type", "kind", "status", "aliases", "people"],
    "source": ["type", "source_kind", "raw", "sha256", "date", "people", "topics"],
    "call": ["type", "source_kind", "raw", "sha256", "date", "people", "topics"],
    "task": ["type", "status", "owner", "topic", "source", "due"],
}
SECTIONS = {
    "person": ["Context", "Open items", "Interaction log"],
    "topic": [
        "Summary",
        "Current state",
        "Decisions",
        "Open questions",
        "Related sources",
    ],
    "source": ["Summary", "Key facts"],
    "call": ["Summary", "Key facts", "Decisions", "Action items"],
    "task": ["Description", "Acceptance criteria", "Notes"],
}


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def files(root: Path) -> list[str]:
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.relative_to(root).parts[0] != ".git"
    )


def init(dest: Path, *args: str, env=None):
    return run_script(SCRIPT, str(dest), *args, env=env)


@pytest.mark.parametrize(("profile", "ignored"), [("personal", []), ("work", ["raw/"])])
def test_profile_renders_tree_toml_gitignore_and_commit(tmp_path, profile, ignored):
    dest = tmp_path / "vault"
    result = init(dest, "--profile", profile)
    assert result.returncode == 0, result.stderr
    assert files(dest) == TREE
    toml = tomllib.loads((dest / "vault.toml").read_text("utf-8"))
    assert toml == {
        "profile": profile,
        "registries": ["people", "topics", "sources"],
        "git_ignore": ignored,
    }
    lines = (dest / ".gitignore").read_text("utf-8").splitlines()
    assert lines == [*ignored, ".obsidian/workspace*.json"]
    assert git("branch", "--show-current", cwd=dest) == "main"
    assert git("rev-list", "--count", "HEAD", cwd=dest) == "1"
    assert git("log", "-1", "--format=%s", cwd=dest) == (
        "Scaffold vault from claude-kit"
    )
    assert git("status", "--porcelain", cwd=dest) == ""
    tracked = sorted(git("ls-files", cwd=dest).splitlines())
    if profile == "work":
        assert tracked == [p for p in TREE if not p.startswith("raw/")]
    else:
        assert tracked == TREE
    assert "CLAUDE_KIT_VAULT" in result.stdout
    assert "gh repo create --private" in result.stdout
    assert git("remote", cwd=dest) == ""


def test_default_profile_is_personal(tmp_path):
    assert init(tmp_path / "v").returncode == 0
    toml = tomllib.loads((tmp_path / "v" / "vault.toml").read_text("utf-8"))
    assert toml["profile"] == "personal"


def test_empty_existing_dir_is_accepted(tmp_path):
    assert init(tmp_path).returncode == 0
    assert (tmp_path / "vault.toml").is_file()


def test_non_empty_destination_refused_and_untouched(tmp_path):
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    result = init(tmp_path)
    assert result.returncode == 1
    assert result.stderr
    assert [p.name for p in tmp_path.iterdir()] == ["keep.txt"]


def test_existing_file_refused(tmp_path):
    target = tmp_path / "file"
    target.write_text("x", encoding="utf-8")
    assert init(target).returncode == 1
    assert target.read_text("utf-8") == "x"


def test_bad_profile_is_usage_error(tmp_path):
    result = init(tmp_path / "v", "--profile", "team")
    assert result.returncode == 2
    assert not (tmp_path / "v").exists()


def test_no_placeholder_remains(tmp_path):
    init(tmp_path / "v")
    for rel in files(tmp_path / "v"):
        assert "{{" not in (tmp_path / "v" / rel).read_text("utf-8"), rel


def test_commit_falls_back_to_kit_identity(tmp_path):
    empty = tmp_path / "empty.gitconfig"
    empty.write_text("", encoding="utf-8")
    # HOME and XDG_CONFIG_HOME isolate git older than 2.32 (no GIT_CONFIG_GLOBAL).
    env = clean_env(
        GIT_CONFIG_GLOBAL=str(empty),
        GIT_CONFIG_NOSYSTEM="1",
        HOME=str(tmp_path),
        XDG_CONFIG_HOME=str(tmp_path),
    )
    for key in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "EMAIL",
    ):
        env.pop(key, None)
    result = init(tmp_path / "v", env=env)
    assert result.returncode == 0, result.stderr
    author = git("log", "-1", "--format=%an <%ae>", cwd=tmp_path / "v")
    assert author == "claude-kit <claude-kit@localhost>"


def failing_git(*args, cwd):
    if args[0] == "commit":
        return subprocess.CompletedProcess(["git", *args], 1, "", "no identity")
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def missing_git(*args, cwd):
    raise FileNotFoundError("git")


@pytest.mark.parametrize("fake", [failing_git, missing_git])
@pytest.mark.parametrize("pre_existing", [False, True])
def test_git_failure_removes_what_was_written(
    tmp_path, monkeypatch, capsys, fake, pre_existing
):
    mod = load_module(SCRIPT, "vault_init")
    monkeypatch.setattr(mod, "git", fake)
    dest = tmp_path / "v"
    if pre_existing:
        dest.mkdir()
    assert mod.main([str(dest)]) == 1
    assert capsys.readouterr().err.startswith("error:")
    if pre_existing:
        assert list(dest.iterdir()) == []
    else:
        assert not dest.exists()


def _fail_copy(*args, **kwargs):
    raise OSError("copy failed")


@pytest.mark.parametrize("pre_existing", [False, True])
@pytest.mark.parametrize("stage", ["copytree", "write_text"])
def test_copy_or_write_failure_rolls_back(
    tmp_path, monkeypatch, capsys, stage, pre_existing
):
    mod = load_module(SCRIPT, "vault_init")
    if stage == "copytree":
        monkeypatch.setattr(mod.shutil, "copytree", _fail_copy)
    else:
        monkeypatch.setattr(Path, "write_text", _fail_copy)
    dest = tmp_path / "v"
    if pre_existing:
        dest.mkdir()
    assert mod.main([str(dest)]) == 1
    assert capsys.readouterr().err.startswith("error:")
    if pre_existing:
        assert list(dest.iterdir()) == []
    else:
        assert not dest.exists()


def test_obsidian_settings(tmp_path):
    init(tmp_path / "v")
    obsidian = tmp_path / "v" / ".obsidian"
    app = json.loads((obsidian / "app.json").read_text("utf-8"))
    assert app["useMarkdownLinks"] is False
    assert app["newLinkFormat"] == "shortest"
    templates = json.loads((obsidian / "templates.json").read_text("utf-8"))
    assert templates["folder"] == "wiki/_templates"


@pytest.mark.parametrize("name", sorted(FRONTMATTER))
def test_page_templates_match_spec(name):
    path = PLUGIN / "templates" / "vault" / "wiki" / "_templates" / f"{name}.md"
    body = path.read_text("utf-8")
    assert body.startswith("---\n")
    front = body.split("---", 2)[1].strip().splitlines()
    assert [line.split(":", 1)[0] for line in front] == FRONTMATTER[name]
    assert f"type: {'source' if name == 'call' else name}" in front
    for section in SECTIONS[name]:
        assert f"\n## {section}\n" in body + "\n", section
    if name == "call":
        assert "source_kind: call" in front
    if name == "task":
        assert "status: inbox" in front


def test_vault_rules_and_index():
    vault = PLUGIN / "templates" / "vault"
    rules = " ".join((vault / "CLAUDE.md").read_text("utf-8").split())
    for needle in ("wiki/index.md", "raw/", "claude-kit:ingest", "Open questions"):
        assert needle in rules, needle
    assert "never invent" in rules.lower()
    index = (vault / "wiki" / "index.md").read_text("utf-8")
    for section in ("People", "Topics", "Sources", "Tasks"):
        assert f"## {section}" in index
