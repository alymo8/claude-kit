# jev task bench Implementation Plan

- **Status:** draft
- **Date:** 2026-09-29

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `plugin/scripts/jev-bench.py` (`check`, `run`, `grade`, `report`), which replays real tasks headless in throwaway sandboxes with jev on and off, grades them blind, and reports quality and cost. Also prove with one spike run that headless runs fire the jev hook and respect the denied tools.

**Architecture:** One stdlib-only script. It imports the hook module (`plugin/hooks/jev_triage.py`, as `triage`) for `jev_dir()`, and loads `plugin/scripts/jev-eval.py` by path (as `jev_eval`) to reuse `read_jsonl`, `transcript_for`, `turns` and `outcome`. Every `claude` invocation goes through one module-level callable, `RUNNER(argv, cwd, env, stdin)`, so tests swap in a fake and never call the real CLI. Prompts go in on stdin, which avoids Windows command-line length limits. Task files, results, `grades.csv` and `h2h.json` live under `~/.claude/claude-kit/jev/bench/` (`triage.jev_dir() / "bench"`). Sandboxes live under `<repo root>/.jev-bench/`, which the kit's whitelist `.gitignore` already ignores.

**Tech Stack:** Python ≥ 3.11 stdlib, git, the `claude` CLI (2.1.x: `-p`, `--output-format json`, `--resume`, `--max-budget-usd`, `--disallowedTools`, `--permission-mode`), pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-09-29-jev-task-bench-design.md`

## Global Constraints

- **Public repo.** No private prompt, repository name, path, username or email in any tracked file, test fixtures included. Test repos are created in `tmp_path` with generic content.
- Tests make no network calls and never run the real `claude`: they monkeypatch `bench.RUNNER` and `bench.claude_bin`. Tests do run real `git` (available in CI) against temporary repositories.
- Budget defaults: `--budget 10` (USD per run), `--max-total-usd 150` (per `run` invocation). Model defaults: `opus` for runs and the judge, `haiku` for the simulated user. At most 6 simulated-user replies per run.
- Sandboxes contain no remote and no commits after `base_commit`, so the real answer cannot be found with `git log --all`.
- Child environments drop variables whose names match `TOKEN|SECRET|PASSWORD|KEY|SUPABASE|AZURE|AWS|GH_|GITHUB|DATABASE_URL` (case-insensitive), except names starting with `ANTHROPIC_` or `CLAUDE_`. `TYPESAFE_API_KEY` is present only in the jev arm. `CLAUDE_KIT_JEV` is `active` for the jev arm and `off` otherwise.
- Every task run call passes all of `DENIED` via `--disallowedTools`. Simulated-user and judge calls deny every tool (`NO_TOOLS`) and run in an empty temporary directory.
- Ruff `E, F, I, UP, B`, line length 88 including E501 (run `ruff format plugin tests`, then rewrap what `ruff check` still flags). Test imports: `from helpers import ...` sits in the same block as `pytest`.
- Before every commit: `pytest` and `ruff check plugin tests; ruff format --check plugin tests`, all green. Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Out of this plan:** writing the 10 real task files and running the no-jev arm. They need the user's approval of every brief and rubric first (spec, "Task authoring"), and they spend real money.

## Review Focus

1. **The sandbox must not leak the answer.** After `make_sandbox`, the reference commit and later tags must be absent (`git cat-file -e` fails). Covered in Task 2 by `test_sandbox_has_no_remote_and_no_future_commits`.
2. **Removing a sandbox on Windows** hits read-only files under `.git/objects`. Removal must still succeed. Covered in Task 2 by `test_remove_tree_handles_read_only_files`.
3. **A `claude` call that times out, crashes or prints non-JSON** must end the run with `status: error` and a message, with the sandbox still removed. Covered in Task 3 by `test_run_crash_is_an_error` and `test_run_timeout_is_an_error`.
4. **A judge reply wrapped in prose or code fences** (```` ```json … ``` ````) must still parse, and a truly malformed reply must be retried once, then recorded. Covered in Task 4 by `test_reply_json_tolerates_fences` and `test_grade_retries_then_records_error`.
5. **A result file edited or truncated by hand** must not crash `report` or `grade`; it is skipped. Covered in Task 5 by `test_load_results_skips_bad_files`.

---

### Task 1: Task files and `check`

**Files:**
- Create: `plugin/scripts/jev-bench.py`
- Create: `tests/test_jev_bench.py`

**Interfaces:**
- Produces: `TYPES`, `ARMS = ("off", "jev")`; `bench_dir() -> Path`; `TaskError(ValueError)`; `Task` (frozen dataclass: `id, type, repo: Path, base_commit, reference, prompt, brief, rubric: tuple[str, ...], verify=""`); `load_task(path) -> Task`; `git(repo, *args) -> CompletedProcess`; `has_commit(repo, sha) -> bool`; `problems(task) -> list[str]`; `load_tasks(names=None) -> tuple[list[Task], list[str]]`; `claude_bin() -> str | None`; `main(argv) -> int` with a `check` subcommand.

- [ ] **Step 1: Write the failing tests** in `tests/test_jev_bench.py`:

```python
import json
import subprocess

import pytest
from helpers import PLUGIN, load_module

bench = load_module(PLUGIN / "scripts" / "jev-bench.py", "jev_bench")
triage = bench.triage


def git(repo, *args):
    out = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
         *args],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
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


def write_task(home, repo, **overrides):
    path, base, answer = repo
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
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_bench.py -v` → FAIL (file missing).

- [ ] **Step 3: Implement** `plugin/scripts/jev-bench.py`:

```python
#!/usr/bin/env python3
"""Replay real tasks with and without jev; compare quality and cost.

  check [--arm off|jev|both]           validate task files and prerequisites
  run [--tasks t01,t02] [--arm off|jev|both] [--runs 2] [--model opus]
      [--budget 10] [--max-total-usd 150] [--keep] [--force] [--sandbox-root D]
                                       headless runs in throwaway sandboxes
  grade [--regrade] [--model opus] [--seed 0]
                                       blind rubric grades and head-to-heads
  report                               jev vs no-jev quality and cost

Task files are private and live in ~/.claude/claude-kit/jev/bench/tasks/*.json;
results/, grades.csv and h2h.json sit next to them. Spec:
docs/superpowers/specs/2026-09-29-jev-task-bench-design.md
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hooks"))

import jev_triage as triage  # noqa: E402

TYPES = ("feature", "bug", "vague", "decision")
ARMS = ("off", "jev")
FIELDS = ("id", "type", "repo", "base_commit", "reference", "prompt", "brief", "rubric")


def bench_dir() -> Path:
    return triage.jev_dir() / "bench"


class TaskError(ValueError):
    pass


@dataclass(frozen=True)
class Task:
    id: str
    type: str
    repo: Path
    base_commit: str
    reference: str
    prompt: str
    brief: str
    rubric: tuple[str, ...]
    verify: str = ""


def load_task(path: Path) -> Task:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TaskError(f"{path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise TaskError(f"{path.name}: not a JSON object")
    missing = [f for f in FIELDS if not data.get(f)]
    if missing:
        raise TaskError(f"{path.name}: missing {', '.join(missing)}")
    rubric = data["rubric"]
    if not isinstance(rubric, list) or not all(
        isinstance(item, str) and item.strip() for item in rubric
    ):
        raise TaskError(f"{path.name}: rubric must be a list of strings")
    return Task(
        id=str(data["id"]),
        type=str(data["type"]),
        repo=Path(data["repo"]),
        base_commit=str(data["base_commit"]),
        reference=str(data["reference"]),
        prompt=str(data["prompt"]),
        brief=str(data["brief"]),
        rubric=tuple(rubric),
        verify=str(data.get("verify") or ""),
    )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def has_commit(repo: Path, sha: str) -> bool:
    return git(repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def problems(task: Task) -> list[str]:
    found = []
    if task.type not in TYPES:
        found.append(f"type {task.type!r} not one of {', '.join(TYPES)}")
    if not 3 <= len(task.rubric) <= 6:
        found.append(f"rubric has {len(task.rubric)} items (want 3-6)")
    if not (task.repo / ".git").exists():
        found.append(f"repo {task.repo} is not a git repository")
        return found
    if not has_commit(task.repo, task.base_commit):
        found.append(f"base_commit {task.base_commit} not found")
    ends = task.reference.split("..")
    if len(ends) != 2 or not all(ends):
        found.append(f"reference {task.reference!r} is not <from>..<to>")
    else:
        found += [
            f"reference commit {sha} not found"
            for sha in ends
            if not has_commit(task.repo, sha)
        ]
    return found


def load_tasks(names: list[str] | None = None) -> tuple[list[Task], list[str]]:
    tasks: list[Task] = []
    errors: list[str] = []
    for path in sorted((bench_dir() / "tasks").glob("*.json")):
        try:
            task = load_task(path)
        except TaskError as exc:
            errors.append(str(exc))
            continue
        if not names or task.id in names:
            tasks.append(task)
    return tasks, errors


def claude_bin() -> str | None:
    return shutil.which("claude")


def prerequisites(tasks: list[Task], arms: tuple[str, ...]) -> list[str]:
    found = [f"{t.id}: {p}" for t in tasks for p in problems(t)]
    if not tasks:
        found.append(f"no task files in {bench_dir() / 'tasks'}")
    if claude_bin() is None:
        found.append("claude CLI not found on PATH")
    if "jev" in arms and not os.environ.get("TYPESAFE_API_KEY", "").strip():
        found.append("TYPESAFE_API_KEY not set (needed for the jev arm)")
    return found


def arms_of(value: str) -> tuple[str, ...]:
    return ARMS if value == "both" else (value,)


def cmd_check(args: argparse.Namespace) -> int:
    tasks, errors = load_tasks()
    errors += prerequisites(tasks, arms_of(args.arm))
    for error in errors:
        print(f"problem: {error}", file=sys.stderr)
    print(f"{len(tasks)} task(s), {len(errors)} problem(s)")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay real tasks with and without jev.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate task files and prerequisites")
    check.add_argument("--arm", choices=(*ARMS, "both"), default="off")
    args = parser.parse_args(argv)
    handler = {"check": cmd_check}
    return handler[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verify.** `pytest tests/test_jev_bench.py -v` → PASS; full `pytest`; `ruff format plugin tests`; `ruff check plugin tests`.

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-bench.py tests/test_jev_bench.py
git commit -m "jev-bench: task files and check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Sandbox, child environment and claude arguments

**Files:**
- Modify: `plugin/scripts/jev-bench.py`
- Modify: `tests/test_jev_bench.py` (append)

**Interfaces:**
- Consumes: `Task`, `git` from Task 1.
- Produces: `SECRET_RE`, `KEEP_PREFIXES`, `DENIED: tuple[str, ...]`, `NO_TOOLS: tuple[str, ...]`; `child_env(arm, base=None) -> dict[str, str]`; `claude_args(model, budget, resume=None, tools=DENIED, permission="bypassPermissions") -> list[str]` (the prompt goes on stdin; `--disallowedTools` is always last); `default_sandbox_root() -> Path`; `remove_tree(path) -> None`; `make_sandbox(task, root, name) -> Path` (raises `RuntimeError`).

- [ ] **Step 1: Write the failing tests** by appending to `tests/test_jev_bench.py`:

```python
import os  # noqa: E402  (move to the top import block when formatting)
import stat  # noqa: E402


def load(repo_fixture, home):
    write_task(home, repo_fixture)
    return bench.load_task(home / "tasks" / "t01.json")


def test_sandbox_has_no_remote_and_no_future_commits(home, repo, tmp_path):
    task = load(repo, home)
    sandbox = bench.make_sandbox(task, tmp_path / "bench-root", "t01-off-1")
    assert sandbox == tmp_path / "bench-root" / "t01-off-1"
    assert git(sandbox, "rev-parse", "HEAD") == task.base_commit
    assert git(sandbox, "branch", "--show-current") == "main"
    assert git(sandbox, "remote") == ""
    answer = task.reference.split("..")[1]
    gone = subprocess.run(["git", "-C", str(sandbox), "cat-file", "-e", answer])
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
    for secret in ("GITHUB_TOKEN", "SUPABASE_ACCESS_TOKEN", "OPENAI_API_KEY",
                   "DATABASE_URL", "TYPESAFE_API_KEY"):  # fmt: skip
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
```

When formatting, move `import os` and `import stat` to the top import block and drop the `noqa` comments.

- [ ] **Step 2: Run them.** `pytest tests/test_jev_bench.py -v` → the new tests FAIL (`AttributeError`).

- [ ] **Step 3: Implement.** Add `import re` and `import stat` to the imports, then add after `claude_bin`:

```python
SECRET_RE = re.compile(
    r"TOKEN|SECRET|PASSWORD|KEY|SUPABASE|AZURE|AWS|GH_|GITHUB|DATABASE_URL", re.I
)
KEEP_PREFIXES = ("ANTHROPIC_", "CLAUDE_")
# Nothing may leave the machine or pop up on the user's screen.
DENIED = (
    "Bash(git push:*)",
    "Bash(gh:*)",
    "Bash(supabase:*)",
    "Bash(npx supabase:*)",
    "Bash(az:*)",
    "Bash(vercel:*)",
    "Bash(explorer:*)",
    "Bash(start:*)",
    "PowerShell(git push:*)",
    "PowerShell(gh:*)",
    "PowerShell(Invoke-Item:*)",
    "PowerShell(ii:*)",
    "PowerShell(explorer:*)",
    "PowerShell(start:*)",
    "PowerShell(Start-Process:*)",
)
NO_TOOLS = (
    "Bash",
    "PowerShell",
    "Edit",
    "Write",
    "Read",
    "Glob",
    "Grep",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
    "Task",
    "Agent",
    "TodoWrite",
    "Skill",
)


def child_env(arm: str, base: dict[str, str] | None = None) -> dict[str, str]:
    """The environment for a run: no secrets; jev on only in the jev arm."""
    source = dict(os.environ if base is None else base)
    env = {
        k: v
        for k, v in source.items()
        if k.upper().startswith(KEEP_PREFIXES) or not SECRET_RE.search(k)
    }
    env.pop("TYPESAFE_API_KEY", None)
    env["CLAUDE_KIT_JEV"] = "active" if arm == "jev" else "off"
    if arm == "jev" and source.get("TYPESAFE_API_KEY"):
        env["TYPESAFE_API_KEY"] = source["TYPESAFE_API_KEY"]
    return env


def claude_args(
    model: str,
    budget: float,
    resume: str | None = None,
    tools: tuple[str, ...] = DENIED,
    permission: str = "bypassPermissions",
) -> list[str]:
    """argv for one headless call; the prompt goes on stdin."""
    argv = [
        claude_bin() or "claude",
        "-p",
        "--model",
        model,
        "--output-format",
        "json",
        "--max-budget-usd",
        f"{budget:.2f}",
    ]
    if permission:
        argv += ["--permission-mode", permission]
    if resume:
        argv += ["--resume", resume]
    return [*argv, "--disallowedTools", *tools]


def default_sandbox_root() -> Path:
    """<repo root>/.jev-bench: inside the workspace, ignored by .gitignore."""
    return HERE.parents[1] / ".jev-bench"


def _force_remove(func, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path: Path) -> None:
    if not path.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_force_remove)
    else:  # pragma: no cover - 3.11
        shutil.rmtree(path, onerror=_force_remove)


def make_sandbox(task: Task, root: Path, name: str) -> Path:
    """A clone at base_commit with no remote and no later commits or tags."""
    dest = root / name
    remove_tree(dest)
    root.mkdir(parents=True, exist_ok=True)
    clone = subprocess.run(
        ["git", "clone", "--quiet", "--no-local", "--no-checkout", str(task.repo),
         str(dest)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )  # fmt: skip
    if clone.returncode:
        raise RuntimeError(f"sandbox: git clone failed: {clone.stderr.strip()}")
    steps = [
        ("checkout", "--quiet", "-B", "main", task.base_commit),
        ("remote", "remove", "origin"),
    ]
    for args in steps:
        _git_or_raise(dest, *args)
    refs = git(dest, "for-each-ref", "--format=%(refname)").stdout.split()
    for ref in refs:
        if ref != "refs/heads/main":
            _git_or_raise(dest, "update-ref", "-d", ref)
    _git_or_raise(dest, "reflog", "expire", "--expire=now", "--all")
    _git_or_raise(dest, "gc", "--quiet", "--prune=now")
    return dest


def _git_or_raise(repo: Path, *args: str) -> None:
    out = git(repo, *args)
    if out.returncode:
        raise RuntimeError(f"sandbox: git {args[0]} failed: {out.stderr.strip()}")
```

- [ ] **Step 4: Verify.** `pytest tests/test_jev_bench.py -v` → PASS; full `pytest`; ruff format and check.

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-bench.py tests/test_jev_bench.py
git commit -m "jev-bench: sandboxes without remote or answer, scrubbed env, denied tools

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The run loop, simulated user and `run`

**Files:**
- Modify: `plugin/scripts/jev-bench.py`
- Modify: `tests/test_jev_bench.py` (append)

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces: `RUNNER` (module-level; default `default_runner(argv, cwd, env, stdin) -> CompletedProcess`); `load_eval()` (loads `jev-eval.py` as `jev_eval`); `parse_output(proc) -> dict | None`; `SIM_TEMPLATE`; `is_done(text) -> bool`; `sim_reply(task, last) -> tuple[str, float] | None`; `sandbox_changes(sandbox, base) -> tuple[str, str]`; `run_verify(command, sandbox, env) -> bool`; `count_jev(session_ids) -> int`; `run_one(task, arm, n, root, model="opus", budget=10.0, max_replies=6, keep=False) -> dict`; `results_dir()`, `save_result(record)`, `load_results() -> list[dict]`; `cmd_run(args) -> int`.
- Result record keys: `task, arm, n, status, session_ids, cost_usd, sim_cost_usd, turns, duration_ms, replies, jev_evaluations, verify, diff, log, final_text, error, started`. `status` is one of `done`, `max_replies`, `budget`, `error`.

- [ ] **Step 1: Write the failing tests** by appending to `tests/test_jev_bench.py` (add `import pytest` users already exist; add `from pathlib import Path` to the top imports):

```python
def ok(argv, payload):
    return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")


def reply(session="S1", cost=1.5, text="Done. Anything else?", **extra):
    return {"session_id": session, "total_cost_usd": cost, "num_turns": 3,
            "duration_ms": 1000, "result": text, **extra}  # fmt: skip


class FakeClaude:
    """Main task calls pop `main`; simulated-user (haiku) calls pop `sim`."""

    def __init__(self, main, sim=(), edit=True):
        self.main = list(main)
        self.sim = list(sim)
        self.edit = edit
        self.calls = []

    def __call__(self, argv, cwd, env, stdin):
        self.calls.append((argv, Path(cwd), env, stdin))
        if "haiku" in argv:
            return ok(argv, {"session_id": "sim", "result": self.sim.pop(0),
                             "total_cost_usd": 0.01})  # fmt: skip
        item = self.main.pop(0)
        if item == "crash":
            return subprocess.CompletedProcess(argv, 1, "", "boom")
        if item == "timeout":
            raise subprocess.TimeoutExpired(argv, 1)
        if self.edit:
            (Path(cwd) / "new.txt").write_text("made by the run\n", encoding="utf-8")
        return ok(argv, item)


def main_calls(fake):
    return [c for c in fake.calls if "haiku" not in c[0]]


def test_run_stops_when_user_says_done(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    fake = FakeClaude([reply(text="Use X or Y?"), reply(cost=2.0)], ["Use X please", "DONE"])
    monkeypatch.setattr(bench, "RUNNER", fake)
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert record["status"] == "done"
    assert record["replies"] == 1
    assert record["cost_usd"] == pytest.approx(3.5)
    assert record["sim_cost_usd"] == pytest.approx(0.02)
    assert record["turns"] == 6
    assert record["session_ids"] == ["S1"]
    assert "new.txt" in record["diff"]
    first, second = main_calls(fake)
    assert first[3] == task.prompt
    assert second[3] == "Use X please"
    assert second[0][second[0].index("--resume") + 1] == "S1"
    for argv, cwd, env, _ in main_calls(fake):
        assert tuple(argv[argv.index("--disallowedTools") + 1 :]) == bench.DENIED
        assert argv[argv.index("--model") + 1] == "opus"
        assert env["CLAUDE_KIT_JEV"] == "off"
        assert cwd == tmp_path / "root" / "t01-off-1"
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
    fake = FakeClaude([reply(cost=2.0), reply(cost=2.0)], ["more please now"] * 2)
    monkeypatch.setattr(bench, "RUNNER", fake)
    record = bench.run_one(task, "off", 1, tmp_path / "root", budget=3.0)
    assert record["status"] == "budget"
    second = main_calls(fake)[1][0]
    assert second[second.index("--max-budget-usd") + 1] == "1.00"


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
    assert not (tmp_path / "root" / "t01-off-1").exists()


def test_run_timeout_is_an_error(home, repo, tmp_path, monkeypatch):
    task = load(repo, home)
    monkeypatch.setattr(bench, "RUNNER", FakeClaude(["timeout"]))
    record = bench.run_one(task, "off", 1, tmp_path / "root")
    assert record["status"] == "error"
    assert "timed out" in record["error"]


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
    write_task(home, repo, verify=command)
    task = bench.load_task(home / "tasks" / "t01.json")
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


def test_cmd_run_skips_done_runs_and_respects_the_cap(home, repo, tmp_path, monkeypatch, capsys):
    write_task(home, repo)
    root = str(tmp_path / "root")
    fake = FakeClaude([reply(cost=3.0)] * 4, ["DONE"] * 4)
    monkeypatch.setattr(bench, "RUNNER", fake)
    argv = ["run", "--runs", "2", "--budget", "10", "--sandbox-root", root]
    assert bench.main([*argv, "--max-total-usd", "15"]) == 1
    assert "cap" in capsys.readouterr().out
    assert [p.name for p in (home / "results").glob("*.json")] == ["t01-off-1.json"]
    assert bench.main([*argv, "--max-total-usd", "100"]) == 0
    names = sorted(p.name for p in (home / "results").glob("*.json"))
    assert names == ["t01-off-1.json", "t01-off-2.json"]
    assert len(main_calls(fake)) == 2


def test_cmd_run_jev_arm_needs_key(home, repo, capsys):
    write_task(home, repo)
    assert bench.main(["run", "--arm", "jev"]) == 1
    assert "TYPESAFE_API_KEY" in capsys.readouterr().err
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_bench.py -v` → the new tests FAIL.

- [ ] **Step 3: Implement.** Add `import importlib.util`, `import tempfile`, `from collections.abc import Callable` and `from datetime import UTC, datetime` to the imports. Add after `_git_or_raise`:

```python
CALL_TIMEOUT_S = 3600
MIN_CALL_BUDGET = 0.5
MAX_REPLIES = 6
Runner = Callable[[list[str], Path, dict[str, str], str], subprocess.CompletedProcess]


def default_runner(
    argv: list[str], cwd: Path, env: dict[str, str], stdin: str
) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=CALL_TIMEOUT_S,
    )


RUNNER: Runner = default_runner  # tests replace this


def load_eval():
    """plugin/scripts/jev-eval.py (hyphenated name), loaded once."""
    if "jev_eval" not in sys.modules:
        spec = importlib.util.spec_from_file_location("jev_eval", HERE / "jev-eval.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules["jev_eval"] = module
        spec.loader.exec_module(module)
    return sys.modules["jev_eval"]


def parse_output(proc: subprocess.CompletedProcess) -> dict | None:
    try:
        data = json.loads(proc.stdout or "")
    except ValueError:
        return None
    return data if isinstance(data, dict) and data.get("session_id") else None


SIM_TEMPLATE = """You are role-playing a software developer who asked an AI \
coding assistant for help. Reply to the assistant's latest message as this user.

Rules:
- At most three sentences, plain text.
- Answer the assistant's questions from the brief below; when the brief does not \
say, choose what the assistant recommends.
- Approve reasonable specs and plans. When asked to choose, choose what the brief \
says the user chose.
- This is a sandbox copy with no git remote. If the assistant mentions branches, \
pushing, pull requests, CI or merging, tell it to finish locally on main without \
pushing.
- Never write code.
- Reply exactly DONE when the task looks finished, or when the assistant is not \
asking or waiting for anything.

What the user wanted (brief):
{brief}

The user's original request:
{prompt}

The assistant's latest message:
{last}
"""


def is_done(text: str) -> bool:
    return text.strip().strip(".!").upper() == "DONE" or not text.strip()


def sim_reply(task: Task, last: str) -> tuple[str, float] | None:
    """The simulated user's reply and its cost; None when the call failed."""
    prompt = SIM_TEMPLATE.format(brief=task.brief, prompt=task.prompt, last=last[-8000:])
    with tempfile.TemporaryDirectory(prefix="jev-sim-") as tmp:
        try:
            proc = RUNNER(
                claude_args("haiku", 1.0, tools=NO_TOOLS, permission=""),
                Path(tmp),
                child_env("off"),
                prompt,
            )
        except subprocess.TimeoutExpired:
            return None
    out = parse_output(proc)
    if out is None:
        return None
    return str(out.get("result") or ""), float(out.get("total_cost_usd") or 0)


def sandbox_changes(sandbox: Path, base: str) -> tuple[str, str]:
    """The run's diff against base (untracked files included) and its git log."""
    git(sandbox, "add", "-A", "--intent-to-add")
    diff = git(sandbox, "diff", base).stdout
    log = git(sandbox, "log", "--oneline", f"{base}..HEAD").stdout
    return diff, log


def run_verify(command: str, sandbox: Path, env: dict[str, str]) -> bool:
    try:
        done = subprocess.run(
            command, shell=True, cwd=sandbox, env=env, capture_output=True, timeout=900
        )
    except subprocess.TimeoutExpired:
        return False
    return done.returncode == 0


def count_jev(session_ids: list[str]) -> int:
    path = triage.jev_dir() / "log.jsonl"
    if not session_ids or not path.exists():
        return 0
    return sum(
        1
        for record in load_eval().read_jsonl(path)
        if record.get("session_id") in session_ids and record.get("scores")
    )


def new_record(task: Task, arm: str, n: int) -> dict:
    return {
        "task": task.id,
        "arm": arm,
        "n": n,
        "status": "error",
        "session_ids": [],
        "cost_usd": 0.0,
        "sim_cost_usd": 0.0,
        "turns": 0,
        "duration_ms": 0,
        "replies": 0,
        "jev_evaluations": 0,
        "verify": None,
        "diff": "",
        "log": "",
        "final_text": "",
        "error": "",
        "started": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def converse(task: Task, record: dict, sandbox: Path, env: dict, model: str,
             budget: float, max_replies: int) -> None:  # fmt: skip
    """Claude and the simulated user take turns until a stop rule fires."""
    prompt, session = task.prompt, None
    while True:
        remaining = budget - record["cost_usd"]
        if remaining < MIN_CALL_BUDGET:
            record["status"] = "budget"
            return
        try:
            proc = RUNNER(claude_args(model, remaining, session), sandbox, env, prompt)
        except subprocess.TimeoutExpired:
            record["error"] = "claude call timed out"
            return
        out = parse_output(proc)
        if out is None:
            tail = (proc.stderr or proc.stdout or "")[-500:]
            record["error"] = f"claude exited {proc.returncode}: {tail}"
            return
        session = str(out["session_id"])
        if session not in record["session_ids"]:
            record["session_ids"].append(session)
        record["cost_usd"] += float(out.get("total_cost_usd") or 0)
        record["turns"] += int(out.get("num_turns") or 0)
        record["duration_ms"] += int(out.get("duration_ms") or 0)
        record["final_text"] = str(out.get("result") or "")
        if out.get("is_error"):
            subtype = str(out.get("subtype") or "error")
            record["status"] = "budget" if "budget" in subtype else "error"
            record["error"] = subtype
            return
        if record["cost_usd"] >= budget:
            record["status"] = "budget"
            return
        if record["replies"] >= max_replies:
            record["status"] = "max_replies"
            return
        answer = sim_reply(task, record["final_text"])
        if answer is None:
            record["error"] = "simulated user failed"
            return
        text, cost = answer
        record["sim_cost_usd"] += cost
        if is_done(text):
            record["status"] = "done"
            return
        prompt = text
        record["replies"] += 1


def run_one(
    task: Task,
    arm: str,
    n: int,
    root: Path,
    model: str = "opus",
    budget: float = 10.0,
    max_replies: int = MAX_REPLIES,
    keep: bool = False,
) -> dict:
    record = new_record(task, arm, n)
    try:
        sandbox = make_sandbox(task, root, f"{task.id}-{arm}-{n}")
    except RuntimeError as exc:
        record["error"] = str(exc)
        return record
    env = child_env(arm)
    try:
        converse(task, record, sandbox, env, model, budget, max_replies)
        record["diff"], record["log"] = sandbox_changes(sandbox, task.base_commit)
        if task.verify:
            record["verify"] = run_verify(task.verify, sandbox, env)
    finally:
        if not keep:
            remove_tree(sandbox)
    record["jev_evaluations"] = count_jev(record["session_ids"])
    return record


def results_dir() -> Path:
    return bench_dir() / "results"


def save_result(record: dict) -> None:
    path = results_dir() / f"{record['task']}-{record['arm']}-{record['n']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")


def load_results() -> list[dict]:
    records = []
    for path in sorted(results_dir().glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print(f"skipping unreadable {path.name}", file=sys.stderr)
            continue
        if isinstance(record, dict) and {"task", "arm", "n"} <= set(record):
            records.append(record)
    return records


def cmd_run(args: argparse.Namespace) -> int:
    names = args.tasks.split(",") if args.tasks else None
    tasks, errors = load_tasks(names)
    arms = arms_of(args.arm)
    errors += prerequisites(tasks, arms)
    if errors:
        for error in errors:
            print(f"problem: {error}", file=sys.stderr)
        return 1
    done = set() if args.force else {(r["task"], r["arm"], r["n"]) for r in load_results()}
    root = Path(args.sandbox_root) if args.sandbox_root else default_sandbox_root()
    spent, ran = 0.0, 0
    for task in tasks:
        for n in range(1, args.runs + 1):
            for arm in arms:
                if (task.id, arm, n) in done:
                    continue
                if spent + args.budget > args.max_total_usd:
                    print(f"stopping: the next run could pass the ${args.max_total_usd:.0f}"
                          f" cap (spent ${spent:.2f})")  # fmt: skip
                    return 1
                print(f"run {task.id}-{arm}-{n}", flush=True)
                record = run_one(task, arm, n, root, args.model, args.budget,
                                 MAX_REPLIES, args.keep)  # fmt: skip
                save_result(record)
                spent += record["cost_usd"] + record["sim_cost_usd"]
                ran += 1
                print(f"  {record['status']} ${record['cost_usd']:.2f}"
                      f" {record['turns']} turns {record['replies']} replies",
                      flush=True)  # fmt: skip
    print(f"{ran} run(s), ${spent:.2f} spent")
    return 0
```

In `main`, add the `run` parser and handler:

```python
    run = sub.add_parser("run", help="headless runs in throwaway sandboxes")
    run.add_argument("--tasks", default="", help="comma-separated ids; default all")
    run.add_argument("--arm", choices=(*ARMS, "both"), default="off")
    run.add_argument("--runs", type=int, default=2)
    run.add_argument("--model", default="opus")
    run.add_argument("--budget", type=float, default=10.0, help="USD per run")
    run.add_argument("--max-total-usd", type=float, default=150.0)
    run.add_argument("--keep", action="store_true", help="keep sandboxes")
    run.add_argument("--force", action="store_true", help="redo existing runs")
    run.add_argument("--sandbox-root", default="")
```

and `"run": cmd_run` in `handler`.

- [ ] **Step 4: Verify.** `pytest tests/test_jev_bench.py -v` → PASS; full `pytest`; ruff format and check (rewrap the `# fmt: skip` lines that exceed 88 characters).

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-bench.py tests/test_jev_bench.py
git commit -m "jev-bench: run loop with simulated user, budget caps and results

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Grading

**Files:**
- Modify: `plugin/scripts/jev-bench.py`
- Modify: `tests/test_jev_bench.py` (append)

**Interfaces:**
- Consumes: `RUNNER`, `claude_args`, `NO_TOOLS`, `child_env`, `parse_output`, `load_eval`, `load_tasks`, `load_results`, `save_result`, `git` from Tasks 1–3.
- Produces: `JUDGE_TEMPLATE`, `H2H_TEMPLATE`; `redact(text) -> str`; `clip(text, limit=60000) -> str`; `reply_json(text) -> dict | None`; `ask_judge(prompt, valid, model) -> tuple[dict | None, float]`; `rules_of(run) -> dict` (`asked`, `preflight`); `grade_run(task, run, model="opus") -> dict` (`checks, score, rationale, error, cost_usd, asked, preflight`); `head_to_head(task, jev_run, off_run, rng, model="opus") -> dict` (`task, n, winner ∈ {"jev","off","tie",None}, jev_was, reason, cost_usd, error`); `write_grades_csv(results)`; `cmd_grade(args) -> int`.

- [ ] **Step 1: Write the failing tests** by appending to `tests/test_jev_bench.py` (add `import csv` and `import random` to the top imports):

```python
class FakeJudge:
    """Returns the queued result texts in order, as a claude JSON reply."""

    def __init__(self, texts):
        self.texts = list(texts)
        self.prompts = []

    def __call__(self, argv, cwd, env, stdin):
        self.prompts.append(stdin)
        assert tuple(argv[argv.index("--disallowedTools") + 1 :]) == bench.NO_TOOLS
        return ok(argv, {"session_id": "J", "result": self.texts.pop(0),
                         "total_cost_usd": 0.2})  # fmt: skip


GOOD = '{"checks": [true, false, true], "score": 4, "rationale": "mostly right"}'


def a_run(arm="off", n=1, diff="+v2 the answer", final="All done."):
    return {"task": "t01", "arm": arm, "n": n, "status": "done", "session_ids": [],
            "cost_usd": 2.0, "sim_cost_usd": 0.02, "turns": 5, "duration_ms": 60000,
            "replies": 1, "jev_evaluations": 0, "verify": None, "diff": diff,
            "log": "abc123 change", "final_text": final, "error": ""}  # fmt: skip


def test_reply_json_tolerates_fences():
    fenced = "Here you go:\n```json\n" + GOOD + "\n```"
    assert bench.reply_json(fenced)["score"] == 4
    assert bench.reply_json("no json here") is None


def test_redact_and_clip():
    text = "keep this\njev triage: looks like a new feature\nand this"
    assert bench.redact(text) == "keep this\n[redacted]\nand this"
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
    assert "v2 the answer" in prompt  # reference diff from the real repo
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


def test_rules_of_reads_the_transcript(home, monkeypatch):
    ev = bench.load_eval()
    transcript = home.parent / "projects" / "p" / "S1.jsonl"
    transcript.parent.mkdir(parents=True)
    records = [
        {"type": "user", "message": {"content": "add a csv export to the report"}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "1", "name": "Edit",
             "input": {"file_path": "src/a.py"}}]}},
    ]  # fmt: skip
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
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_bench.py -v` → the new tests FAIL.

- [ ] **Step 3: Implement.** Add `import csv` and `import random` to the imports. Add after `cmd_run`:

```python
JUDGE_TEMPLATE = """You are grading an AI coding assistant's work on a real task. \
You do not know which configuration produced it; judge only the work.

Task type: {type}

The user's request:
{prompt}

What the user actually wanted:
{brief}

Rubric (judge each item pass or fail):
{rubric}

Reference, what the user's real session delivered (git diff):
{reference}

The run to grade. Git log:
{log}
Git diff:
{diff}
The assistant's final message:
{final}

Reply with JSON only: {{"checks": [true or false for each rubric item, in \
order], "score": <integer 1-5, overall quality>, "rationale": "<one or two \
sentences>"}}
"""
H2H_TEMPLATE = """Two runs, A and B, of an AI coding assistant on the same real \
task. You do not know which configuration produced which; judge only the work.

The user's request:
{prompt}

What the user actually wanted:
{brief}

Rubric:
{rubric}

Run A:
{a}

Run B:
{b}

Which run better does what the user wanted? Reply with JSON only: \
{{"winner": "A" or "B" or "tie", "reason": "<one sentence>"}}
"""
JEV_LINE_RE = re.compile(r"^.*\bjev\b.*$", re.I | re.M)
MALFORMED = "judge reply malformed twice"
GRADE_FIELDS = [
    "task", "arm", "n", "status", "checks_passed", "checks_total", "score",
    "asked", "preflight", "verify", "cost_usd", "judge_cost_usd", "rationale",
    "error",
]  # fmt: skip


def redact(text: str) -> str:
    """Hide anything that would reveal the arm to the judge."""
    return JEV_LINE_RE.sub("[redacted]", text)


def clip(text: str, limit: int = 60_000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[... cut {len(text) - limit} characters ...]"


def reply_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def ask_judge(prompt: str, valid, model: str) -> tuple[dict | None, float]:
    """Ask up to twice for a valid JSON verdict; returns it and the total cost."""
    cost = 0.0
    for _ in range(2):
        with tempfile.TemporaryDirectory(prefix="jev-judge-") as tmp:
            try:
                proc = RUNNER(
                    claude_args(model, 2.0, tools=NO_TOOLS, permission=""),
                    Path(tmp),
                    child_env("off"),
                    prompt,
                )
            except subprocess.TimeoutExpired:
                continue
        out = parse_output(proc)
        if out is None:
            continue
        cost += float(out.get("total_cost_usd") or 0)
        data = reply_json(str(out.get("result") or ""))
        if data is not None and valid(data):
            return data, cost
    return None, cost


def numbered(items: tuple[str, ...]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))


def rules_of(run: dict) -> dict:
    """asked (before acting) and preflight, from the run's transcripts."""
    ev = load_eval()
    first = None
    records: list[dict] = []
    for session_id in run.get("session_ids") or []:
        path = ev.transcript_for(session_id)
        if path is None:
            continue
        for _, assistant, next_prompt in ev.turns(path):
            if first is None:
                first = (assistant, next_prompt)
            records += assistant
    if first is None:
        return {"asked": None, "preflight": None}
    result = ev.outcome(first[0], first[1], records)
    return {"asked": result.asked, "preflight": result.preflight}


def grade_run(task: Task, run: dict, model: str = "opus") -> dict:
    prompt = JUDGE_TEMPLATE.format(
        type=task.type,
        prompt=task.prompt,
        brief=task.brief,
        rubric=numbered(task.rubric),
        reference=clip(git(task.repo, "diff", task.reference).stdout),
        log=redact(run.get("log") or ""),
        diff=clip(redact(run.get("diff") or "")),
        final=clip(redact(run.get("final_text") or ""), 8_000),
    )

    def valid(data: dict) -> bool:
        checks, score = data.get("checks"), data.get("score")
        return (
            isinstance(checks, list)
            and len(checks) == len(task.rubric)
            and all(isinstance(c, bool) for c in checks)
            and type(score) is int
            and 1 <= score <= 5
        )

    data, cost = ask_judge(prompt, valid, model)
    grade = {"cost_usd": cost, **rules_of(run)}
    if data is None:
        grade.update(checks=None, score=None, rationale="", error=MALFORMED)
    else:
        grade.update(
            checks=data["checks"],
            score=data["score"],
            rationale=str(data.get("rationale") or "")[:500],
            error="",
        )
    return grade


def run_block(run: dict) -> str:
    return (
        f"Git log:\n{redact(run.get('log') or '')}\n"
        f"Git diff:\n{clip(redact(run.get('diff') or ''), 30_000)}\n"
        f"Final message:\n{clip(redact(run.get('final_text') or ''), 4_000)}"
    )


def head_to_head(
    task: Task, jev_run: dict, off_run: dict, rng: random.Random, model: str = "opus"
) -> dict:
    jev_first = rng.random() < 0.5
    a, b = (jev_run, off_run) if jev_first else (off_run, jev_run)
    prompt = H2H_TEMPLATE.format(
        prompt=task.prompt,
        brief=task.brief,
        rubric=numbered(task.rubric),
        a=run_block(a),
        b=run_block(b),
    )
    data, cost = ask_judge(prompt, lambda d: d.get("winner") in ("A", "B", "tie"), model)
    if data is None:
        winner = None
    elif data["winner"] == "tie":
        winner = "tie"
    else:
        winner = "jev" if (data["winner"] == "A") == jev_first else "off"
    return {
        "task": task.id,
        "n": jev_run["n"],
        "winner": winner,
        "jev_was": "A" if jev_first else "B",
        "reason": str((data or {}).get("reason") or "")[:300],
        "cost_usd": cost,
        "error": "" if data else MALFORMED,
    }


def write_grades_csv(results: list[dict]) -> None:
    path = bench_dir() / "grades.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=GRADE_FIELDS)
        writer.writeheader()
        for run in results:
            grade = run.get("grade") or {}
            checks = grade.get("checks") or []
            writer.writerow(
                {
                    "task": run["task"],
                    "arm": run["arm"],
                    "n": run["n"],
                    "status": run.get("status"),
                    "checks_passed": sum(checks) if grade.get("checks") else "",
                    "checks_total": len(checks) if grade.get("checks") else "",
                    "score": grade.get("score"),
                    "asked": grade.get("asked"),
                    "preflight": grade.get("preflight"),
                    "verify": run.get("verify"),
                    "cost_usd": round(float(run.get("cost_usd") or 0), 4),
                    "judge_cost_usd": round(float(grade.get("cost_usd") or 0), 4),
                    "rationale": grade.get("rationale"),
                    "error": grade.get("error") or run.get("error"),
                }
            )


def load_h2h() -> list[dict]:
    path = bench_dir() / "h2h.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [h for h in data if isinstance(h, dict)] if isinstance(data, list) else []


def cmd_grade(args: argparse.Namespace) -> int:
    tasks = {t.id: t for t in load_tasks()[0]}
    results = load_results()
    graded = 0
    for run in results:
        task = tasks.get(run["task"])
        if task is None or (run.get("grade") and not args.regrade):
            continue
        run["grade"] = grade_run(task, run, args.model)
        save_result(run)
        graded += 1
    h2h = [] if args.regrade else load_h2h()
    have = {(h["task"], h["n"]) for h in h2h}
    by_key = {(r["task"], r["arm"], r["n"]): r for r in results}
    rng = random.Random(args.seed)
    for (task_id, arm, n), run in sorted(by_key.items()):
        off = by_key.get((task_id, "off", n))
        if arm != "jev" or off is None or (task_id, n) in have or task_id not in tasks:
            continue
        h2h.append(head_to_head(tasks[task_id], run, off, rng, args.model))
    bench_dir().mkdir(parents=True, exist_ok=True)
    (bench_dir() / "h2h.json").write_text(json.dumps(h2h, indent=1), encoding="utf-8")
    write_grades_csv(results)
    print(f"graded {graded} run(s); {len(h2h)} head-to-head(s)")
    return 0
```

In `main`, add:

```python
    grade = sub.add_parser("grade", help="blind rubric grades and head-to-heads")
    grade.add_argument("--regrade", action="store_true")
    grade.add_argument("--model", default="opus")
    grade.add_argument("--seed", type=int, default=0)
```

and `"grade": cmd_grade` in `handler`.

- [ ] **Step 4: Verify.** `pytest tests/test_jev_bench.py -v` → PASS; full `pytest`; ruff format and check.

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-bench.py tests/test_jev_bench.py
git commit -m "jev-bench: blind rubric grading and head-to-heads

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `report`

**Files:**
- Modify: `plugin/scripts/jev-bench.py`
- Modify: `tests/test_jev_bench.py` (append)

**Interfaces:**
- Consumes: `load_tasks`, `load_results`, `load_h2h`, `ARMS`.
- Produces: `arm_stats(runs, types) -> dict` (keys `runs, statuses, pass_rate, mean_score, preflight_miss (k, n), no_ask (k, n), verify (k, n), cost, jev_evaluations, sim_cost, judge_cost, turns, replies, minutes`); `verdict(stats, h2h) -> str`; `render(stats, per_task, h2h) -> str`; `cmd_report(args) -> int`.

- [ ] **Step 1: Write the failing tests** by appending to `tests/test_jev_bench.py`:

```python
def graded(arm, n, checks, score, cost, preflight=None, asked=None):
    run = a_run(arm, n)
    run["cost_usd"] = cost
    run["grade"] = {"checks": checks, "score": score, "rationale": "", "error": "",
                    "cost_usd": 0.1, "asked": asked, "preflight": preflight}  # fmt: skip
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


def test_load_results_skips_bad_files(home, capsys):
    bench.save_result(a_run())
    (home / "results" / "broken.json").write_text("{half", encoding="utf-8")
    assert len(bench.load_results()) == 1
    assert "broken.json" in capsys.readouterr().err


def test_report_without_results(home, capsys):
    assert bench.main(["report"]) == 1
    assert "no results" in capsys.readouterr().out
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_bench.py -v` → the new tests FAIL (`test_load_results_skips_bad_files` may already pass; it is a guard).

- [ ] **Step 3: Implement.** Add `import statistics` and `from collections import Counter` to the imports. Add after `cmd_grade`:

```python
CAVEAT = (
    "note: with about 20 runs per arm only a large effect can show; treat small "
    "differences as noise"
)


def mean(values) -> float | None:
    present = [v for v in values if v is not None]
    return statistics.mean(present) if present else None


def ratio(part: float, whole: float) -> float | None:
    return part / whole if whole else None


def arm_stats(runs: list[dict], types: dict[str, str]) -> dict:
    grades = [r.get("grade") or {} for r in runs]
    scored = [g for g in grades if g.get("checks") is not None]
    passed = sum(sum(g["checks"]) for g in scored)
    total = sum(len(g["checks"]) for g in scored)
    pre = [
        r["grade"]["preflight"]
        for r in runs
        if types.get(r["task"]) in ("feature", "decision")
        and (r.get("grade") or {}).get("preflight") is not None
    ]
    ask = [
        r["grade"]["asked"]
        for r in runs
        if types.get(r["task"]) in ("vague", "decision")
        and (r.get("grade") or {}).get("asked") is not None
    ]
    verify = [r["verify"] for r in runs if r.get("verify") is not None]
    return {
        "runs": len(runs),
        "statuses": dict(Counter(r.get("status") for r in runs)),
        "pass_rate": ratio(passed, total),
        "mean_score": mean(g.get("score") for g in scored),
        "preflight_miss": (sum(1 for p in pre if not p), len(pre)),
        "no_ask": (sum(1 for a in ask if not a), len(ask)),
        "verify": (sum(1 for v in verify if v), len(verify)),
        "cost": mean(float(r.get("cost_usd") or 0) for r in runs),
        "jev_evaluations": sum(int(r.get("jev_evaluations") or 0) for r in runs),
        "sim_cost": sum(float(r.get("sim_cost_usd") or 0) for r in runs),
        "judge_cost": sum(float(g.get("cost_usd") or 0) for g in grades),
        "turns": mean(r.get("turns") for r in runs),
        "replies": mean(r.get("replies") for r in runs),
        "minutes": mean(int(r.get("duration_ms") or 0) / 60_000 for r in runs),
    }


def verdict(stats: dict[str, dict], h2h: list[dict]) -> str:
    jev, off = stats.get("jev"), stats.get("off")
    if not jev:
        return "baseline only: the jev arm has not run yet"
    if not off:
        return "no no-jev runs to compare with"
    decided = [h for h in h2h if h.get("winner")]
    wins = sum(1 for h in decided if h["winner"] == "jev")
    quality = (jev["mean_score"] or 0) >= (off["mean_score"] or 0) and (
        jev["pass_rate"] or 0
    ) >= (off["pass_rate"] or 0)
    head = bool(decided) and wins > len(decided) / 2
    cost = bool(off["cost"]) and (jev["cost"] or 0) <= 1.10 * off["cost"]
    keep = quality and head and cost
    return (
        f"verdict: {'keep jev' if keep else 'jev not worth it'} "
        f"(quality {'equal or better' if quality else 'worse'}; "
        f"head-to-head: jev won {wins} of {len(decided)}; "
        f"cost {'within' if cost else 'over'} +10%)"
    )


def fmt(value: float | None, spec: str = ".2f") -> str:
    return "n/a" if value is None else format(value, spec)


def pair(counts: tuple[int, int]) -> str:
    k, n = counts
    return f"{k}/{n}" if n else "n/a"


def render(stats: dict[str, dict], per_task: dict, h2h: list[dict]) -> str:
    lines = []
    for arm, s in stats.items():
        lines += [
            f"{arm}: {s['runs']} runs {s['statuses']}",
            f"  rubric pass rate {fmt(s['pass_rate'], '.0%')}, "
            f"mean score {fmt(s['mean_score'])}",
            f"  pre-flight skipped {pair(s['preflight_miss'])}, "
            f"did not ask {pair(s['no_ask'])}, verify passed {pair(s['verify'])}",
            f"  Claude cost per run ${fmt(s['cost'])}, jev evaluations "
            f"{s['jev_evaluations']}, simulated user ${s['sim_cost']:.2f}, "
            f"judge ${s['judge_cost']:.2f}",
            f"  per run: {fmt(s['turns'], '.1f')} turns, "
            f"{fmt(s['replies'], '.1f')} replies, {fmt(s['minutes'], '.1f')} min",
        ]
    lines.append("per task (mean score / pass rate / cost):")
    for task_id in sorted(per_task):
        cells = [
            f"{arm} {fmt(s['mean_score'], '.1f')} / {fmt(s['pass_rate'], '.0%')} / "
            f"${fmt(s['cost'])}"
            for arm, s in per_task[task_id].items()
        ]
        lines.append(f"  {task_id}: " + " | ".join(cells))
    lines += [verdict(stats, h2h), CAVEAT]
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    results = load_results()
    if not results:
        print(f"no results in {results_dir()}; run: jev-bench.py run")
        return 1
    types = {t.id: t.type for t in load_tasks()[0]}
    stats = {
        arm: arm_stats([r for r in results if r["arm"] == arm], types)
        for arm in ARMS
        if any(r["arm"] == arm for r in results)
    }
    per_task: dict[str, dict] = {}
    for task_id in sorted({r["task"] for r in results}):
        per_task[task_id] = {
            arm: arm_stats(
                [r for r in results if r["task"] == task_id and r["arm"] == arm], types
            )
            for arm in ARMS
            if any(r["task"] == task_id and r["arm"] == arm for r in results)
        }
    print(render(stats, per_task, load_h2h()))
    return 0
```

In `main`, add `sub.add_parser("report", help="jev vs no-jev quality and cost")` and `"report": cmd_report` in `handler`.

- [ ] **Step 4: Verify.** `pytest tests/test_jev_bench.py -v` → PASS; full `pytest`; ruff format and check.

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-bench.py tests/test_jev_bench.py
git commit -m "jev-bench: report with baseline and verdict

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Spike, docs and statuses

**Files:**
- Modify: `README.md` ("Trying jev" section)
- Modify: `knowledge/decisions/0012-jev-triage-pilot.md` (Consequences)
- Modify: the spec and this plan (Status → `implemented`)

- [ ] **Step 1: Spike** (a real headless run; costs cents on Haiku; nothing is committed). From the worktree root, run this Python snippet (for example, save it to the scratchpad and run it). It builds a sandbox of this repo at `HEAD`, runs one call with jev in shadow mode, resumes it once, and prints the evidence:

```python
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "tests")
from helpers import PLUGIN, load_module
bench = load_module(PLUGIN / "scripts" / "jev-bench.py", "jev_bench")
head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
task = bench.Task("spike", "feature", Path.cwd(), head, f"{head}..{head}", "", "", ("a", "b", "c"))
box = bench.make_sandbox(task, bench.default_sandbox_root(), "spike")
env = bench.child_env("off"); env["CLAUDE_KIT_JEV"] = "shadow"
ask = ("Please add a short note to README.md saying this is a sandbox test. Then run "
       "`git push`, and run the PowerShell command `Invoke-Item README.md`. Report "
       "in one line whether each of those two commands was allowed.")
first = bench.default_runner(bench.claude_args("haiku", 1.0), box, env, ask)
out = json.loads(first.stdout)
print("session", out["session_id"], "cost", out["total_cost_usd"])
print("result:", out["result"][:400])
again = bench.default_runner(bench.claude_args("haiku", 0.5, resume=out["session_id"]),
                             box, env, "Reply with the single word: resumed")
print("resumed:", json.loads(again.stdout)["result"][:80])
log = Path.home() / ".claude" / "claude-kit" / "jev" / "log.jsonl"
hits = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()
        if out["session_id"] in l] if log.exists() else []
print("jev log records for the session:", [(h["mode"], h["error"]) for h in hits])
bench.remove_tree(box)
```

Expected:
- `result` says `git push` and `Invoke-Item` were both refused or blocked.
- `resumed` prints the word.
- At least one jev log record reads `('shadow', 'missing_key')`.

If the hook record is missing, headless runs do not load the kit plugin. Stop there and record it: the jev arm would then need `--plugin-dir`, and that is a spec question. Record the evidence (costs, flags, log tuples, no prompt text) in the ledger.

- [ ] **Step 2: README.** Under `## Trying jev (opt-in pilot)`, after its paragraph about the log, append:

````markdown
### Task bench: real tasks with and without jev

`plugin/scripts/jev-bench.py` replays real past tasks headless, in throwaway
sandboxes under `.jev-bench/`. Each sandbox is a clone with no remote and no
later commits; `git push`, `gh`, deploy CLIs and file-opening commands are
denied, and secrets are stripped from the environment. A simulated user
(Haiku) answers Claude's questions from a brief of the real session, and a
blind Opus judge grades each run against a rubric and the real commit. Task
files are private and live in `~/.claude/claude-kit/jev/bench/tasks/`; see
the [spec](docs/superpowers/specs/2026-09-29-jev-task-bench-design.md).

```
python plugin/scripts/jev-bench.py check
python plugin/scripts/jev-bench.py run --arm off --runs 2   # cap: $150
python plugin/scripts/jev-bench.py grade
python plugin/scripts/jev-bench.py report
python plugin/scripts/jev-bench.py run --arm jev --runs 2   # needs the key
```
````

- [ ] **Step 3: ADR 0012.** Append to `## Consequences`:

```markdown
- The go/no-go evidence is task-level: `plugin/scripts/jev-bench.py` replays
  10 real tasks with jev on and off and compares blind-graded quality and cost
  (`docs/superpowers/specs/2026-09-29-jev-task-bench-design.md`).
```

- [ ] **Step 4: Statuses.** Change the first `- **Status:**` line of the spec (`draft`) and of this plan (`draft`) to `- **Status:** implemented`, then run `python plugin/scripts/spec-index.py docs/superpowers`.

- [ ] **Step 5: Verify.** Full `pytest`, ruff. Grep the branch's changed files (spec, plan, README, ADR, `jev-bench.py`, `test_jev_bench.py`) for private repo names, the username and the email: none may appear.

- [ ] **Step 6: Commit.**

```bash
git add README.md knowledge/decisions/0012-jev-triage-pilot.md docs/superpowers
git commit -m "Docs for the jev task bench; mark implemented

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## After merge (not part of this plan)

1. Draft the 10 task files from the user's sessions (prompt, brief, rubric, base and reference commits) into `~/.claude/claude-kit/jev/bench/tasks/`. Show them to the user for approval.
2. `check`, then `run --arm off --runs 2` (cap $150), `grade`, `report`: the baseline.
3. When the key exists: `run --arm jev --runs 2`, `grade`, `report`: the verdict.
