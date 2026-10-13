import json
import shutil
import subprocess

from helpers import PLUGIN, REPO, clean_env, run_script

HOOK = PLUGIN / "hooks" / "workspace_rules_inject.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
GIT += ["-c", "commit.gpgsign=false"]


def run(script=HOOK, stdin="{}", **env: str):
    environment = clean_env(**env)
    if "CLAUDE_PROJECT_DIR" not in env:
        environment.pop("CLAUDE_PROJECT_DIR", None)
    return run_script(script, stdin=stdin, env=environment)


def context(result) -> str:
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    return out["additionalContext"]


def make_kit(tmp_path, claude_md):
    kit = tmp_path / "kit"
    (kit / "plugin" / "hooks").mkdir(parents=True)
    shutil.copy(HOOK, kit / "plugin" / "hooks" / HOOK.name)
    if claude_md is not None:
        (kit / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    return kit


def test_outside_the_kit_injects_rules_without_kit_dev(tmp_path):
    result = run(CLAUDE_PROJECT_DIR=str(tmp_path))
    assert result.returncode == 0, result.stderr
    text = context(result)
    assert text.startswith("Workspace rules (claude-kit, from ")
    assert f"{REPO.as_posix()}/CLAUDE.md" in text
    assert "## How we work" in text
    assert "## Developing the kit" not in text


def test_inside_the_kit_is_silent():
    for project in (REPO, REPO / "plugin"):
        result = run(CLAUDE_PROJECT_DIR=str(project))
        assert result.returncode == 0
        assert result.stdout == "", project


def test_kit_worktree_elsewhere_is_silent(tmp_path):
    kit = make_kit(tmp_path, "# Rules\n\n## How we work\n\nx\n")
    subprocess.run(GIT + ["init", "-q", str(kit)], check=True)
    subprocess.run(GIT + ["-C", str(kit), "add", "-A"], check=True)
    subprocess.run(GIT + ["-C", str(kit), "commit", "-qm", "init"], check=True)
    worktree = tmp_path / "wt"
    subprocess.run(
        GIT + ["-C", str(kit), "worktree", "add", "-q", str(worktree)], check=True
    )
    hook = kit / "plugin" / "hooks" / HOOK.name
    assert run(hook, CLAUDE_PROJECT_DIR=str(worktree)).stdout == ""
    other = tmp_path / "other"
    other.mkdir()
    assert "## How we work" in context(run(hook, CLAUDE_PROJECT_DIR=str(other)))


def test_project_dir_from_stdin(tmp_path):
    stdin = json.dumps({"cwd": str(tmp_path)})
    assert "## How we work" in context(run(stdin=stdin))
    stdin = json.dumps({"cwd": str(REPO)})
    assert run(stdin=stdin).stdout == ""


def test_malformed_stdin_is_ignored():
    # Falls back to the current directory: the test process runs in the kit.
    result = run(stdin="not json")
    assert result.returncode == 0
    assert result.stderr == ""


def test_zero_turns_it_off(tmp_path):
    result = run(CLAUDE_KIT_WORKSPACE_RULES="0", CLAUDE_PROJECT_DIR=str(tmp_path))
    assert result.returncode == 0
    assert result.stdout == ""


def test_missing_claude_md_prints_nothing(tmp_path):
    kit = make_kit(tmp_path, None)
    other = tmp_path / "other"
    other.mkdir()
    result = run(kit / "plugin" / "hooks" / HOOK.name, CLAUDE_PROJECT_DIR=str(other))
    assert result.returncode == 0
    assert result.stdout == ""


def test_whole_file_when_no_kit_dev_section(tmp_path):
    kit = make_kit(tmp_path, "# Rules\n\n## Only\n\nkeep me\n")
    other = tmp_path / "other"
    other.mkdir()
    hook = kit / "plugin" / "hooks" / HOOK.name
    assert "keep me" in context(run(hook, CLAUDE_PROJECT_DIR=str(other)))


def test_size_cap(tmp_path):
    assert len(context(run(CLAUDE_PROJECT_DIR=str(tmp_path)))) <= 12_000


def test_registered_after_kit_map_without_matcher():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    groups = hooks["hooks"]["SessionStart"]
    commands = [g["hooks"][0]["command"] for g in groups]
    kit = next(i for i, c in enumerate(commands) if "kit_map_inject.py" in c)
    rules = groups[kit + 1]
    assert "hooks/workspace_rules_inject.py" in rules["hooks"][0]["command"]
    assert "matcher" not in rules
