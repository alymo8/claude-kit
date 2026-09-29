import csv
import json
import os
import random
import stat
import subprocess
import sys
import time
from pathlib import Path

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
        "ADO_PAT": "s",
        "POSTGRES_URL": "s",
        "SENTRY_DSN": "s",
        "MONGODB_URI": "s",
        "ANTHROPIC_API_KEY": "keep",
        "CLAUDE_CONFIG_DIR": "keep",
        "TYPESAFE_API_KEY": "tk",
    }
    off = bench.child_env("off", base)
    assert off["PATH"] == "p"
    assert off["ANTHROPIC_API_KEY"] == "keep"
    assert off["CLAUDE_CONFIG_DIR"] == "keep"
    assert off["CLAUDE_KIT_JEV"] == "off"
    secrets = ("GITHUB_TOKEN", "SUPABASE_ACCESS_TOKEN", "OPENAI_API_KEY", "ADO_PAT")
    others = ("DATABASE_URL", "POSTGRES_URL", "SENTRY_DSN", "MONGODB_URI")
    for secret in (*secrets, *others, "TYPESAFE_API_KEY"):
        assert secret not in off
    jev = bench.child_env("jev", base)
    assert jev["CLAUDE_KIT_JEV"] == "active"
    assert jev["TYPESAFE_API_KEY"] == "tk"


def test_child_env_blocks_git_credentials_and_pushes(tmp_path):
    env = bench.child_env("off")
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GCM_INTERACTIVE"] == "Never"
    assert "GH_CONFIG_DIR" in env and "NPM_CONFIG_USERCONFIG" in env
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    def config(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), "config", *args],
            capture_output=True,
            text=True,
            env=env,
        ).stdout.split("\n")

    # the last credential.helper wins, and an empty one resets the list
    assert config("--get", "credential.helper")[0] == ""
    rewrites = config("--get-all", "url.https://invalid.invalid/.pushinsteadof")
    assert "https://" in rewrites and "git@" in rewrites
    # a remote re-added by the run cannot be pushed to
    remote = ["git", "-C", str(tmp_path), "remote"]
    subprocess.run([*remote, "add", "origin", "https://example.com/x/y.git"], env=env)
    push = subprocess.run(
        [*remote, "get-url", "--push", "origin"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert push.stdout.startswith("https://invalid.invalid/")


def test_claude_args(monkeypatch):
    monkeypatch.setattr(bench, "claude_bin", lambda: "claude")
    argv = bench.claude_args("opus", 7.5, resume="S1")
    assert argv[:2] == ["claude", "-p"]
    assert argv[argv.index("--model") + 1] == "opus"
    assert argv[argv.index("--max-budget-usd") + 1] == "7.50"
    assert argv[argv.index("--resume") + 1] == "S1"
    assert argv[argv.index("--permission-mode") + 1] == "bypassPermissions"
    assert argv[argv.index("--output-format") + 1] == "json"
    assert "--strict-mcp-config" in argv
    assert "--append-system-prompt" not in argv
    tools = argv[argv.index("--disallowedTools") + 1 :]
    assert tuple(tools) == bench.DENIED
    needed = ("Bash(git push:*)", "Bash(gh:*)", "PowerShell(Invoke-Item:*)")
    for rule in (*needed, "Bash(pwsh:*)", "PowerShell(cmd:*)", "Bash(npx vercel:*)"):
        assert rule in tools
    guarded = bench.claude_args("opus", 1, system=bench.GUARD)
    assert guarded[guarded.index("--append-system-prompt") + 1] == bench.GUARD
    quiet = bench.claude_args("haiku", 1, tools=bench.NO_TOOLS, permission="")
    assert "--permission-mode" not in quiet
    assert "--strict-mcp-config" in quiet
    assert "Bash" in quiet and "Write" in quiet


def ok(argv, payload):
    return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")


def reply(session="S1", cost=1.5, text="Done. Anything else?", turns=3, **extra):
    """claude -p JSON; cost and turns are cumulative for the session, as on
    a real --resume."""
    payload = {"session_id": session, "total_cost_usd": cost, "num_turns": turns}
    return {**payload, "duration_ms": 1000, "result": text, **extra}


def write_new_file(cwd):
    (cwd / "new.txt").write_text("made by the run\n", encoding="utf-8")


class FakeClaude:
    """Main task calls pop `main`; simulated-user (haiku) calls pop `sim`."""

    def __init__(self, main, sim=(), action=write_new_file):
        self.main = list(main)
        self.sim = list(sim)
        self.action = action
        self.calls = []
        self.timeouts = []

    def __call__(self, argv, cwd, env, stdin, timeout=None):
        self.calls.append((argv, Path(cwd), env, stdin))
        self.timeouts.append((argv[argv.index("--model") + 1], timeout))
        if "haiku" in argv:
            payload = {"session_id": "sim", "total_cost_usd": 0.01}
            return ok(argv, {**payload, "result": self.sim.pop(0)})
        item = self.main.pop(0)
        if item == "crash":
            return subprocess.CompletedProcess(argv, 1, "", "boom")
        if item == "timeout":
            raise subprocess.TimeoutExpired(argv, 1)
        if item == "oserror":
            raise OSError("disk on fire")
        if self.action:
            self.action(Path(cwd))
            self.action = None
        return ok(argv, item)


def main_calls(fake):
    return [c for c in fake.calls if "haiku" not in c[0]]


def test_run_stops_when_user_says_done(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    main = [reply(text="Use X or Y?"), reply(cost=2.0, turns=6)]
    fake = FakeClaude(main, ["Use X please", "DONE"])
    monkeypatch.setattr(bench, "RUNNER", fake)
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert record["status"] == "done"
    assert record["replies"] == 1
    assert record["cost_usd"] == pytest.approx(2.0)  # cumulative, not 1.5 + 2.0
    assert record["sim_cost_usd"] == pytest.approx(0.02)
    assert record["turns"] == 6
    assert isinstance(record["duration_ms"], int)
    assert record["session_ids"] == ["S1"]
    assert "new.txt" in record["diff"]
    first, second = main_calls(fake)
    assert first[3] == task.prompt
    assert second[3] == "Use X please"
    assert second[0][second[0].index("--resume") + 1] == "S1"
    for argv, cwd, env, _ in main_calls(fake):
        assert tuple(argv[argv.index("--disallowedTools") + 1 :]) == bench.DENIED
        assert argv[argv.index("--model") + 1] == "opus"
        assert argv[argv.index("--append-system-prompt") + 1] == bench.GUARD
        assert env["CLAUDE_KIT_JEV"] == "off"
        assert cwd == tmp_path / "root" / "t01-off-1"
    assert ("haiku", bench.SIDE_TIMEOUT_S) in fake.timeouts
    assert not (tmp_path / "root" / "t01-off-1").exists()


def test_resumed_costs_count_once_per_session(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    main = [reply("S1", 1.0), reply("S1", 1.5), reply("S2", 0.5)]
    fake = FakeClaude(main, ["go on please", "and more please", "DONE"])
    monkeypatch.setattr(bench, "RUNNER", fake)
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert record["cost_usd"] == pytest.approx(2.0)
    assert record["session_ids"] == ["S1", "S2"]


def build_in_worktree(cwd):
    git(cwd, "worktree", "add", "-q", ".claude/worktrees/feat", "-b", "feat")
    tree = cwd / ".claude" / "worktrees" / "feat"
    (tree / "feature.txt").write_text("the feature\n", encoding="utf-8")
    git(tree, "add", ".")
    git(tree, "commit", "-q", "-m", "add feature")
    (tree / "wip.txt").write_text("uncommitted\n", encoding="utf-8")
    handoffs = cwd / ".claude" / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)
    (handoffs / "main.md").write_text("kit hook noise\n", encoding="utf-8")


def test_run_captures_work_in_a_worktree(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    fake = FakeClaude([reply()], ["DONE"], action=build_in_worktree)
    monkeypatch.setattr(bench, "RUNNER", fake)
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert "feature.txt" in record["diff"]
    assert "wip.txt" in record["diff"]
    assert "add feature" in record["log"]
    assert "Subproject commit" not in record["diff"]
    assert "kit hook noise" not in record["diff"]
    assert not (tmp_path / "root" / "t01-off-1").exists()


def test_run_max_replies(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    fake = FakeClaude([reply(cost=0.1)] * 3, ["keep going please"] * 3)
    monkeypatch.setattr(bench, "RUNNER", fake)
    record = bench.run_one(task, "off", 1, tmp_path / "root", max_replies=2)
    assert record["status"] == "max_replies"
    assert record["replies"] == 2


def test_run_budget(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    fake = FakeClaude([reply(cost=2.0), reply(cost=4.0)], ["more please now"] * 2)
    monkeypatch.setattr(bench, "RUNNER", fake)
    record = bench.run_one(task, "off", 1, tmp_path / "root", budget=3.0)
    assert record["status"] == "budget"
    # --max-budget-usd applies to the session's cumulative cost
    second = main_calls(fake)[1][0]
    assert second[second.index("--max-budget-usd") + 1] == "3.00"


def test_run_budget_reported_by_claude(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    over = reply(is_error=True, subtype="error_max_budget_usd")
    monkeypatch.setattr(bench, "RUNNER", FakeClaude([over]))
    assert bench.run_one(task, "off", 1, tmp_path / "root")["status"] == "budget"


def test_run_crash_is_an_error(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    monkeypatch.setattr(bench, "RUNNER", FakeClaude(["crash"]))
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert record["status"] == "error"
    assert "exited 1" in record["error"]
    assert record["uncounted_usd"] == pytest.approx(10.0)
    assert not (tmp_path / "root" / "t01-off-1").exists()


def test_run_timeout_is_an_error(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    monkeypatch.setattr(bench, "RUNNER", FakeClaude(["timeout"]))
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert record["status"] == "error"
    assert "timed out" in record["error"]
    assert record["uncounted_usd"] == pytest.approx(10.0)
    assert not (tmp_path / "root" / "t01-off-1").exists()


def test_run_harness_exception_is_recorded(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    monkeypatch.setattr(bench, "RUNNER", FakeClaude(["oserror"]))
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert record["status"] == "error"
    assert record["error"].startswith("harness error")
    assert not (tmp_path / "root" / "t01-off-1").exists()


def test_run_survives_a_locked_sandbox(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    monkeypatch.setattr(bench, "RUNNER", FakeClaude([reply()], ["DONE"]))
    real_remove = bench.remove_tree
    calls = []

    def locked(path):
        calls.append(path)
        if len(calls) > 1:  # the first call clears leftovers in make_sandbox
            raise PermissionError(13, "in use")
        real_remove(path)

    monkeypatch.setattr(bench, "remove_tree", locked)
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert record["status"] == "done"
    assert "sandbox not removed" in record["cleanup_error"]
    real_remove(tmp_path / "root")


def test_default_runner_kills_the_process_tree_on_timeout(tmp_path):
    child = "import subprocess, sys, time; "
    child += "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
    child += "time.sleep(60)"
    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        bench.default_runner(
            [sys.executable, "-c", child], tmp_path, dict(os.environ), "", timeout=2
        )
    assert time.monotonic() - start < 30


def test_default_runner_returns_output(tmp_path):
    code = "import sys; print(sys.stdin.read().upper())"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # claude speaks UTF-8
    done = bench.default_runner(
        [sys.executable, "-c", code], tmp_path, env, "héllo", timeout=30
    )
    assert done.returncode == 0
    assert done.stdout.strip() == "HÉLLO"


def test_run_jev_arm_env(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    monkeypatch.setenv("TYPESAFE_API_KEY", "tk")
    fake = FakeClaude([reply()], ["DONE"])
    monkeypatch.setattr(bench, "RUNNER", fake)
    bench.run_one(task, "jev", 1, tmp_path / "root")
    env = main_calls(fake)[0][2]
    assert env["CLAUDE_KIT_JEV"] == "active"
    assert env["TYPESAFE_API_KEY"] == "tk"
    sim_env = [c for c in fake.calls if "haiku" in c[0]][0][2]
    assert sim_env["CLAUDE_KIT_JEV"] == "off"
    assert "TYPESAFE_API_KEY" not in sim_env


@pytest.mark.parametrize("command,expected", [("exit 0", True), ("exit 3", False)])
def test_run_records_verify(home, repo, tmp_path, monkeypatch, command, expected):
    task = load(repo, home, verify=command)
    monkeypatch.setattr(bench, "RUNNER", FakeClaude([reply()], ["DONE"]))
    assert bench.run_one(task, "off", 1, tmp_path / "root")["verify"] is expected


def test_run_keep_leaves_the_sandbox(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    monkeypatch.setattr(bench, "RUNNER", FakeClaude([reply()], ["DONE"]))
    bench.run_one(task, "off", 1, tmp_path / "root", keep=True)
    assert (tmp_path / "root" / "t01-off-1" / "new.txt").exists()


def test_count_jev(home):
    log = triage.jev_dir() / "log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"session_id": "S1", "scores": {"new_feature": 0.9}},
        {"session_id": "S1", "scores": None, "error": "timeout"},
        {"session_id": "S2", "scores": {"new_feature": 0.1}},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert bench.count_jev(["S1"]) == 1
    assert bench.count_jev([]) == 0


def test_cmd_run_skips_done_runs_and_respects_the_cap(
    home, repo, tmp_path, monkeypatch, capsys
):
    write_task(home, repo)
    fake = FakeClaude([reply(cost=3.0)] * 4, ["DONE"] * 4)
    monkeypatch.setattr(bench, "RUNNER", fake)
    argv = ["run", "--runs", "2", "--sandbox-root", str(tmp_path / "root")]
    # $3 spent + $10 budget for the next run > $12
    assert bench.main([*argv, "--max-total-usd", "12"]) == 1
    assert "cap" in capsys.readouterr().out
    names = [p.name for p in (home / "results").glob("*.json")]
    assert names == ["t01-off-1.json"]
    assert bench.main([*argv, "--max-total-usd", "100"]) == 0
    names = sorted(p.name for p in (home / "results").glob("*.json"))
    assert names == ["t01-off-1.json", "t01-off-2.json"]
    assert len(main_calls(fake)) == 2


def test_cmd_run_jev_arm_needs_key(home, repo, capsys):
    write_task(home, repo)
    assert bench.main(["run", "--arm", "jev"]) == 1
    assert "TYPESAFE_API_KEY" in capsys.readouterr().err


def test_cmd_run_charges_crashed_runs_to_the_cap(home, repo, tmp_path, monkeypatch):
    write_task(home, repo)
    monkeypatch.setattr(bench, "RUNNER", FakeClaude(["crash", "crash"]))
    argv = ["run", "--runs", "2", "--sandbox-root", str(tmp_path / "root")]
    # a crash may have spent its whole $10 budget: $10 + $10 > $15
    assert bench.main([*argv, "--max-total-usd", "15"]) == 1
    assert len(list((home / "results").glob("*.json"))) == 1


class FakeJudge:
    """Returns the queued result texts in order, as claude JSON replies."""

    def __init__(self, texts):
        self.texts = list(texts)
        self.prompts = []

    def __call__(self, argv, cwd, env, stdin, timeout=None):
        assert timeout == bench.SIDE_TIMEOUT_S
        assert "--strict-mcp-config" in argv
        self.prompts.append(stdin)
        assert tuple(argv[argv.index("--disallowedTools") + 1 :]) == bench.NO_TOOLS
        payload = {"session_id": "J", "total_cost_usd": 0.2}
        return ok(argv, {**payload, "result": self.texts.pop(0)})


GOOD = '{"checks": [true, false, true], "score": 4, "rationale": "mostly right"}'


def a_run(arm="off", n=1, diff="+a change", final="All done."):
    return {
        "task": "t01",
        "arm": arm,
        "n": n,
        "status": "done",
        "session_ids": [],
        "cost_usd": 2.0,
        "sim_cost_usd": 0.02,
        "turns": 5,
        "duration_ms": 60000,
        "replies": 1,
        "jev_evaluations": 0,
        "verify": None,
        "diff": diff,
        "log": "abc123 change",
        "final_text": final,
        "error": "",
    }


def test_reply_json_tolerates_fences():
    fenced = "Here you go:\n```json\n" + GOOD + "\n```"
    assert bench.reply_json(fenced)["score"] == 4
    assert bench.reply_json("no json here") is None


def test_redact_and_clip():
    text = (
        "keep this\njev triage: looks like a new feature\n"
        "Per the triage hint I asked first.\nand this"
    )
    # dropped silently: a marker would itself reveal the arm
    assert bench.redact(text) == "keep this\nand this"
    clipped = bench.clip("x" * 100, 40)
    assert clipped.startswith("x" * 40) and "cut 60 characters" in clipped


def test_grade_run(home, repo, monkeypatch):
    task = load(repo, home)
    judge = FakeJudge([GOOD])
    monkeypatch.setattr(bench, "RUNNER", judge)
    grade = bench.grade_run(task, a_run(final="jev triage said so\nAll done."))
    assert grade["checks"] == [True, False, True]
    assert grade["score"] == 4
    assert grade["error"] == ""
    assert grade["cost_usd"] == pytest.approx(0.2)
    prompt = judge.prompts[0]
    assert "v2 the answer" in prompt  # the reference diff from the real repo
    assert "jev triage said so" not in prompt
    assert "1. app.txt says v2" in prompt


def test_grade_retries_then_records_error(home, repo, monkeypatch):
    task = load(repo, home)
    wrong_length = '{"checks": [true], "score": 4, "rationale": "x"}'
    monkeypatch.setattr(bench, "RUNNER", FakeJudge(["not json", wrong_length]))
    grade = bench.grade_run(task, a_run())
    assert grade["checks"] is None
    assert grade["error"] == "judge reply malformed twice"
    assert grade["cost_usd"] == pytest.approx(0.4)


def test_grade_rejects_bool_score(home, repo, monkeypatch):
    task = load(repo, home)
    bad = '{"checks": [true, true, true], "score": true, "rationale": "x"}'
    monkeypatch.setattr(bench, "RUNNER", FakeJudge([bad, GOOD]))
    assert bench.grade_run(task, a_run())["score"] == 4


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_head_to_head_is_blind_and_mapped_back(home, repo, monkeypatch, seed):
    task = load(repo, home)
    jev = a_run("jev", diff="+ALPHA SIDE", final="jev triage hint seen\nok")
    off = a_run("off", diff="+OMEGA SIDE")
    judge = FakeJudge(['{"winner": "A", "reason": "A is better"}'])
    monkeypatch.setattr(bench, "RUNNER", judge)
    result = bench.head_to_head(task, jev, off, random.Random(seed))
    prompt = judge.prompts[0]
    jev_first = prompt.index("ALPHA SIDE") < prompt.index("OMEGA SIDE")
    assert result["jev_was"] == ("A" if jev_first else "B")
    assert result["winner"] == ("jev" if jev_first else "off")
    assert "jev" not in prompt.lower()
    assert "redacted" not in prompt


def test_rules_of_reads_the_transcript(home, monkeypatch):
    ev = bench.load_eval()
    transcript = home.parent / "projects" / "p" / "S1.jsonl"
    transcript.parent.mkdir(parents=True)
    edit = {"type": "tool_use", "id": "1", "name": "Edit"}
    records = [
        {"type": "user", "message": {"content": "add a csv export to the report"}},
        {
            "type": "assistant",
            "message": {"content": [{**edit, "input": {"file_path": "src/a.py"}}]},
        },
    ]
    transcript.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    monkeypatch.setattr(ev, "projects_dir", lambda: home.parent / "projects")
    run = a_run()
    run["session_ids"] = ["S1"]
    assert bench.rules_of(run) == {"asked": False, "preflight": False}
    assert bench.rules_of(a_run()) == {"asked": None, "preflight": None}


def test_cmd_grade(home, repo, monkeypatch):
    write_task(home, repo)
    for record in (a_run("off", 1), a_run("jev", 1), a_run("off", 2)):
        bench.save_result(record)
    judge = FakeJudge([GOOD, GOOD, GOOD, '{"winner": "tie", "reason": "same"}'])
    monkeypatch.setattr(bench, "RUNNER", judge)
    assert bench.main(["grade"]) == 0
    results = bench.load_results()
    assert all(r["grade"]["score"] == 4 for r in results)
    h2h = json.loads((home / "h2h.json").read_text(encoding="utf-8"))
    assert [(h["task"], h["n"], h["winner"]) for h in h2h] == [("t01", 1, "tie")]
    with (home / "grades.csv").open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3 and rows[0]["checks_passed"] == "2"
    assert bench.main(["grade"]) == 0  # nothing left to grade
    assert judge.texts == []


def test_cmd_grade_redoes_stale_head_to_heads(home, repo, monkeypatch):
    write_task(home, repo)
    for record in (a_run("off", 1), a_run("jev", 1)):
        record["grade"] = {"checks": [True] * 3, "score": 5, "cost_usd": 0}
        bench.save_result(record)
    (home / "h2h.json").write_text('[{"junk": 1}]', encoding="utf-8")
    judge = FakeJudge(['{"winner": "A", "reason": "x"}'])
    monkeypatch.setattr(bench, "RUNNER", judge)
    assert bench.main(["grade"]) == 0  # junk entry ignored, h2h computed
    rerun = a_run("jev", 1)
    rerun["started"] = "2026-10-01T00:00:00+00:00"  # redone with --force
    rerun["grade"] = {"checks": [True] * 3, "score": 5, "cost_usd": 0}
    bench.save_result(rerun)
    judge.texts.append('{"winner": "tie", "reason": "y"}')
    assert bench.main(["grade"]) == 0
    h2h = json.loads((home / "h2h.json").read_text(encoding="utf-8"))
    assert [h["winner"] for h in h2h] == ["tie"]


def graded(arm, n, checks, score, cost, preflight=None, asked=None):
    run = a_run(arm, n)
    run["cost_usd"] = cost
    grade = {"checks": checks, "score": score, "rationale": "", "error": ""}
    run["grade"] = {**grade, "cost_usd": 0.1, "asked": asked, "preflight": preflight}
    return run


def test_arm_stats():
    types = {"t01": "feature"}
    runs = [
        graded("off", 1, [True, True, False], 3, 2.0, preflight=False),
        graded("off", 2, [True, True, True], 5, 4.0, preflight=True),
    ]
    stats = bench.arm_stats(runs, types)
    assert stats["runs"] == 2
    assert stats["pass_rate"] == pytest.approx(5 / 6)
    assert stats["mean_score"] == pytest.approx(4)
    assert stats["preflight_miss"] == (1, 2)
    assert stats["no_ask"] == (0, 0)
    assert stats["cost"] == pytest.approx(3.0)
    assert stats["judge_cost"] == pytest.approx(0.2)


def test_verdict():
    base = {"runs": 2, "mean_score": 4, "pass_rate": 0.8, "cost": 3.0}
    assert "baseline only" in bench.verdict({"off": base}, [])
    better = {**base, "mean_score": 4.5, "cost": 3.2}
    wins = [{"winner": "jev"}, {"winner": "jev"}, {"winner": "tie"}]
    assert "keep jev" in bench.verdict({"off": base, "jev": better}, wins)
    pricey = {**better, "cost": 3.5}
    assert "not worth it" in bench.verdict({"off": base, "jev": pricey}, wins)
    losing = [{"winner": "off"}, {"winner": "jev"}]
    assert "not worth it" in bench.verdict({"off": base, "jev": better}, losing)


def test_report_baseline_only(home, repo, capsys):
    write_task(home, repo)
    bench.save_result(graded("off", 1, [True, True, False], 3, 2.0, preflight=False))
    assert bench.main(["report"]) == 0
    out = capsys.readouterr().out
    assert "baseline only" in out
    assert "t01" in out
    assert "large effect" in out
    assert "pre-flight skipped 1/1" in out


def test_load_results_skips_bad_files(home, capsys):
    bench.save_result(a_run())
    (home / "results" / "broken.json").write_text("{half", encoding="utf-8")
    wrong = [
        {**a_run(n=2), "grade": "x"},
        {**a_run(n=3), "cost_usd": "abc"},
        {**a_run(n=4), "grade": {"checks": [True, "x"], "score": 3}},
    ]
    for i, record in enumerate(wrong):
        path = home / "results" / f"wrong{i}.json"
        path.write_text(json.dumps(record), encoding="utf-8")
    assert len(bench.load_results()) == 1
    err = capsys.readouterr().err
    assert "broken.json" in err and "wrong2.json" in err


def test_render_shows_wins_ties_losses():
    stats = {"off": {**bench.arm_stats([graded("off", 1, [True], 4, 2.0)], {})}}
    stats["jev"] = bench.arm_stats([graded("jev", 1, [True], 4, 2.0)], {})
    h2h = [{"winner": "jev"}, {"winner": "tie"}, {"winner": "off"}]
    out = bench.render(stats, {}, h2h)
    assert "jev wins / ties / losses: 1 / 1 / 1" in out
    assert "/run" in out


def test_report_without_results(home, capsys):
    assert bench.main(["report"]) == 1
    assert "no results" in capsys.readouterr().out
