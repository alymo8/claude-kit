import json
import shutil
import subprocess

import pytest
from helpers import PLUGIN, REPO, clean_env, load_module, run_script

HOOK = PLUGIN / "hooks" / "workspace_rules_inject.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
GIT += ["-c", "commit.gpgsign=false"]
AGENTS = ("vibe", "codex", "cursor")
RULES_TEXT = "# Rules\n\n## How we work\n\nx\n"
AGENT_TEXT = "follow them as you would an AGENTS.md"
CLAUDE_TEXT = "as you would a CLAUDE.md"


def run(script=HOOK, stdin="{}", **env: str):
    environment = clean_env(**env)
    if "CLAUDE_PROJECT_DIR" not in env:
        environment.pop("CLAUDE_PROJECT_DIR", None)
    return run_script(script, stdin=stdin, env=environment)


def context(result) -> str:
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    return out["additionalContext"]


def make_kit(root, rules=RULES_TEXT, name="agent-kit"):
    (root / "plugin" / "hooks").mkdir(parents=True, exist_ok=True)
    (root / "plugin" / "rules.md").write_text(rules, encoding="utf-8")
    (root / ".claude-plugin").mkdir(exist_ok=True)
    marketplace = root / ".claude-plugin" / "marketplace.json"
    marketplace.write_text(json.dumps({"name": name}), encoding="utf-8")
    shutil.copy(HOOK, root / "plugin" / "hooks" / HOOK.name)
    return root


def make_copy(tmp_path):
    copy = tmp_path / "cache" / "agent-kit" / "1.0.0"
    shutil.copytree(PLUGIN, copy, ignore=shutil.ignore_patterns("__pycache__"))
    return copy / "hooks" / HOOK.name


def git_repo(path):
    subprocess.run(GIT + ["init", "-q", str(path)], check=True)
    subprocess.run(GIT + ["-C", str(path), "add", "-A"], check=True)
    subprocess.run(GIT + ["-C", str(path), "commit", "-qm", "i"], check=True)


def test_outside_any_kit_injects_rules(tmp_path):
    result = run(CLAUDE_PROJECT_DIR=str(tmp_path))
    assert result.returncode == 0, result.stderr
    text = context(result)
    assert text.startswith("Workspace rules (agent-kit, from ")
    assert f"{PLUGIN.as_posix()}/rules.md" in text
    assert "## How we work" in text
    assert "## Developing the kit" not in text


def test_copy_injects_in_unrelated_repo(tmp_path):
    hook = make_copy(tmp_path)
    copy = hook.parents[1].resolve()
    other = tmp_path / "other"
    other.mkdir()
    (other / "README.md").write_text("o\n", encoding="utf-8")
    git_repo(other)
    result = run(hook, CLAUDE_PROJECT_DIR=str(other))
    assert result.returncode == 0, result.stderr
    text = context(result)
    assert f"{copy.as_posix()}/rules.md" in text
    assert "## How we work" in text


@pytest.mark.parametrize("hook_from", ["kit", "copy"])
@pytest.mark.parametrize("agent", ["", "vibe", "codex", "cursor"])
def test_rules_table(tmp_path, agent, hook_from):
    kit = make_kit(tmp_path / "kit")
    git_repo(kit)
    worktree = tmp_path / "wt"
    subprocess.run(
        GIT + ["-C", str(kit), "worktree", "add", "-q", str(worktree)], check=True
    )
    child = kit / "child"
    child.mkdir()
    (child / "README.md").write_text("c\n", encoding="utf-8")
    git_repo(child)
    other = tmp_path / "other"
    other.mkdir()
    (other / "README.md").write_text("o\n", encoding="utf-8")
    git_repo(other)
    if hook_from == "kit":
        hook = kit / "plugin" / "hooks" / HOOK.name
    else:
        hook = make_copy(tmp_path)
    extra = {"CLAUDE_KIT_AGENT": agent} if agent else {}
    for project in (kit, kit / "plugin", child, worktree):
        result = run(hook, CLAUDE_PROJECT_DIR=str(project), **extra)
        assert result.returncode == 0, result.stderr
        if agent == "":
            assert result.stdout == "", project
        else:
            text = context(result)
            assert "## How we work" in text, project
            assert AGENT_TEXT in text, project
    result = run(hook, CLAUDE_PROJECT_DIR=str(other), **extra)
    text = context(result)
    assert "## How we work" in text
    if agent == "":
        assert CLAUDE_TEXT in text


def test_old_branch_worktree(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "README.md").write_text("old\n", encoding="utf-8")
    git_repo(kit)
    make_kit(kit)
    subprocess.run(GIT + ["-C", str(kit), "add", "-A"], check=True)
    subprocess.run(GIT + ["-C", str(kit), "commit", "-qm", "kit"], check=True)
    old = tmp_path / "old"
    subprocess.run(
        GIT + ["-C", str(kit), "worktree", "add", "-q", "--detach", str(old), "HEAD~1"],
        check=True,
    )
    assert not (old / "plugin" / "rules.md").exists()
    hook = kit / "plugin" / "hooks" / HOOK.name
    assert run(hook, CLAUDE_PROJECT_DIR=str(old)).stdout == ""
    for agent in AGENTS:
        env = {"CLAUDE_PROJECT_DIR": str(old), "CLAUDE_KIT_AGENT": agent}
        assert AGENT_TEXT in context(run(hook, **env))


@pytest.mark.parametrize("marketplace", ["{oops", "[]", '{"name": "other"}'])
def test_malformed_or_foreign_marketplace_is_not_a_kit(tmp_path, marketplace):
    folder = tmp_path / "folder"
    (folder / "plugin").mkdir(parents=True)
    (folder / "plugin" / "rules.md").write_text(RULES_TEXT, encoding="utf-8")
    (folder / ".claude-plugin").mkdir()
    (folder / ".claude-plugin" / "marketplace.json").write_text(
        marketplace, encoding="utf-8"
    )
    module = load_module(HOOK, "workspace_rules_inject")
    assert module.is_kit_checkout(folder) is False
    result = run(CLAUDE_PROJECT_DIR=str(folder / "plugin"))
    assert result.returncode == 0, result.stderr
    assert "## How we work" in context(result)


def test_kit_checkout_helpers(tmp_path):
    kit = make_kit(tmp_path / "kit")
    module = load_module(HOOK, "workspace_rules_inject")
    assert module.KIT_NAME == "agent-kit"
    assert module.is_kit_checkout(kit) is True
    assert module.find_kit(kit / "plugin" / "hooks") == kit
    assert module.find_kit(tmp_path) is None
    assert module.plugin_root() == PLUGIN.resolve()
    assert module.plugin_kit() == REPO.resolve()


def test_inside_the_real_kit_is_silent():
    for project in (REPO, REPO / "plugin"):
        result = run(CLAUDE_PROJECT_DIR=str(project))
        assert result.returncode == 0
        assert result.stdout == "", project
        for agent in AGENTS:
            env = {"CLAUDE_PROJECT_DIR": str(project), "CLAUDE_KIT_AGENT": agent}
            assert AGENT_TEXT in context(run(**env)), (agent, project)


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


def test_missing_rules_prints_nothing(tmp_path):
    hooks = tmp_path / "bare" / "plugin" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(HOOK, hooks / HOOK.name)
    other = tmp_path / "other"
    other.mkdir()
    result = run(hooks / HOOK.name, CLAUDE_PROJECT_DIR=str(other))
    assert result.returncode == 0
    assert result.stdout == ""


def test_size_cap(tmp_path):
    # Claude Code truncates hook context above 10,000 characters to a preview,
    # so keep a margin; trim plugin/rules.md if this fails.
    assert len(context(run(CLAUDE_PROJECT_DIR=str(tmp_path)))) <= 9_500


def test_registered_after_kit_map_without_matcher():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    groups = hooks["hooks"]["SessionStart"]
    commands = [g["hooks"][0]["command"] for g in groups]
    kit = next(i for i, c in enumerate(commands) if "kit_map_inject.py" in c)
    rules = groups[kit + 1]
    assert "hooks/workspace_rules_inject.py" in rules["hooks"][0]["command"]
    assert "matcher" not in rules
