import json
import os
import stat
import subprocess

import pytest
from helpers import PLUGIN, load_module

bench = load_module(PLUGIN / "scripts" / "jev-bench.py", "jev_bench")
triage = bench.triage


def git(repo, *args):
    config = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    out = subprocess.run(
        ["git", "-C", str(repo), *config, *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A repo with a base commit, a later 'answer' commit and a tag on it."""
    path = tmp_path / "proj"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    (path / "app.txt").write_text("v1\n", encoding="utf-8")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "base")
    base = git(path, "rev-parse", "HEAD")
    (path / "app.txt").write_text("v2 the answer\n", encoding="utf-8")
    git(path, "commit", "-q", "-am", "answer")
    answer = git(path, "rev-parse", "HEAD")
    git(path, "tag", "v2")
    return path, base, answer


@pytest.fixture
def home(monkeypatch, tmp_path):
    monkeypatch.setattr(triage, "jev_dir", lambda: tmp_path / "jev")
    monkeypatch.setattr(bench, "claude_bin", lambda: "claude")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    return tmp_path / "jev" / "bench"


def write_task(home, fixture, **overrides):
    path, base, answer = fixture
    data = {
        "id": "t01",
        "type": "feature",
        "repo": str(path),
        "base_commit": base,
        "reference": f"{base}..{answer}",
        "prompt": "change app.txt to v2",
        "brief": "The user wants app.txt to say v2.",
        "rubric": ["app.txt says v2", "nothing else changed", "no new files"],
    }
    data.update(overrides)
    tasks = home / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    (tasks / f"{data['id']}.json").write_text(json.dumps(data), encoding="utf-8")
    return data


def test_valid_task_passes_check(home, repo, capsys):
    write_task(home, repo)
    assert bench.main(["check"]) == 0
    assert "1 task(s), 0 problem(s)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "overrides,problem",
    [
        ({"type": "chore"}, "type"),
        ({"rubric": ["only one"]}, "rubric has 1"),
        ({"base_commit": "0" * 40}, "base_commit"),
        ({"reference": "not-a-range"}, "reference"),
        ({"repo": "/no/such/repo"}, "not a git repository"),
    ],
)
def test_bad_task_fails_check(home, repo, capsys, overrides, problem):
    write_task(home, repo, **overrides)
    assert bench.main(["check"]) == 1
    assert problem in capsys.readouterr().err


def test_missing_field_and_bad_json(home, repo, capsys):
    data = write_task(home, repo)
    del data["brief"]
    (home / "tasks" / "t01.json").write_text(json.dumps(data), encoding="utf-8")
    (home / "tasks" / "t02.json").write_text("{not json", encoding="utf-8")
    assert bench.main(["check"]) == 1
    err = capsys.readouterr().err
    assert "missing brief" in err
    assert "t02.json" in err


def test_check_jev_arm_needs_key(home, repo, capsys):
    write_task(home, repo)
    assert bench.main(["check", "--arm", "jev"]) == 1
    assert "TYPESAFE_API_KEY" in capsys.readouterr().err


def test_check_without_tasks(home, capsys):
    assert bench.main(["check"]) == 1
    assert "no task files" in capsys.readouterr().err


def load(fixture, home, **overrides):
    write_task(home, fixture, **overrides)
    return bench.load_task(home / "tasks" / "t01.json")


def test_sandbox_has_no_remote_and_no_future_commits(home, repo, tmp_path):
    task = load(repo, home)
    sandbox = bench.make_sandbox(task, tmp_path / "bench-root", "t01-off-1")
    assert sandbox == tmp_path / "bench-root" / "t01-off-1"
    assert git(sandbox, "rev-parse", "HEAD") == task.base_commit
    assert git(sandbox, "branch", "--show-current") == "main"
    assert git(sandbox, "remote") == ""
    answer = task.reference.split("..")[1]
    gone = subprocess.run(
        ["git", "-C", str(sandbox), "cat-file", "-e", answer], capture_output=True
    )
    assert gone.returncode != 0
    assert git(sandbox, "tag") == ""
    assert (sandbox / "app.txt").read_text(encoding="utf-8") == "v1\n"


def test_make_sandbox_replaces_a_leftover(home, repo, tmp_path):
    task = load(repo, home)
    root = tmp_path / "bench-root"
    (root / "t01-off-1").mkdir(parents=True)
    (root / "t01-off-1" / "junk.txt").write_text("x", encoding="utf-8")
    sandbox = bench.make_sandbox(task, root, "t01-off-1")
    assert not (sandbox / "junk.txt").exists()


def test_remove_tree_handles_read_only_files(tmp_path):
    target = tmp_path / "t"
    (target / "sub").mkdir(parents=True)
    locked = target / "sub" / "ro.txt"
    locked.write_text("x", encoding="utf-8")
    os.chmod(locked, stat.S_IREAD)
    bench.remove_tree(target)
    assert not target.exists()


def test_child_env_drops_secrets_and_sets_the_arm():
    base = {
        "PATH": "p",
        "GITHUB_TOKEN": "s",
        "SUPABASE_ACCESS_TOKEN": "s",
        "OPENAI_API_KEY": "s",
        "DATABASE_URL": "s",
        "ANTHROPIC_API_KEY": "keep",
        "CLAUDE_CONFIG_DIR": "keep",
        "TYPESAFE_API_KEY": "tk",
    }
    off = bench.child_env("off", base)
    assert off["PATH"] == "p"
    assert off["ANTHROPIC_API_KEY"] == "keep"
    assert off["CLAUDE_CONFIG_DIR"] == "keep"
    assert off["CLAUDE_KIT_JEV"] == "off"
    secrets = ("GITHUB_TOKEN", "SUPABASE_ACCESS_TOKEN", "OPENAI_API_KEY")
    for secret in (*secrets, "DATABASE_URL", "TYPESAFE_API_KEY"):
        assert secret not in off
    jev = bench.child_env("jev", base)
    assert jev["CLAUDE_KIT_JEV"] == "active"
    assert jev["TYPESAFE_API_KEY"] == "tk"


def test_claude_args(monkeypatch):
    monkeypatch.setattr(bench, "claude_bin", lambda: "claude")
    argv = bench.claude_args("opus", 7.5, resume="S1")
    assert argv[:2] == ["claude", "-p"]
    assert argv[argv.index("--model") + 1] == "opus"
    assert argv[argv.index("--max-budget-usd") + 1] == "7.50"
    assert argv[argv.index("--resume") + 1] == "S1"
    assert argv[argv.index("--permission-mode") + 1] == "bypassPermissions"
    assert argv[argv.index("--output-format") + 1] == "json"
    tools = argv[argv.index("--disallowedTools") + 1 :]
    assert tuple(tools) == bench.DENIED
    for needed in ("Bash(git push:*)", "Bash(gh:*)", "PowerShell(Invoke-Item:*)"):
        assert needed in tools
    quiet = bench.claude_args("haiku", 1, tools=bench.NO_TOOLS, permission="")
    assert "--permission-mode" not in quiet
    assert "Bash" in quiet and "Write" in quiet
