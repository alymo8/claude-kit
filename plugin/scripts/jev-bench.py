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
import csv
import importlib.util
import json
import os
import random
import re
import shutil
import signal
import stat
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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


SECRET_RE = re.compile(
    r"TOKEN|SECRET|PASSWORD|PASSWD|KEY|SUPABASE|AZURE|AWS|GH_|GITHUB|CREDENTIAL"
    r"|AUTH|PRIVATE|DSN|PAT$|_URI$|_URL$",
    re.I,
)
KEEP_PREFIXES = ("ANTHROPIC_", "CLAUDE_")
# Nothing may leave the machine or pop up on the user's screen. Prefix rules
# are easy to route around, so the real guards are elsewhere: no remote, no git
# credentials, pushes rewritten to an invalid URL (child_env), and GUARD.
_BLOCKED = (
    "git push",
    "gh",
    "supabase",
    "npx supabase",
    "pnpm dlx supabase",
    "bunx supabase",
    "az",
    "vercel",
    "npx vercel",
    "pnpm dlx vercel",
    "bunx vercel",
    "explorer",
    "explorer.exe",
    "start",
    "cmd",
    "cmd.exe",
    "powershell",
    "pwsh",
)
DENIED = (
    *(f"Bash({command}:*)" for command in _BLOCKED),
    *(f"PowerShell({command}:*)" for command in _BLOCKED),
    "PowerShell(Invoke-Item:*)",
    "PowerShell(ii:*)",
    "PowerShell(Start-Process:*)",
)
GUARD = (
    "You are working in a disposable copy of this repository. Keep every read "
    "and write inside the current directory: do not read, copy or modify files "
    "outside it (sibling repositories and their .env files included). Do not "
    "push, deploy, publish, or open windows or browsers. Otherwise work exactly "
    "as you normally would."
)
EMPTY_DIR = Path(tempfile.gettempdir()) / "jev-bench-empty"
# Pushes go nowhere and git can use no stored credentials.
GIT_CONFIG = (
    ("credential.helper", ""),
    ("url.https://invalid.invalid/.pushInsteadOf", "https://"),
    ("url.https://invalid.invalid/.pushInsteadOf", "git@"),
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
    EMPTY_DIR.mkdir(parents=True, exist_ok=True)
    # GIT_CONFIG_PARAMETERS is what `git -c` uses; GIT_CONFIG_COUNT with an
    # empty value does not reach git on Windows.
    env["GIT_CONFIG_PARAMETERS"] = " ".join(f"'{k}={v}'" for k, v in GIT_CONFIG)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "Never"
    env["GH_CONFIG_DIR"] = str(EMPTY_DIR)
    env["NPM_CONFIG_USERCONFIG"] = str(EMPTY_DIR / "npmrc")
    return env


def claude_args(
    model: str,
    budget: float,
    resume: str | None = None,
    tools: tuple[str, ...] = DENIED,
    permission: str = "bypassPermissions",
    system: str = "",
) -> list[str]:
    """argv for one headless call; the prompt goes on stdin. MCP servers and
    connectors are off (--strict-mcp-config with no --mcp-config)."""
    argv = [
        claude_bin() or "claude",
        "-p",
        "--model",
        model,
        "--output-format",
        "json",
        "--max-budget-usd",
        f"{budget:.2f}",
        "--strict-mcp-config",
    ]
    if permission:
        argv += ["--permission-mode", permission]
    if system:
        argv += ["--append-system-prompt", system]
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


def _git_or_raise(repo: Path, *args: str) -> None:
    out = git(repo, *args)
    if out.returncode:
        raise RuntimeError(f"sandbox: git {args[0]} failed: {out.stderr.strip()}")


def make_sandbox(task: Task, root: Path, name: str) -> Path:
    """A clone at base_commit with no remote and no later commits or tags."""
    dest = root / name
    remove_tree(dest)
    root.mkdir(parents=True, exist_ok=True)
    clone = subprocess.run(
        ["git", "clone", "--quiet", "--no-local", "--no-checkout", str(task.repo)]
        + [str(dest)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if clone.returncode:
        raise RuntimeError(f"sandbox: git clone failed: {clone.stderr.strip()}")
    _git_or_raise(dest, "checkout", "--quiet", "-B", "main", task.base_commit)
    _git_or_raise(dest, "remote", "remove", "origin")
    for ref in git(dest, "for-each-ref", "--format=%(refname)").stdout.split():
        if ref != "refs/heads/main":
            _git_or_raise(dest, "update-ref", "-d", ref)
    _git_or_raise(dest, "reflog", "expire", "--expire=now", "--all")
    _git_or_raise(dest, "gc", "--quiet", "--prune=now")
    return dest


CALL_TIMEOUT_S = 3600
SIDE_TIMEOUT_S = 300  # simulated user and judge
MIN_CALL_BUDGET = 0.5
MAX_REPLIES = 6
SIM_USD = 1.0  # cap per simulated-user reply
Runner = Callable[..., subprocess.CompletedProcess]


def kill_tree(proc: subprocess.Popen) -> None:
    """Kill the process and everything it started (dev servers, test runners)."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True
        )
    else:  # pragma: no cover - POSIX
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def default_runner(
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    stdin: str,
    timeout: float = CALL_TIMEOUT_S,
) -> subprocess.CompletedProcess:
    """Run one call. Output goes to temporary files, not pipes, so orphaned
    grandchildren cannot block us; on timeout the whole tree is killed."""
    group = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=out,
            stderr=err,
            **group,
        )
        try:
            proc.communicate(stdin.encode("utf-8"), timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(proc)
            proc.wait(timeout=30)
            raise subprocess.TimeoutExpired(argv, timeout) from None
        out.seek(0)
        err.seek(0)
        stdout = out.read().decode("utf-8", "replace")
        stderr = err.read().decode("utf-8", "replace")
    return subprocess.CompletedProcess(argv, proc.returncode, stdout, stderr)


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
    prompt = SIM_TEMPLATE.format(
        brief=task.brief, prompt=task.prompt, last=last[-8000:]
    )
    with tempfile.TemporaryDirectory(prefix="jev-sim-") as tmp:
        try:
            proc = RUNNER(
                claude_args("haiku", SIM_USD, tools=NO_TOOLS, permission=""),
                Path(tmp),
                child_env("off"),
                prompt,
                timeout=SIDE_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return None
    out = parse_output(proc)
    if out is None:
        return None
    return str(out.get("result") or ""), float(out.get("total_cost_usd") or 0)


# Nested worktrees are diffed on their own; the rest is kit-hook noise.
NOISE = (
    ":(exclude).claude/worktrees",
    ":(exclude).worktrees",
    ":(exclude).claude/handoffs",
    ":(exclude)docs/superpowers/README.md",
)


def worktrees(sandbox: Path) -> list[tuple[Path, str]]:
    """(path, branch) of every worktree of the sandbox repo, main first."""
    found: list[tuple[Path, str]] = []
    path = None
    listing = git(sandbox, "worktree", "list", "--porcelain").stdout
    for line in listing.splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree ") :])
        elif path is not None and line.startswith("branch "):
            found.append((path, line[len("branch ") :].removeprefix("refs/heads/")))
        elif path is not None and line == "detached":
            found.append((path, "detached"))
    return found or [(sandbox, "main")]


def sandbox_changes(sandbox: Path, base: str) -> tuple[str, str]:
    """Diff against base of every worktree (untracked files included), and the
    log of every branch. The workflow builds features in worktrees, so the main
    tree alone would miss the work."""
    sections = []
    for tree, branch in worktrees(sandbox):
        git(tree, "add", "-A", "--intent-to-add", "--", ".", *NOISE)
        diff = git(tree, "diff", base, "--", ".", *NOISE).stdout
        if diff.strip():
            sections.append(f"### worktree: {branch}\n{diff}")
    log = git(sandbox, "log", "--oneline", "--branches", "--not", base).stdout
    return "\n".join(sections), log


def drop_outside_worktrees(sandbox: Path) -> None:
    """Remove worktrees the run created outside the sandbox, if any."""
    inside = sandbox.resolve()
    for tree, _ in worktrees(sandbox):
        if tree.resolve() != inside and inside not in tree.resolve().parents:
            git(sandbox, "worktree", "remove", "--force", str(tree))


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
        "uncounted_usd": 0.0,
        "cleanup_error": "",
        "session_costs": {},
        "session_turns": {},
        "started": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def converse(
    task: Task,
    record: dict,
    sandbox: Path,
    env: dict[str, str],
    model: str,
    budget: float,
    max_replies: int,
) -> None:
    """Claude and the simulated user take turns until a stop rule fires.

    claude -p reports total_cost_usd and num_turns cumulatively for the session
    (a --resume included), so each session counts once, at its latest value,
    and --max-budget-usd gets the budget minus what other sessions spent."""
    prompt, session = task.prompt, None
    costs, turns = record["session_costs"], record["session_turns"]
    while True:
        cap = budget - (record["cost_usd"] - costs.get(session, 0.0))
        if cap - costs.get(session, 0.0) < MIN_CALL_BUDGET:
            record["status"] = "budget"
            return
        start = time.perf_counter()
        try:
            proc = RUNNER(
                claude_args(model, cap, session, system=GUARD), sandbox, env, prompt
            )
        except subprocess.TimeoutExpired:
            record["error"] = "claude call timed out"
            record["uncounted_usd"] = cap - costs.get(session, 0.0)
            return
        finally:
            record["duration_ms"] += round((time.perf_counter() - start) * 1000)
        out = parse_output(proc)
        if out is None:
            tail = (proc.stderr or proc.stdout or "")[-500:]
            record["error"] = f"claude exited {proc.returncode}: {tail}"
            record["uncounted_usd"] = cap - costs.get(session, 0.0)
            return
        session = str(out["session_id"])
        if session not in record["session_ids"]:
            record["session_ids"].append(session)
        costs[session] = max(costs.get(session, 0.0), float(out["total_cost_usd"] or 0))
        turns[session] = max(turns.get(session, 0), int(out.get("num_turns") or 0))
        record["cost_usd"] = sum(costs.values())
        record["turns"] = sum(turns.values())
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
        try:
            converse(task, record, sandbox, env, model, budget, max_replies)
        except Exception as exc:  # a harness bug must not lose the record
            record["status"] = "error"
            record["error"] = f"harness error: {exc}"
        record["diff"], record["log"] = sandbox_changes(sandbox, task.base_commit)
        if task.verify:
            record["verify"] = run_verify(task.verify, sandbox, env)
    except Exception as exc:
        record["error"] = record["error"] or f"harness error: {exc}"
    finally:
        try:
            drop_outside_worktrees(sandbox)
            if not keep:
                remove_tree(sandbox)
        except OSError as exc:  # e.g. files still locked on Windows
            record["cleanup_error"] = f"sandbox not removed: {sandbox}: {exc}"
    record["jev_evaluations"] = count_jev(record["session_ids"])
    return record


def results_dir() -> Path:
    return bench_dir() / "results"


def save_result(record: dict) -> None:
    path = results_dir() / f"{record['task']}-{record['arm']}-{record['n']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record, ensure_ascii=False, indent=1)
    path.write_text(text, encoding="utf-8")


def sane(record: object) -> bool:
    """A result file with the fields and types report and grade rely on."""
    if not isinstance(record, dict) or not {"task", "arm", "n"} <= set(record):
        return False
    try:
        for key in ("cost_usd", "sim_cost_usd", "uncounted_usd"):
            float(record.get(key) or 0)
        for key in ("turns", "replies", "duration_ms", "jev_evaluations"):
            int(record.get(key) or 0)
        grade = record.get("grade")
        if grade is None:
            return True
        if not isinstance(grade, dict):
            return False
        float(grade.get("cost_usd") or 0)
    except (TypeError, ValueError):
        return False
    checks = grade.get("checks")
    return checks is None or (
        isinstance(checks, list) and all(isinstance(c, bool) for c in checks)
    )


def load_results() -> list[dict]:
    records = []
    for path in sorted(results_dir().glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print(f"skipping unreadable {path.name}", file=sys.stderr)
            continue
        if sane(record):
            records.append(record)
        else:
            print(f"skipping malformed {path.name}", file=sys.stderr)
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
    done = set()
    if not args.force:
        done = {(r["task"], r["arm"], r["n"]) for r in load_results()}
    root = Path(args.sandbox_root) if args.sandbox_root else default_sandbox_root()
    spent, ran = 0.0, 0
    for task in tasks:
        for n in range(1, args.runs + 1):
            for arm in arms:
                if (task.id, arm, n) in done:
                    continue
                reserve = args.budget + MAX_REPLIES * SIM_USD
                if spent + reserve > args.max_total_usd:
                    cap = f"${args.max_total_usd:.0f}"
                    print(f"stopping: the next run could pass the {cap} cap"
                          f" (spent ${spent:.2f})")  # fmt: skip
                    return 1
                print(f"run {task.id}-{arm}-{n}", flush=True)
                record = run_one(
                    task, arm, n, root, args.model, args.budget, MAX_REPLIES, args.keep
                )
                save_result(record)
                # a crashed or timed-out call may have spent up to its cap
                spent += (
                    record["cost_usd"]
                    + record["sim_cost_usd"]
                    + record["uncounted_usd"]
                )
                ran += 1
                print(
                    f"  {record['status']} ${record['cost_usd']:.2f}"
                    f" {record['turns']} turns {record['replies']} replies",
                    flush=True,
                )
    print(f"{ran} run(s), ${spent:.2f} spent")
    return 0


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
# Lines that could reveal the arm: jev, its hints, or Claude paraphrasing them.
ARM_LINE_RE = re.compile(
    r"^.*(\bjev\b|triage|typesafe|looks underspecified|pre-flight branch check"
    r"|hinge on a key decision).*(\n|$)",
    re.I | re.M,
)
MALFORMED = "judge reply malformed twice"
GRADE_FIELDS = [
    "task",
    "arm",
    "n",
    "status",
    "checks_passed",
    "checks_total",
    "score",
    "asked",
    "preflight",
    "verify",
    "cost_usd",
    "judge_cost_usd",
    "rationale",
    "error",
]


def redact(text: str) -> str:
    """Drop lines that would reveal the arm, silently: a marker would itself
    appear almost only in the jev arm. Applied to both arms alike."""
    return ARM_LINE_RE.sub("", text)


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
                    timeout=SIDE_TIMEOUT_S,
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
    data, cost = ask_judge(
        prompt, lambda d: d.get("winner") in ("A", "B", "tie"), model
    )
    if data is None:
        winner = None
    elif data["winner"] == "tie":
        winner = "tie"
    else:
        winner = "jev" if (data["winner"] == "A") == jev_first else "off"
    return {
        "task": task.id,
        "n": jev_run["n"],
        "runs": run_pair_key(jev_run, off_run),
        "winner": winner,
        "jev_was": "A" if jev_first else "B",
        "reason": str((data or {}).get("reason") or "")[:300],
        "cost_usd": cost,
        "error": "" if data else MALFORMED,
    }


def grade_row(run: dict) -> dict:
    grade = run.get("grade") or {}
    checks = grade.get("checks")
    return {
        "task": run["task"],
        "arm": run["arm"],
        "n": run["n"],
        "status": run.get("status"),
        "checks_passed": sum(checks) if checks else "",
        "checks_total": len(checks) if checks else "",
        "score": grade.get("score"),
        "asked": grade.get("asked"),
        "preflight": grade.get("preflight"),
        "verify": run.get("verify"),
        "cost_usd": round(float(run.get("cost_usd") or 0), 4),
        "judge_cost_usd": round(float(grade.get("cost_usd") or 0), 4),
        "rationale": grade.get("rationale"),
        "error": grade.get("error") or run.get("error"),
    }


def write_grades_csv(results: list[dict]) -> None:
    path = bench_dir() / "grades.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=GRADE_FIELDS)
        writer.writeheader()
        writer.writerows(grade_row(run) for run in results)


def run_pair_key(jev_run: dict, off_run: dict) -> str:
    """Identifies the exact two runs compared; a redone run changes it."""
    return f"{jev_run.get('started', '')}|{off_run.get('started', '')}"


def load_h2h() -> list[dict]:
    path = bench_dir() / "h2h.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [h for h in data if isinstance(h, dict) and {"task", "n"} <= set(h)]


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
    by_key = {(r["task"], r["arm"], r["n"]): r for r in results}

    def current(h: dict) -> bool:
        jev_run = by_key.get((h["task"], "jev", h["n"]))
        off_run = by_key.get((h["task"], "off", h["n"]))
        return bool(jev_run and off_run) and h.get("runs") == run_pair_key(
            jev_run, off_run
        )

    h2h = [] if args.regrade else [h for h in load_h2h() if current(h)]
    have = {(h["task"], h["n"]) for h in h2h}
    rng = random.Random(args.seed)
    for (task_id, arm, n), run in sorted(by_key.items()):
        off = by_key.get((task_id, "off", n))
        if arm != "jev" or off is None or (task_id, n) in have:
            continue
        if task_id in tasks:
            h2h.append(head_to_head(tasks[task_id], run, off, rng, args.model))
    bench_dir().mkdir(parents=True, exist_ok=True)
    (bench_dir() / "h2h.json").write_text(json.dumps(h2h, indent=1), encoding="utf-8")
    write_grades_csv(results)
    print(f"graded {graded} run(s); {len(h2h)} head-to-head(s)")
    return 0


CAVEAT = (
    "note: with about 20 runs per arm only a large effect can show; treat small "
    "differences as noise"
)


def mean(values) -> float | None:
    present = [v for v in values if v is not None]
    return statistics.mean(present) if present else None


def ratio(part: float, whole: float) -> float | None:
    return part / whole if whole else None


def rule_values(runs: list[dict], types: dict[str, str], key: str, kinds) -> list:
    return [
        r["grade"][key]
        for r in runs
        if types.get(r["task"]) in kinds and (r.get("grade") or {}).get(key) is not None
    ]


def arm_stats(runs: list[dict], types: dict[str, str]) -> dict:
    grades = [r.get("grade") or {} for r in runs]
    scored = [g for g in grades if g.get("checks") is not None]
    passed = sum(sum(g["checks"]) for g in scored)
    total = sum(len(g["checks"]) for g in scored)
    pre = rule_values(runs, types, "preflight", ("feature", "decision"))
    ask = rule_values(runs, types, "asked", ("vague", "decision"))
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


def wins_ties_losses(h2h: list[dict]) -> str:
    counts = Counter(h.get("winner") for h in h2h)
    return f"{counts['jev']} / {counts['tie']} / {counts['off']}"


def render(stats: dict[str, dict], per_task: dict, h2h: list[dict]) -> str:
    lines = []
    for arm, s in stats.items():
        runs = s["runs"] or 1
        lines += [
            f"{arm}: {s['runs']} runs {s['statuses']}",
            f"  rubric pass rate {fmt(s['pass_rate'], '.0%')}, "
            f"mean score {fmt(s['mean_score'])}",
            f"  pre-flight skipped {pair(s['preflight_miss'])}, "
            f"did not ask {pair(s['no_ask'])}, verify passed {pair(s['verify'])}",
            f"  cost: Claude ${fmt(s['cost'])}/run, simulated user "
            f"${s['sim_cost'] / runs:.2f}/run, judge ${s['judge_cost'] / runs:.2f}"
            f"/run; jev evaluations {s['jev_evaluations']} in total",
            f"  per run: {fmt(s['turns'], '.1f')} turns, "
            f"{fmt(s['replies'], '.1f')} replies, {fmt(s['minutes'], '.1f')} min",
        ]
    if h2h:
        lines.append(f"head-to-head, jev wins / ties / losses: {wins_ties_losses(h2h)}")
    lines.append("per task (arm: mean score / pass rate / cost per run):")
    for task_id in sorted(per_task):
        cells = [
            f"{arm} {fmt(s['mean_score'], '.1f')} / {fmt(s['pass_rate'], '.0%')} / "
            f"${fmt(s['cost'])}"
            for arm, s in per_task[task_id].items()
        ]
        task_h2h = [h for h in h2h if h.get("task") == task_id]
        if task_h2h:
            cells.append(f"h2h {wins_ties_losses(task_h2h)}")
        lines.append(f"  {task_id}: " + " | ".join(cells))
    lines += [verdict(stats, h2h), CAVEAT]
    return "\n".join(lines)


def by_arm(runs: list[dict], types: dict[str, str]) -> dict[str, dict]:
    return {
        arm: arm_stats([r for r in runs if r["arm"] == arm], types)
        for arm in ARMS
        if any(r["arm"] == arm for r in runs)
    }


def cmd_report(args: argparse.Namespace) -> int:
    results = load_results()
    if not results:
        print(f"no results in {results_dir()}; run: jev-bench.py run")
        return 1
    types = {t.id: t.type for t in load_tasks()[0]}
    per_task = {
        task_id: by_arm([r for r in results if r["task"] == task_id], types)
        for task_id in sorted({r["task"] for r in results})
    }
    print(render(by_arm(results, types), per_task, load_h2h()))
    return 0


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
    parser = argparse.ArgumentParser(
        description="Replay real tasks with and without jev."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate task files and prerequisites")
    check.add_argument("--arm", choices=(*ARMS, "both"), default="off")
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
    grade = sub.add_parser("grade", help="blind rubric grades and head-to-heads")
    grade.add_argument("--regrade", action="store_true")
    grade.add_argument("--model", default="opus")
    grade.add_argument("--seed", type=int, default=0)
    sub.add_parser("report", help="jev vs no-jev quality and cost")
    args = parser.parse_args(argv)
    handler = {
        "check": cmd_check,
        "run": cmd_run,
        "grade": cmd_grade,
        "report": cmd_report,
    }
    return handler[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
