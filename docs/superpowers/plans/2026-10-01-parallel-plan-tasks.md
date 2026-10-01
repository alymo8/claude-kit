# Parallel Plan Tasks Implementation Plan

- **Status:** implemented
- **Date:** 2026-10-01

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a plan's independent tasks as concurrent subagents in waves:
a `**Depends on:**` task line checked by `spec-lint.py` (`P10-depends`), a
`parallel-plan.py waves` command, a `parallel-tasks` skill, and `/ship` wiring.

**Architecture:** `spec-lint.py` gains the `**Depends on:**` parser and the
`P10-depends` plan rule. A new stdlib script `plugin/scripts/parallel-plan.py`
loads `spec-lint.py` with `importlib`, reuses its fence-aware parser and task
splitter, adds the path and overlap helpers, and prints waves as JSON. A new
skill runs each wave with one subagent per task in its own worktree and merges
the task branches back with `--no-ff`. `/ship` step 3 adds the lines, step 4
picks the skill when a wave holds more than one task, and a repo-wide git lock
retry rule covers concurrent worktrees.

**Tech Stack:** Python 3.11+ standard library, pytest, ruff, Markdown skill
and command files.

**Spec:** `docs/superpowers/specs/2026-09-30-parallel-plan-tasks-design.md`

## Context for a cold start

- Work in the feature worktree on branch `feat/parallel-plan-tasks`, never in
  the main checkout. The plan gate (PR #19) is already merged: `spec-lint.py`
  has a plan mode (`lint_plan`, `task_spans`, `FILES_RE`, `SPAN_RE`, `parse`).
- Full suite: `pytest`. Lint: `ruff check plugin tests; ruff format --check plugin tests`.
  Run `ruff format plugin tests` first. Ruff enforces E501 (88 columns) and
  does not wrap long string literals, so split them by hand. Baseline: 309
  passed (about 140 s on this machine; subprocess tests take about 1 s each).
- Tests load scripts with `helpers.load_module(path, name)` and run them with
  `helpers.run_script(script, *args)`; `helpers.PLUGIN` and `helpers.REPO`
  point at `plugin/` and the repo root.
- Plan-rule tests in `tests/test_spec_lint.py` use the `PLAN` fixture (49
  lines; Task 1 heading on line 10, its first step on line 17; Task 2 heading
  on line 35, its first step `- [ ] **Step 1: Check it**` on line 40; last
  line `Done.` on line 49) and the helpers `plan_root(root)` and
  `plan_rules(text, root)`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Global Constraints

- Standard library only in `parallel-plan.py`.
- `parallel-plan.py waves` exit codes: 0 success, 1 invalid plan (one stderr
  line per problem), 2 bad usage (including `--max` below 1) or unreadable
  file. Output: one JSON object `{"waves": [[...], ...]}`.
- `--max` defaults to 3.
- `**Depends on:**` line: `^\s*(?:- )?\*\*Depends on:\*\*\s*(.*?)\s*$`
  outside code fences inside a task; value exactly `none` or `Task N` items
  separated by `,` with optional spaces; case-sensitive; distinct;
  lower-numbered existing tasks only; at most one line per task.
- ADR number 0017; plugin version 0.7.0 → 0.8.0.

## Review Focus

1. A Depends line inside a fenced code block (a plan quoting an example) must
   be ignored by both `P10-depends` and `waves`. Pinned in Task 1 and Task 2.
2. A plan with no `### Task` headings must print `{"waves": []}`, not crash.
   Pinned in Task 2.
3. A plan with CRLF line endings must give the same waves. Pinned in Task 2.
4. Existing plans (no Depends lines) must run one task per wave. Pinned in
   Task 2 and checked on real plans in Task 6.
5. `/ship` step 4 must never stop the run because `waves` failed. Pinned in
   Task 4.

---

### Task 1: `**Depends on:**` parser and rule `P10-depends`

**Files:**
- Modify: `plugin/scripts/spec-lint.py`
- Test: `tests/test_spec_lint.py`

**Depends on:** none

**Interfaces:**
- Produces in `spec-lint.py`: `DEPENDS_RE`; `depends_value(value: str) -> list[int] | None`
  (`[]` for `none`, `None` when malformed); `task_depends(body: list[Line]) -> list[tuple[int, str]]`
  (line, raw value) per Depends line outside fences;
  `depends_problems(tasks) -> list[tuple[int, int, str]]` (line, task, message)
  where `tasks` is `task_spans(...)` output. Task 2 imports all four.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_spec_lint.py`:

```python
def with_depends(value, before="- [ ] **Step 1: Check it**"):
    """PLAN with a Depends line inserted before a step (default: Task 2's)."""
    return PLAN.replace(before, f"**Depends on:** {value}\n\n{before}", 1)


TASK3 = """

### Task 3: Third

**Files:**
- Modify: `src/new.py`

**Depends on:** {value}

- [ ] **Step 1: Check it again**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 2: Commit**
"""


def three(value):
    """PLAN plus a Task 3 whose Depends line (line 56) holds ``value``."""
    return PLAN.rstrip("\n") + TASK3.format(value=value)


def p10(text, root):
    return [(n, r) for n, r in plan_rules(text, root) if r == "P10-depends"]


def test_p10_none_and_earlier_tasks_pass(root):
    plan_root(root)
    assert sl.lint_plan(with_depends("none"), root) == []
    assert sl.lint_plan(with_depends("Task 1"), root) == []
    assert sl.lint_plan(three("Task 1, Task 2"), root) == []
    assert sl.lint_plan(three("Task 1,Task 2"), root) == []


def test_p10_bulleted_line_is_read(root):
    plan_root(root)
    text = PLAN.replace(
        "- [ ] **Step 1: Check it**",
        "- **Depends on:** Task 2\n\n- [ ] **Step 1: Check it**",
    )
    assert p10(text, root) == [(40, "P10-depends")]


def test_p10_forward_unknown_and_self_fail(root):
    plan_root(root)
    assert p10(three("none").replace(
        "- [ ] **Step 1: Check it**", "**Depends on:** Task 3\n\n- [ ] **Step 1: Check it**", 1
    ), root) == [(40, "P10-depends")]
    assert p10(three("Task 9"), root) == [(56, "P10-depends")]
    assert p10(with_depends("Task 2"), root) == [(40, "P10-depends")]


def test_p10_malformed_values_fail(root):
    plan_root(root)
    for value in ("Task 1, Task 1", "Task 1 and Task 2", "none.", "task 1", ""):
        assert p10(three(value), root) == [(56, "P10-depends")], value


def test_p10_second_line_fails(root):
    plan_root(root)
    text = with_depends("none").replace(
        "**Depends on:** none\n", "**Depends on:** none\n**Depends on:** Task 1\n"
    )
    assert p10(text, root) == [(41, "P10-depends")]


def test_p10_line_inside_a_fence_is_ignored(root):
    plan_root(root)
    text = PLAN.replace("Done.", "```text\n**Depends on:** Task 9\n```")
    assert p10(text, root) == []


def test_depends_value_parses():
    assert sl.depends_value("none") == []
    assert sl.depends_value("Task 1, Task 3") == [1, 3]
    assert sl.depends_value("Task 1 and Task 2") is None
```

Line numbers: `with_depends` puts the Depends line on line 40 (where Task 2's
first step was); `three` appends Task 3 so its Depends line is line 56.

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/test_spec_lint.py -q -k "p10 or depends"`
Expected: FAIL (`AttributeError: ... no attribute 'depends_value'` and empty
`P10-depends` lists)

- [ ] **Step 3: Implement in `plugin/scripts/spec-lint.py`**

Add after `APPROVED_RE` (the last constant), before `Line = ...`:

```python
DEPENDS_RE = re.compile(r"^\s*(?:- )?\*\*Depends on:\*\*\s*(.*?)\s*$")
DEPENDS_ITEM_RE = re.compile(r"^Task (\d+)$")
```

Add these functions after `check_plan_paths`:

```python
def depends_value(value: str) -> list[int] | None:
    """Task numbers in a Depends-on value: [] for ``none``, None if malformed."""
    if value == "none":
        return []
    numbers = []
    for item in value.split(","):
        match = DEPENDS_ITEM_RE.match(item.strip())
        if not match:
            return None
        numbers.append(int(match.group(1)))
    return numbers


def task_depends(body: list[Line]) -> list[tuple[int, str]]:
    """(line, value) of each ``**Depends on:**`` line in a task, outside fences."""
    out = []
    for number, line, code in body:
        match = None if code else DEPENDS_RE.match(line)
        if match:
            out.append((number, match.group(1)))
    return out


def depends_problems(
    tasks: list[tuple[int, int, list[Line]]],
) -> list[tuple[int, int, str]]:
    """(line, task, message) for each invalid ``**Depends on:**`` line."""
    numbers = {task for _, task, _ in tasks}
    out = []
    for _, task, body in tasks:
        for index, (number, value) in enumerate(task_depends(body)):
            if index:
                out.append((number, task, f"Task {task}: second Depends line"))
                continue
            deps = depends_value(value)
            if deps is None:
                message = f"Task {task}: malformed Depends value {value!r}"
            elif len(set(deps)) != len(deps):
                message = f"Task {task}: Depends repeats a task"
            elif any(d >= task or d not in numbers for d in deps):
                bad = next(d for d in deps if d >= task or d not in numbers)
                message = f"Task {task}: Task {bad} is not an earlier task"
            else:
                continue
            out.append((number, task, message))
    return out
```

In `lint_plan`, add to the `found` sum, after the `check_task_parts(...)`
term:

```python
        + [(n, "P10-depends", m) for n, _, m in depends_problems(tasks)]
```

In the module docstring, after the `P9-path (...)` sentence, add:

```
P10-depends (each task has at most one ``**Depends on:**`` line, valued
``none`` or ``Task N`` items, comma-separated, naming distinct earlier tasks).
```

- [ ] **Step 4: Run them to see them pass**

Run: `pytest tests/test_spec_lint.py -q`
Expected: PASS (all, including the existing plan-rule tests)

- [ ] **Step 5: Full suite, lint, commit**

```bash
ruff format plugin tests
pytest
ruff check plugin tests; ruff format --check plugin tests
git add plugin/scripts/spec-lint.py tests/test_spec_lint.py
git commit -m "spec-lint.py: P10-depends and the Depends-on parser

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `pytest` all pass; ruff clean.

### Task 2: `parallel-plan.py waves`

**Files:**
- Create: `plugin/scripts/parallel-plan.py`
- Test: `tests/test_parallel_plan.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes from `spec-lint.py` (Task 1 and the plan gate): `parse`,
  `task_spans`, `FILES_RE`, `SPAN_RE`, `task_depends`, `depends_value`,
  `depends_problems`.
- Produces: `as_path(span: str) -> str | None`, `overlaps(a: str, b: str) -> bool`,
  `any_overlap(left, right) -> bool`, `task_paths(body) -> set[str]`,
  `plan_waves(text: str, max_size: int) -> tuple[list[list[int]], list[str]]`
  (waves, problems), `main(argv) -> int`. The `/ship-many` spec reuses
  `as_path`, `overlaps` and `any_overlap`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_parallel_plan.py`:

```python
"""Tests for plugin/scripts/parallel-plan.py."""

from __future__ import annotations

import json

import pytest
from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "parallel-plan.py"
pp = load_module(SCRIPT, "parallel_plan")


def plan(*tasks):
    """A plan whose task i has Modify bullets ``files`` and an optional Depends."""
    parts = ["# P\n\n**Goal:** g.\n\n**Spec:** `docs/x.md`\n"]
    for number, (files, depends) in enumerate(tasks, 1):
        parts.append(f"\n### Task {number}: T{number}\n\n**Files:**\n")
        parts += [f"- Modify: `{name}`\n" for name in files]
        if depends is not None:
            parts.append(f"\n**Depends on:** {depends}\n")
        parts.append("\n- [ ] **Step 1: Commit**\n")
    return "".join(parts)


def waves(text, max_size=3):
    found, problems = pp.plan_waves(text, max_size)
    assert problems == []
    return found


def test_no_depends_lines_runs_one_task_per_wave():
    text = plan((["a.py"], None), (["b.py"], None), (["c.py"], None))
    assert waves(text) == [[1], [2], [3]]


def test_independent_tasks_fill_waves_up_to_max():
    text = plan(*[([f"{n}.py"], "none") for n in "abcd"])
    assert waves(text) == [[1, 2, 3], [4]]
    assert waves(text, 2) == [[1, 2], [3, 4]]


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("a.py", "a.py"),
        ("src/", "src/x.py"),
        ("CLAUDE.md", "CLAUDE.md"),
        ("a.py:1-5", "a.py"),
    ],
)
def test_overlapping_paths_keep_plan_order(first, second):
    text = plan(([first], "none"), ([second], "none"))
    assert waves(text) == [[1], [2]]


def test_declared_dependency_forces_a_later_wave():
    text = plan((["a.py"], "none"), (["b.py"], "none"), (["c.py"], "Task 1"))
    assert waves(text) == [[1, 2], [3]]


@pytest.mark.parametrize(
    ("span", "path"),
    [
        ("CLAUDE.md", "CLAUDE.md"),
        (".gitignore", ".gitignore"),
        ("smoke/", "smoke/"),
        ("plugin/a.py:12-20", "plugin/a.py"),
        ("0001", None),
        ("0.8.0", None),
        ("origin/main", None),
        ("docs/<slug>.md", None),
        ("a b.py", None),
    ],
)
def test_as_path(span, path):
    assert pp.as_path(span) == path


def test_plan_with_no_tasks_has_no_waves(tmp_path):
    assert pp.plan_waves("# P\n\nNothing yet.\n", 3) == ([], [])
    path = tmp_path / "plan.md"
    path.write_text("# P\n\nNothing yet.\n", encoding="utf-8")
    result = run_script(SCRIPT, "waves", str(path))
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"waves": []}


def test_crlf_plan_gives_the_same_waves():
    text = plan((["a.py"], "none"), (["b.py"], "none"))
    assert waves(text.replace("\n", "\r\n")) == waves(text)


def test_depends_line_in_a_fence_is_ignored():
    text = plan((["a.py"], "none"), (["b.py"], "none"))
    text += "\n```text\n**Depends on:** Task 9\n```\n"
    assert waves(text) == [[1, 2]]


@pytest.mark.parametrize("value", ["Task 2", "Task 9", "Task 1, Task 1"])
def test_invalid_depends_is_reported(value, tmp_path):
    text = plan((["a.py"], "none"), (["b.py"], value))
    if value == "Task 2":
        text = plan((["a.py"], value), (["b.py"], "none"))
    found, problems = pp.plan_waves(text, 3)
    assert found == [] and len(problems) == 1
    path = tmp_path / "plan.md"
    path.write_text(text, encoding="utf-8")
    assert run_script(SCRIPT, "waves", str(path)).returncode == 1


def test_cli_prints_json(tmp_path):
    path = tmp_path / "plan.md"
    path.write_text(plan((["a.py"], "none"), (["b.py"], "none")), encoding="utf-8")
    result = run_script(SCRIPT, "waves", str(path))
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"waves": [[1, 2]]}


def test_cli_invalid_plan_exits_one(tmp_path):
    path = tmp_path / "plan.md"
    text = plan((["a.py"], "none"), (["b.py"], "none")).replace(
        "**Depends on:** none\n", "**Depends on:** none\n**Depends on:** none\n", 1
    )
    path.write_text(text, encoding="utf-8")
    result = run_script(SCRIPT, "waves", str(path))
    assert result.returncode == 1
    assert "Depends" in result.stderr


def test_cli_bad_max_and_missing_file_exit_two(tmp_path):
    path = tmp_path / "plan.md"
    path.write_text(plan((["a.py"], "none")), encoding="utf-8")
    assert run_script(SCRIPT, "waves", str(path), "--max", "0").returncode == 2
    assert run_script(SCRIPT, "waves", str(tmp_path / "no.md")).returncode == 2
```

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/test_parallel_plan.py -q`
Expected: FAIL (collection error: `plugin/scripts/parallel-plan.py` does not exist)

- [ ] **Step 3: Write `plugin/scripts/parallel-plan.py`**

```python
#!/usr/bin/env python3
"""Group a plan's tasks into waves that can run concurrently.

    python parallel-plan.py waves PLAN.md [--max N]

Prints one JSON object, ``{"waves": [[1, 2], [3]]}``: task numbers per wave,
in order. A task's paths are the backticked paths in the Create/Modify/Test
bullets of its ``**Files:**`` block. Its dependencies are its
``**Depends on:**`` line (``none`` or ``Task N`` items), or every earlier task
when the line is missing, plus every earlier task whose paths overlap its own.
A task goes into the first wave after its dependencies' waves that holds fewer
than ``--max`` (default 3) tasks.

A path is a backticked span that, without a ``:LINE`` or ``:LINE-LINE``
suffix, has no whitespace, none of ``< > * $ { ://``, does not start with
``-`` or ``~``, and has a file suffix (its last part starts with ``.`` or has
``.`` then a letter) or ends with ``/``. Two paths overlap when equal or when
one ends with ``/`` and the other starts with it.

Exits 0 on success, 1 on an invalid ``**Depends on:**`` line (one stderr line
per problem), 2 on bad usage or an unreadable file.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


def _load_spec_lint():
    path = Path(__file__).resolve().parent / "spec-lint.py"
    spec = importlib.util.spec_from_file_location("spec_lint_for_parallel", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sl = _load_spec_lint()

BULLET_RE = re.compile(r"^\s*- (Create|Modify|Test):(.*)$")
LINE_SUFFIX_RE = re.compile(r":\d+(-\d+)?$")
SUFFIX_RE = re.compile(r"\.[A-Za-z]")
NOT_A_PATH = ("<", ">", "*", "$", "{", "://")


def as_path(span: str) -> str | None:
    """The span as a path, or None when it is not one."""
    span = LINE_SUFFIX_RE.sub("", span)
    if not span or any(ch.isspace() for ch in span):
        return None
    if any(bad in span for bad in NOT_A_PATH) or span.startswith(("-", "~")):
        return None
    if span.endswith("/"):
        return span
    name = span.rsplit("/", 1)[-1]
    return span if name.startswith(".") or SUFFIX_RE.search(name) else None


def overlaps(a: str, b: str) -> bool:
    """Equal paths, or a directory path and a path under it."""
    if a == b:
        return True
    return (a.endswith("/") and b.startswith(a)) or (b.endswith("/") and a.startswith(b))


def any_overlap(left, right) -> bool:
    return any(overlaps(a, b) for a in left for b in right)


def task_paths(body) -> set[str]:
    """Paths in the Create/Modify/Test bullets of a task's Files block."""
    out: set[str] = set()
    in_files = False
    for _, line, code in body:
        if code:
            in_files = False
            continue
        if sl.FILES_RE.match(line):
            in_files = True
            continue
        match = BULLET_RE.match(line) if in_files else None
        if match:
            for span in sl.SPAN_RE.findall(match.group(2)):
                path = as_path(span)
                if path:
                    out.add(path)
        elif line.strip() and not line.startswith((" ", "\t")):
            in_files = False
    return out


def plan_waves(text: str, max_size: int) -> tuple[list[list[int]], list[str]]:
    """(waves, problems) for a plan's text; waves is empty when problems exist."""
    tasks = sorted(sl.task_spans(sl.parse(text)), key=lambda t: t[1])
    problems = [message for _, _, message in sl.depends_problems(tasks)]
    if problems:
        return [], problems
    numbers = [task for _, task, _ in tasks]
    paths = {task: task_paths(body) for _, task, body in tasks}
    wave_of: dict[int, int] = {}
    waves: list[list[int]] = []
    for _, task, body in tasks:
        found = sl.task_depends(body)
        if found:
            deps = set(sl.depends_value(found[0][1]))
        else:
            deps = {n for n in numbers if n < task}
        deps |= {n for n in numbers if n < task and any_overlap(paths[n], paths[task])}
        wave = max((wave_of[d] + 1 for d in deps if d in wave_of), default=0)
        while wave < len(waves) and len(waves[wave]) >= max_size:
            wave += 1
        if wave == len(waves):
            waves.append([])
        waves[wave].append(task)
        wave_of[task] = wave
    return waves, []


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="parallel-plan.py")
    commands = parser.add_subparsers(dest="command", required=True)
    waves_cmd = commands.add_parser("waves")
    waves_cmd.add_argument("plan")
    waves_cmd.add_argument("--max", type=int, default=3)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.max < 1:
        print("parallel-plan: --max must be at least 1", file=sys.stderr)
        return 2
    try:
        text = Path(args.plan).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"parallel-plan: cannot read {args.plan}: {exc}", file=sys.stderr)
        return 2
    waves, problems = plan_waves(text, args.max)
    for problem in problems:
        print(f"{args.plan}: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(json.dumps({"waves": waves}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run them to see them pass**

Run: `pytest tests/test_parallel_plan.py -q`
Expected: PASS

- [ ] **Step 5: Full suite, lint, commit**

```bash
ruff format plugin tests
pytest
ruff check plugin tests; ruff format --check plugin tests
git add plugin/scripts/parallel-plan.py tests/test_parallel_plan.py
git commit -m "parallel-plan.py: group a plan's tasks into waves

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `pytest` all pass; ruff clean.

### Task 3: The `parallel-tasks` skill

**Files:**
- Create: `plugin/skills/parallel-tasks/SKILL.md`
- Test: `tests/test_parallel_tasks_skill.py`

**Depends on:** Task 2

**Interfaces:**
- Consumes: `../../scripts/parallel-plan.py` (Task 2) from the skill
  directory.
- Produces: the skill name `claude-kit:parallel-tasks`, used by `/ship` step 4
  (Task 4).

- [ ] **Step 1: Write the failing test**

Create `tests/test_parallel_tasks_skill.py`:

```python
"""Structure tests for the parallel-tasks skill."""

from __future__ import annotations

from helpers import PLUGIN

SKILL = PLUGIN / "skills" / "parallel-tasks" / "SKILL.md"
SCRIPT_REL = "../../scripts/parallel-plan.py"


def body():
    return SKILL.read_text(encoding="utf-8")


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_frontmatter():
    front = frontmatter(body())
    assert front["name"] == "parallel-tasks"
    assert front["description"].startswith("Use when")
    assert "disable-model-invocation" not in front


def test_skill_names_its_commands():
    text = body()
    assert SCRIPT_REL in text and (SKILL.parent / SCRIPT_REL).resolve().is_file()
    for needle in (
        "git worktree add",
        "git merge --no-ff",
        "git worktree remove --force",
        "git branch -D",
        "superpowers:executing-plans",
        "git log --merges --format=%P",
        "git rev-list --count",
    ):
        assert needle in text, needle


def test_subagent_prompt_has_the_lock_retry():
    prompt = body().split("only this prompt", 1)[1]
    assert "Unable to create '...lock': File exists" in prompt
    assert "cannot lock ref" in prompt


def test_resume_skips_complete_tasks():
    assert "complete` ledger line" in body()
```

- [ ] **Step 2: Run it to see it fail**

Run: `pytest tests/test_parallel_tasks_skill.py -q`
Expected: FAIL (`FileNotFoundError` for `SKILL.md`)

- [ ] **Step 3: Write `plugin/skills/parallel-tasks/SKILL.md`**

````markdown
---
name: parallel-tasks
description: Use when /ship (or you) implements a plan whose waves, from parallel-plan.py, hold more than one task. Runs each wave's tasks as concurrent subagents, one git worktree per task, then merges them back in task order with --no-ff and runs the full suite after each wave.
argument-hint: [path-to-plan.md]
---

# Parallel tasks

Runs one plan's tasks by waves from inside a `/ship` feature worktree. Tasks
in a wave share no files and do not depend on each other, so they can be
built at the same time.

## Setup

- **Plan:** `$ARGUMENTS`, the plan `/ship` is implementing.
- **Script:** `python <this skill's directory>/../../scripts/parallel-plan.py`.
- `<branch-slug>` is the feature branch name with `/` replaced by `_`;
  `<tmp>` is the OS temp directory; `<plan>` is the plan's repo-relative
  path (the plan is committed in `/ship` step 3, so every task worktree has
  the same copy).
- Every git command here follows `/ship`'s git lock retry rule: a command
  that fails with `Unable to create '...lock': File exists` or
  `cannot lock ref` is retried after 5 seconds, up to 5 times.

## Steps

1. **Setup.** Do `superpowers:executing-plans`' setup once: its ledger
   workspace, reading the plan and spec, and its pre-flight scan.
2. **Waves.** Run the script: `parallel-plan.py waves <plan>`. If it exits
   non-zero, write a `Ruling:` ledger line with its messages and implement
   the remaining tasks one at a time with `superpowers:executing-plans`.
3. **Each wave, in order**, skipping every task that already has a
   `Task N: complete` ledger line (a resumed run picks up where it stopped):
   - **One task:** implement it in the feature worktree exactly as
     `executing-plans` does (TDD, its commit, its `complete` ledger line).
   - **Several tasks:** for each task N:
     - **Leftovers first.** If a `<feature-branch>-task-N` branch exists from
       an interrupted run, it counts as merged only when its tip appears as
       the second parent of a merge commit on the feature branch: look for
       `git rev-parse <feature-branch>-task-N` in the second column of
       `git log --merges --format=%P <feature-branch>`. A branch that never
       got a commit sits at an ancestor of HEAD and does not count. If it
       counts, write its missing `complete` ledger line and skip the task.
       Otherwise remove any worktree at its path
       (`git worktree remove --force`) and delete the branch
       (`git branch -D`).
     - Create its worktree:
       `git worktree add <tmp>/claude-tasks/<branch-slug>/task-N -b <feature-branch>-task-N HEAD`.

     Then dispatch one new general-purpose subagent per task, all in the
     background, each given only this prompt:

     > Implement Task N of the plan at `<plan>` in the git worktree at
     > `<task worktree>`, exactly as written, test-first. Read the plan's
     > header and Global Constraints first. Run the full test suite and lint
     > that the plan names (else the repo's `CLAUDE.md`) in that worktree,
     > and commit there with the task's commit message. Any git command that
     > fails with `Unable to create '...lock': File exists` or
     > `cannot lock ref` is retried after 5 seconds, up to 5 times. Do not
     > push, merge, or touch any other worktree. Report the commit SHAs and
     > the test result.

     When every subagent has reported, merge, in task-number order with
     `git merge --no-ff --no-edit <feature-branch>-task-N`, only the task
     branches whose subagent reported a passing suite and for which
     `git rev-list --count HEAD..<feature-branch>-task-N` is at least 1.
     Right after each merge, append
     `Task N: complete (merged <task branch> at <merge sha7>, tests: <reported result>)`
     to the ledger. A merge conflict means a `**Files:**` list was
     incomplete: resolve it keeping both changes and write a `Ruling:` ledger
     line. A failed task's branch is not merged; after the merges, implement
     that task inline in the feature worktree from the merged HEAD, and write
     its `complete` line after its commit.
   - **After the wave:** run the full test suite and lint. Red is debugged
     with `superpowers:systematic-debugging`, fixed and committed. Then
     remove the wave's task worktrees (`git worktree remove --force`) and
     branches (`git branch -D`).
4. **Final review.** Remove `<tmp>/claude-tasks/<branch-slug>/` if it is
   empty, then do `executing-plans`' final whole-branch review and fix pass.
````

- [ ] **Step 4: Run it to see it pass**

Run: `pytest tests/test_parallel_tasks_skill.py tests/test_plugin_manifest.py -q`
Expected: PASS

- [ ] **Step 5: Full suite, lint, commit**

```bash
ruff format plugin tests
pytest
ruff check plugin tests; ruff format --check plugin tests
git add plugin/skills/parallel-tasks tests/test_parallel_tasks_skill.py
git commit -m "parallel-tasks skill: run a plan's waves as concurrent subagents

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `pytest` all pass; ruff clean.

### Task 4: `/ship` wiring

**Files:**
- Modify: `plugin/commands/ship.md`
- Test: `tests/test_ship_command.py`

**Depends on:** none

**Interfaces:**
- Consumes: the names `parallel-plan.py` (Task 2) and
  `claude-kit:parallel-tasks` (Task 3); only text, so no ordering is needed.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ship_command.py`:

```python
def test_step_3_adds_depends_on_lines():
    assert "**Depends on:**" in _step(3)


def test_step_4_picks_waves_and_falls_back():
    step = _step(4)
    assert "parallel-plan.py" in step and "waves" in step
    assert "claude-kit:parallel-tasks" in step
    assert "non-zero" in step and "not a stop rule" in step


def test_git_lock_retry_rule():
    rule = SHIP.split("## Git lock retry", 1)[1].split("## Steps", 1)[0]
    assert "Unable to create '...lock': File exists" in rule
    assert "cannot lock ref" in rule
```

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/test_ship_command.py -q`
Expected: FAIL (the three new tests)

- [ ] **Step 3: Edit `plugin/commands/ship.md`**

Insert this section between the Stop rules list and `## Steps`:

```markdown
## Git lock retry

Any git command in this repository, in the main checkout or any worktree,
that fails with `Unable to create '...lock': File exists` or
`cannot lock ref` is retried after 5 seconds, up to 5 times. All worktrees
share one `.git` directory, so concurrent worktrees can collide on its locks.
A command still failing after that is handled like any other failed command.
```

In step 3, the sentence ends "Do not offer an execution choice." (it wraps
across two lines). Directly after it, insert:

```markdown
Then add a `**Depends on:**` line under each task's `**Files:**` block:
`none`, or the earlier tasks whose results it uses (`Task 1, Task 3`).
Shared files need not be listed (`parallel-plan.py` orders them anyway), so
a task whose only link to earlier tasks is shared files gets
`**Depends on:** none`.
```

In step 4, replace the text from the final `Use` (at the end of the line
ending "otherwise return to step 3. Use") through "in this session." on the
line two below it (that sentence spans three lines) with:

```markdown
Then run
`python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" waves <plan>`
(fallback if the variable is not expanded:
`~/.claude/skills/claude-kit/scripts/parallel-plan.py`). If every wave has
one task, use `superpowers:executing-plans` with
`superpowers:test-driven-development`, in this session. Otherwise use
`claude-kit:parallel-tasks` with `<plan>` as its argument. If the script
exits non-zero, write a
`Ruling:` ledger line with its messages and use `executing-plans` as above:
this is not a stop rule, because the plan is still executable one task at a
time.
```

Keep the rest of step 4 ("The plan's review checkpoints are progress notes…")
unchanged. Indent inserted lines to match the step (3 spaces).

- [ ] **Step 4: Run them to see them pass**

Run: `pytest tests/test_ship_command.py -q`
Expected: PASS (all, including the existing plan-gate step 3 and 4 tests)

- [ ] **Step 5: Full suite, lint, commit**

```bash
ruff format plugin tests
pytest
ruff check plugin tests; ruff format --check plugin tests
git add plugin/commands/ship.md tests/test_ship_command.py
git commit -m "/ship: Depends-on lines, waves in step 4, git lock retry

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `pytest` all pass; ruff clean.

### Task 5: Conventions, ADR 0017, version

**Files:**
- Modify: `conventions/spec-driven-development.md`
- Create: `knowledge/decisions/0017-parallel-plan-tasks.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `tests/test_parallel_tasks_skill.py`

**Depends on:** none

- [ ] **Step 1: Write the failing docs test**

In `tests/test_parallel_tasks_skill.py`, change the import line
`from helpers import PLUGIN` to `from helpers import PLUGIN, REPO`, then
append:

```python
def test_docs_wire_parallel_tasks():
    conventions = (REPO / "conventions" / "spec-driven-development.md").read_text(
        encoding="utf-8"
    )
    assert "**Depends on:**" in conventions
    adr = "0017-parallel-plan-tasks.md"
    assert (REPO / "knowledge" / "decisions" / adr).is_file()
    index = (REPO / "knowledge" / "decisions" / "README.md").read_text(encoding="utf-8")
    assert f"]({adr})" in index
```

- [ ] **Step 2: Run it to see it fail**

Run: `pytest tests/test_parallel_tasks_skill.py::test_docs_wire_parallel_tasks -q`
Expected: FAIL (`AssertionError` on `**Depends on:**`)

- [ ] **Step 3: Write the docs**

In `conventions/spec-driven-development.md`, insert before `## Self-contained plans`:

```markdown
## Parallel plan tasks

A task may carry one `**Depends on:**` line under its `**Files:**` block:
`none`, or the earlier tasks whose results it uses (`Task 1, Task 3`). A task
without the line runs after every earlier task, so plans without these lines
run exactly as before. `plugin/scripts/parallel-plan.py waves` groups tasks
into waves: tasks in a wave share no file (from their Create, Modify and Test
bullets) and depend on no task in the same wave. Under `/ship`, a wave with
more than one task runs through `claude-kit:parallel-tasks`: one subagent and
git worktree per task, merged back in task order
([ADR 0017](../knowledge/decisions/0017-parallel-plan-tasks.md)). The plan
gate checks the line with rule `P10-depends`.
```

Create `knowledge/decisions/0017-parallel-plan-tasks.md`:

```markdown
# ADR 0017: Independent plan tasks run as concurrent subagents

- **Status:** accepted
- **Date:** 2026-10-01

## Context
`/ship` implemented a plan's tasks one after another, even when tasks touched
different files and did not use each other's results. Plans already list each
task's files (the plan gate requires it).

## Decision
A task may declare `**Depends on:** none` or `Task N, ...`; without the line
it depends on every earlier task. `parallel-plan.py waves` adds a dependency
on every earlier task that shares a file, and groups tasks into waves of at
most 3. `/ship` runs a wave with several tasks through the `parallel-tasks`
skill: one subagent per task, each in its own worktree branched from the
feature branch, merged back with `--no-ff` in task order, the full suite run
after each wave. A failed task, or a failing `waves` run, falls back to
one-at-a-time work instead of stopping `/ship`. Every git command in the repo
retries on lock errors, because worktrees share one `.git` directory.

## Consequences
Plans with independent tasks finish sooner, at the cost of one subagent per
parallel task. History shows one merge commit per parallel task. A `Files:`
list that misses a file shows up as a merge conflict, resolved by the agent
and recorded as a ruling.
```

In `knowledge/decisions/README.md`, add after the 0016 row:

```markdown
| [0017](0017-parallel-plan-tasks.md) | Independent plan tasks run as concurrent subagents | accepted | 2026-10-01 |
```

In `plugin/.claude-plugin/plugin.json`, change `"version": "0.7.0"` to
`"version": "0.8.0"`.

- [ ] **Step 4: Run it to see it pass**

Run: `pytest tests/test_parallel_tasks_skill.py tests/test_docs.py tests/test_plugin_manifest.py -q`
Expected: PASS

- [ ] **Step 5: Full suite, lint, commit**

```bash
ruff format plugin tests
pytest
ruff check plugin tests; ruff format --check plugin tests
git add conventions/spec-driven-development.md knowledge/decisions plugin/.claude-plugin/plugin.json tests/test_parallel_tasks_skill.py
git commit -m "Parallel plan tasks: conventions, ADR 0017, v0.8.0

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `pytest` all pass; ruff clean.

### Task 6: Fixture plan, back-compat check, smoke check

**Files:**
- Create: `tests/fixtures/parallel/plan.md`

**Depends on:** Task 2, Task 3

- [ ] **Step 1: Write `tests/fixtures/parallel/plan.md`**

````markdown
# Smoke Plan

- **Status:** implemented
- **Date:** 2026-10-01

**Goal:** Add three tiny modules under `smoke/` to exercise parallel waves.

**Spec:** `docs/superpowers/specs/2026-09-30-parallel-plan-tasks-design.md`

## Global Constraints

- The suite is `pytest tests smoke`; lint is not required for `smoke/`.
- `smoke/` has no `__init__.py`; tests import modules by name.

### Task 1: Module a

**Files:**
- Create: `smoke/a.py`
- Test: `smoke/test_a.py`

**Depends on:** none

- [ ] **Step 1: Write the test** — `smoke/test_a.py`:
  `from a import a` and `def test_a(): assert a() == 1`.
- [ ] **Step 2: Run it** — Run: `pytest smoke/test_a.py -q` Expected: FAIL
  (`ModuleNotFoundError`).
- [ ] **Step 3: Write `smoke/a.py`** — `def a(): return 1`.
- [ ] **Step 4: Run it** — Run: `pytest smoke/test_a.py -q` Expected: PASS.
- [ ] **Step 5: Commit** — `git add smoke/a.py smoke/test_a.py` and
  `git commit -m "smoke: a"`.

### Task 2: Module b

**Files:**
- Create: `smoke/b.py`
- Test: `smoke/test_b.py`

**Depends on:** none

- [ ] **Step 1: Write the test** — `smoke/test_b.py`:
  `from b import b` and `def test_b(): assert b() == 2`.
- [ ] **Step 2: Run it** — Run: `pytest smoke/test_b.py -q` Expected: FAIL.
- [ ] **Step 3: Write `smoke/b.py`** — `def b(): return 2`.
- [ ] **Step 4: Run it** — Run: `pytest smoke/test_b.py -q` Expected: PASS.
- [ ] **Step 5: Commit** — `git add smoke/b.py smoke/test_b.py` and
  `git commit -m "smoke: b"`.

### Task 3: Module c uses a and b

**Files:**
- Create: `smoke/c.py`
- Test: `smoke/test_c.py`

**Depends on:** Task 1, Task 2

- [ ] **Step 1: Write the test** — `smoke/test_c.py`:
  `from c import c` and `def test_c(): assert c() == 3`.
- [ ] **Step 2: Run it** — Run: `pytest smoke/test_c.py -q` Expected: FAIL.
- [ ] **Step 3: Write `smoke/c.py`** — `from a import a`, `from b import b`,
  `def c(): return a() + b()`.
- [ ] **Step 4: Run it** — Run: `pytest tests smoke -q` Expected: PASS.
- [ ] **Step 5: Commit** — `git add smoke/c.py smoke/test_c.py` and
  `git commit -m "smoke: c"`.
````

- [ ] **Step 2: Check its waves and commit**

Run: `python plugin/scripts/parallel-plan.py waves tests/fixtures/parallel/plan.md`
Expected: `{"waves": [[1, 2], [3]]}`

```bash
git add tests/fixtures/parallel/plan.md
git commit -m "Fixture plan for the parallel-tasks smoke check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 3: Back-compat check**

Run `python plugin/scripts/parallel-plan.py waves <plan>` for each plan in
`docs/superpowers/plans/` that has no `**Depends on:**` line (every plan
except this one).
Expected: each prints one task per wave, e.g. `{"waves": [[1], [2], [3]]}`.
Save the output for the PR.

- [ ] **Step 4: Smoke check (by hand, in a scratch clone)**

Run this step in the main session, in the feature worktree on
`feat/parallel-plan-tasks`, after Steps 1–3 are committed; do not delegate it
to a task subagent (it dispatches subagents itself). The plugin loads from
the main checkout until merge, so follow
`plugin/skills/parallel-tasks/SKILL.md` yourself, using the clone's scripts:

1. `git clone --branch feat/parallel-plan-tasks <this worktree> <tmp>/pp-smoke`
   (`<tmp>` = the OS temp directory), then in the clone
   `git checkout -b smoke-run`. Never push from the clone.
2. In the clone, run `python plugin/scripts/parallel-plan.py waves tests/fixtures/parallel/plan.md`.
   Expected: `{"waves": [[1, 2], [3]]}`.
3. Wave 1: create two task worktrees with
   `git worktree add <tmp>/claude-tasks/smoke-run/task-1 -b smoke-run-task-1 HEAD`
   (and `task-2`), dispatch two subagents with the skill's prompt (plan
   `tests/fixtures/parallel/plan.md`), merge both with
   `git merge --no-ff --no-edit`, run `pytest tests smoke -q`, remove both
   worktrees and branches.
4. Wave 2: implement Task 3 inline; Run: `pytest tests smoke -q`
   Expected: PASS.
5. Run: `git log --merges --oneline` Expected: two merges of
   `smoke-run-task-1` and `smoke-run-task-2`. Run: `git worktree list`
   Expected: only the clone itself.
6. Save the outputs for the PR, then delete `<tmp>/pp-smoke` and
   `<tmp>/claude-tasks/smoke-run`.

## Verification (maps to the spec's Success criteria)

| Criterion | Evidence |
|---|---|
| 1 waves tests | `pytest tests/test_parallel_plan.py` (Task 2) |
| 2 P10 tests | `pytest tests/test_spec_lint.py` (Task 1) |
| 3 structure tests | `pytest tests/test_parallel_tasks_skill.py tests/test_ship_command.py` (Tasks 3, 4) |
| 4 back-compat | Task 6 Step 3 output |
| 5 smoke check | Task 6 Step 4 output |
| 6 docs | `pytest tests/test_parallel_tasks_skill.py` (Task 5); `plugin.json` says 0.8.0 |
| 7 suite and lint | `pytest`; `ruff check plugin tests; ruff format --check plugin tests`; CI |

When every task is done, set this plan's Status and the spec's Status to
`implemented`.
