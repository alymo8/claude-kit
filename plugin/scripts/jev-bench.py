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
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
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
    prompt = SIM_TEMPLATE.format(
        brief=task.brief, prompt=task.prompt, last=last[-8000:]
    )
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


def converse(
    task: Task,
    record: dict,
    sandbox: Path,
    env: dict[str, str],
    model: str,
    budget: float,
    max_replies: int,
) -> None:
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
    text = json.dumps(record, ensure_ascii=False, indent=1)
    path.write_text(text, encoding="utf-8")


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
                if spent + args.budget > args.max_total_usd:
                    cap = f"${args.max_total_usd:.0f}"
                    print(f"stopping: the next run could pass the {cap} cap"
                          f" (spent ${spent:.2f})")  # fmt: skip
                    return 1
                print(f"run {task.id}-{arm}-{n}", flush=True)
                record = run_one(
                    task, arm, n, root, args.model, args.budget, MAX_REPLIES, args.keep
                )
                save_result(record)
                spent += record["cost_usd"] + record["sim_cost_usd"]
                ran += 1
                print(
                    f"  {record['status']} ${record['cost_usd']:.2f}"
                    f" {record['turns']} turns {record['replies']} replies",
                    flush=True,
                )
    print(f"{ran} run(s), ${spent:.2f} spent")
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
    args = parser.parse_args(argv)
    handler = {"check": cmd_check, "run": cmd_run}
    return handler[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
