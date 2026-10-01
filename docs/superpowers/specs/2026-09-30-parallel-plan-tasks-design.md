# Parallel plan tasks: independent tasks run as concurrent subagents

- **Status:** approved
- **Date:** 2026-09-30

## Purpose

`/ship` implements a plan's tasks one after another, even when two tasks
touch different files and do not use each other's results. This work runs
such tasks concurrently, one subagent per task, in waves. Tasks that share a
file, or that declare a dependency, keep their plan order.

A plan task already lists the files it touches in its `**Files:**` block; the
plan gate rule `P6-task-parts`
(`docs/superpowers/specs/2026-09-30-plan-gate-design.md`) requires it. This
work adds one optional line per task, `**Depends on:**`, for dependencies that
are not visible as shared files.

This spec builds on the plan gate and assumes it has merged: its plan mode in
`spec-lint.py`, its `P1`–`P9` rules, and its `/ship` steps 3 and 4. It is the
first of two parallel-shipping specs; the second, `/ship-many` for running
several specs at once, reuses this spec's overlap code.

## Scope

**In:**

- `plugin/scripts/parallel-plan.py` (new): the `waves` command, which groups a
  plan's tasks into waves and prints them as JSON, and the shared path and
  overlap helpers.
- `plugin/scripts/spec-lint.py`: a plan rule `P10-depends` for the
  `**Depends on:**` task line.
- `plugin/skills/parallel-tasks/SKILL.md` (new): the procedure that runs one
  plan's waves with one subagent per task.
- `plugin/commands/ship.md`: step 3 adds `**Depends on:**` lines to the plan;
  step 4 uses `claude-kit:parallel-tasks` when a wave has more than one task;
  a retry rule for git lock errors.
- `conventions/spec-driven-development.md`: the `**Depends on:**` task line.
- `knowledge/decisions/0017-parallel-plan-tasks.md` (new): ADR 0017, plus its
  row in `knowledge/decisions/README.md`.
- Tests: `tests/test_parallel_plan.py` (new),
  `tests/test_parallel_tasks_skill.py` (new), and additions to
  `tests/test_spec_lint.py` and `tests/test_ship_command.py`.
- `tests/fixtures/parallel/plan.md` (new): a three-task plan for the smoke
  check.
- Plugin version in `plugin/.claude-plugin/plugin.json`: 0.7.0 → 0.8.0.

**Out:**

- Running several specs at once (`/ship-many`): the second parallel-shipping
  spec.
- Editing the superpowers plugin. `writing-plans` does not know about
  `**Depends on:**`, so `/ship` step 3 adds the lines after it writes the
  plan.
- Parallel review rounds inside the spec or plan gates.
- A per-run override of the wave size. It is fixed at 3 for `/ship`.

## Design

### Paths and overlap

A **path** is a backticked span that, after a trailing `:LINE` or
`:LINE-LINE` suffix is dropped, has no whitespace, contains none of `<`, `>`,
`*`, `$`, `{` or `://`, does not start with `-` or `~`, and either has a file
suffix or ends with `/`. A **file suffix** means the last `/`-separated part either starts with
`.` (a dotfile) or contains a `.` followed by a letter. So `CLAUDE.md`,
`.gitignore`, `smoke/` and `plugin/a.py:12-20` are paths; `0001`, `0.8.0`,
`origin/main` and `docs/<slug>.md` are not. Root files with no dot, such as
`Makefile` or `LICENSE`, are not paths; a missed overlap on them shows up as a
merge conflict, which the skill resolves.

Two paths **overlap** when they are equal, or one ends with `/` and the other
starts with it. Two items overlap when any path of one overlaps any path of
the other.

These helpers live in `parallel-plan.py` so the second spec can reuse them.

### `plugin/scripts/parallel-plan.py waves`

```
python parallel-plan.py waves PLAN.md [--max N]
```

`--max` defaults to 3. Output is one JSON object on stdout. Exit 0 on
success; 1 on an invalid plan, with one message per problem on stderr; 2 on
bad usage (including `--max` below 1) or an unreadable file. The script uses
the standard library only. It reuses `spec-lint.py`'s fence-aware line parser
by loading that file with `importlib`, as the tests already do.

Tasks are the `### Task N:` sections, in number order. A task's paths are the
paths (as defined above) in the `- Create:`, `- Modify:` and `- Test:` bullets
of its `**Files:**` block. A task's declared dependencies come from its
`**Depends on:**` line:

- `**Depends on:** none`: no declared dependencies.
- `**Depends on:** Task 2, Task 4`: those tasks.
- No `**Depends on:**` line: every lower-numbered task. A plan without any
  such line therefore runs one task per wave, exactly as today.

A plan is invalid when a `**Depends on:**` value is neither `none` nor a list
of distinct lower-numbered existing tasks, or a task has more than one such
line (the same checks as `P10-depends`). A plan with no `### Task N:` headings
prints `{"waves": []}`. Task-number gaps and repeats are left to the plan
gate's `P5-tasks`; `waves` uses the numbers as written.

A task's effective dependencies are its declared ones plus every
lower-numbered task whose paths overlap its own, so tasks that share a file
keep their plan order. Waves are assigned in task-number order: a task goes
into the first wave after the waves of all its effective dependencies that
holds fewer than `--max` tasks. Output:

```json
{"waves": [[1, 2], [3]]}
```

### Plan rule `P10-depends` in `spec-lint.py`

A **`**Depends on:**` line** is a line outside code fences, inside a task's
section, matching `^\s*(?:- )?\*\*Depends on:\*\*\s*(.*?)\s*$` (an optional
indent and `- ` bullet are allowed). The parser and the task-section splitter
live in `spec-lint.py`; `parallel-plan.py` uses them through its `importlib`
load. Its value must be
exactly `none`, or one or more `Task N` items separated by `,` with optional
spaces around the comma, case-sensitive, with nothing else (no `and`, no
trailing punctuation). `waves` and `P10-depends` share this parser; a line
that starts with `**Depends on:**` but whose value does not match is invalid,
never ignored.

In plan mode (the plan gate's rule set), each task has at most one
`**Depends on:**` line, and its value is `none` or a comma-separated list of
`Task N`, where every N is a distinct lower-numbered task in the plan. One violation
per bad or extra line, at that line. A task without the line is valid.

### `plugin/skills/parallel-tasks/SKILL.md`

Frontmatter: `name: parallel-tasks` and a `description` starting "Use when",
like the kit's other skills; no `disable-model-invocation`, because `/ship`
invokes it.

Runs one plan's tasks by waves from inside a `/ship` feature worktree. The
scripts are reached as `../../scripts/<name>.py` from the skill directory.
`<branch-slug>` is the feature branch name with `/` replaced by `_`; `<tmp>`
is the OS temp directory.

1. **Setup.** Do `superpowers:executing-plans`' setup once: its ledger
   workspace, reading the plan and spec, and its pre-flight scan.
2. **Waves.** Run `parallel-plan.py waves <plan>`. `/ship` step 4 has already
   run it successfully before invoking this skill; if it nonetheless exits
   non-zero here, write a `Ruling:` ledger line with its messages and
   implement the remaining tasks one at a time with `executing-plans`.
3. For each wave, in order, skipping every task that already has a
   `Task N: complete` ledger line (a resumed run picks up where it stopped):
   - **One task:** implement it in the feature worktree exactly as
     `executing-plans` does (TDD, the task's commit, its `complete` ledger
     line).
   - **Several tasks:** for each remaining task N, run
     `git worktree add <tmp>/claude-tasks/<branch-slug>/task-N -b <feature-branch>-task-N HEAD`.
     `<plan>` below is the plan's repo-relative path; the plan is committed
     in `/ship` step 3, so each task worktree has the same copy. Dispatch one
     new general-purpose subagent per task, all in the background, each given
     only this prompt:

     > Implement Task N of the plan at `<plan>` in the git worktree at
     > `<task worktree>`, exactly as written, test-first. Read the plan's
     > header and Global Constraints first. Run the full test suite and
     > lint that the plan names (else the repo's `CLAUDE.md`) in that
     > worktree, and commit there with the task's commit message. Any git
     > command that fails with `Unable to create '...lock': File exists` or
     > `cannot lock ref` is retried after 5 seconds, up to 5 times. Do not
     > push, merge, or touch any other worktree. Report the commit SHAs and
     > the test result.

     Before creating a task worktree, check for leftovers of an interrupted
     run. An existing `<feature-branch>-task-N` branch counts as merged only
     when a merge commit on the feature branch has the task branch's tip as
     its second parent (`git rev-parse <task branch>` appears as the second
     hash in `git log --merges --format=%P <feature-branch>`); a branch that
     never got a commit sits at an ancestor of HEAD and does not count. If it
     counts as merged, write its missing `complete` ledger line and skip the
     task. Otherwise remove any existing worktree at that path, delete the
     branch, and run the task.

     When all have reported, merge into the feature branch, in task-number
     order with `git merge --no-ff --no-edit`, only the branches of tasks
     whose subagent reported a passing suite and for which
     `git rev-list --count HEAD..<task branch>` is at least 1, and
     append that task's ledger line by hand right after its merge:
     `Task N: complete (merged <task branch> at <merge sha7>, tests: <the subagent's reported result>)`.
     A merge conflict means a `**Files:**` list was incomplete: resolve it
     keeping both changes, and write a `Ruling:` ledger line. A failed task's
     branch is not merged; it is deleted with the others, and that task is
     implemented inline in the feature worktree, from the merged HEAD, after
     the merges, with its `complete` line written after its commit.
   - After the wave, run the full test suite and lint. Red is debugged with
     `superpowers:systematic-debugging`, fixed and committed.
   - Remove every task worktree and branch of the wave
     (`git worktree remove --force`, `git branch -D`).
4. **Final review.** After the last wave, remove
   `<tmp>/claude-tasks/<branch-slug>/` if it is empty, then do
   `executing-plans`' final whole-branch review and fix pass.

Every git command in this procedure follows `/ship`'s git lock retry rule.

### `/ship` changes (`plugin/commands/ship.md`)

- **Step 3.** After `superpowers:writing-plans` writes the plan, and before
  the plan gate runs, add a `**Depends on:**` line under each task's
  `**Files:**` block: `none`, or the earlier tasks whose results it uses.
  Shared files need not be listed (`parallel-plan.py` orders them anyway), so
  a task whose only link to earlier tasks is shared files gets
  `**Depends on:** none`.
- **Step 4.** After the plan gate's `--verify-record` check passes, run
  `python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" waves <plan>`
  (fallback if the variable is not expanded:
  `~/.claude/skills/claude-kit/scripts/parallel-plan.py`). If every wave has
  one task, implement as today with `superpowers:executing-plans`. Otherwise
  use `claude-kit:parallel-tasks`. If it exits non-zero, write a `Ruling:`
  ledger line with its messages and implement as today: this is not a stop
  rule, because the plan is still executable one task at a time.
- **Git lock retry** (a rule for every step). Any git command in this
  repository, in the main checkout or any worktree, that fails with
  `Unable to create '...lock': File exists` or `cannot lock ref` is retried
  after 5 seconds, up to 5 times. All worktrees share one `.git` directory,
  so concurrent task worktrees (and, later, concurrent `/ship` runs) can
  collide on its locks. A command still failing after that is handled like
  any other failed command.

## Decisions

- **Build on the plan gate** rather than parse plans separately: it already
  requires `**Files:**` per task and owns the plan rules. This spec ships
  after the plan gate merges. (User decision.)
- **Ship parallel tasks before `/ship-many`**, as a separate spec. (User
  decision, after the spec gate found the original combined spec to be two
  subsystems.)
- **Default wave size 3.** (User decision.)
- **Overlap comes from the existing `**Files:**` block**, not a new field.
  Only dependencies that do not show as shared files need a new line.
- **A missing `**Depends on:**` line means "after every earlier task"**, so
  existing plans, and plans written without the line, run exactly as today.
- **File overlaps add implicit dependencies on earlier tasks**, so tasks that
  share a file always run in plan order.
- **Task worktrees branch from the feature branch's HEAD and merge back with
  `--no-ff` in task order**, so each task stays visible in history and the
  merge order is deterministic.
- **A failed subagent task, or a failing `waves` run, falls back to
  one-at-a-time work** rather than stopping `/ship`: the plan is still
  executable, just not in parallel.
- **Ledger lines are written per task as soon as it lands**, so a resumed run
  never redoes merged work.
- **The lock retry covers every git command in the repo**, because every
  worktree shares the same `.git` locks.

## Success criteria

1. `pytest tests/test_parallel_plan.py` passes, with tests that:
   - a plan with no `**Depends on:**` lines gives one task per wave;
   - `none` on every task with disjoint paths gives waves of at most `--max`;
   - a shared path forces plan order;
   - a directory path (`src/`) overlaps a file under it;
   - a root file (`CLAUDE.md`) counts as a path, and two tasks sharing only
     it are ordered;
   - a `:LINE-LINE` suffix is ignored; `.gitignore` is a path; `0001`,
     `0.8.0` and `origin/main` are not;
   - a plan with no tasks prints `{"waves": []}`;
   - a declared dependency forces a later wave;
   - a forward or unknown dependency, a repeated task in one list
     (`Task 1, Task 1`), and a duplicate `**Depends on:**` line, exit 1;
   - `--max 0` and a missing file exit 2.
2. `pytest tests/test_spec_lint.py` passes, with `P10-depends` tests: `none`
   passes, `Task 1, Task 2` on Task 3 passes, `Task 3` on Task 2 fails, an
   unknown task fails, `Task 1, Task 1` fails, `Task 1 and Task 2` fails,
   `none.` fails, `Task 1,Task 2` passes, two `**Depends on:**` lines in
   one task fail, and a task without the line passes.
3. Structure tests pass: `tests/test_parallel_tasks_skill.py` asserts the
   skill's frontmatter (`name: parallel-tasks`, a description starting
   "Use when", no `disable-model-invocation`), that it names
   `parallel-plan.py`, `git worktree add`, `git merge --no-ff`,
   `git worktree remove --force`, `git branch -D`, and
   `superpowers:executing-plans`, that the subagent prompt names both lock
   messages, that it skips tasks with a `complete` ledger line, and that its
   resume check uses `git log --merges --format=%P` and its merge check uses
   `git rev-list --count`;
   `tests/test_ship_command.py` asserts step 3 adds `**Depends on:**`,
   step 4 runs `parallel-plan.py waves`, names `claude-kit:parallel-tasks`
   and falls back on a non-zero exit, and the lock retry rule names both
   lock messages.
4. Back-compat check: `parallel-plan.py waves` on every plan in
   `docs/superpowers/plans/` that has no `**Depends on:**` line prints one
   task per wave. The command output is
   in the PR.
5. Smoke check, run by hand because the plugin loads from the main checkout
   until merge: in a scratch clone of the feature branch outside the
   workspace, on a local branch that is never pushed, the executing session
   follows `plugin/skills/parallel-tasks/SKILL.md` itself, using the clone's
   scripts, on `tests/fixtures/parallel/plan.md`. The fixture plan has
   `**Goal:**` and `**Spec:**` lines (the `**Spec:**` line points at this
   spec) and a Global Constraints section. Its Task 1
   and Task 2 each add one module and its test under `smoke/` with
   `**Depends on:** none`; Task 3 adds a module that uses both, with
   `**Depends on:** Task 1, Task 2`; its Global Constraints name
   `pytest tests smoke` as the suite. The check passes when
   `parallel-plan.py waves` prints `{"waves": [[1, 2], [3]]}`, `git log --merges` shows
   the two task merges, `pytest tests smoke` passes, and `git worktree list`
   shows no task worktree afterwards. The output is in the PR, and the clone
   is deleted.
6. `pytest tests/test_parallel_tasks_skill.py` also checks the docs:
   `conventions/spec-driven-development.md` describes `**Depends on:**`, and
   ADR 0017 exists and has a row in `knowledge/decisions/README.md`. A manual
   check confirms `plugin.json` says `0.8.0`.
7. `pytest` and `ruff check plugin tests; ruff format --check plugin tests`
   pass, locally and in CI.
