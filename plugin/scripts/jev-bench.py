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
    parser = argparse.ArgumentParser(
        description="Replay real tasks with and without jev."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate task files and prerequisites")
    check.add_argument("--arm", choices=(*ARMS, "both"), default="off")
    args = parser.parse_args(argv)
    handler = {"check": cmd_check}
    return handler[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
