# `/ship` keeps its main session lean Implementation Plan

- **Status:** approved
- **Date:** 2026-10-20

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/ship`'s main session coordinate instead of doing the work: the spec gate sends the user to a fresh session, a subagent writes and gates the plan, implementation always runs in subagents, step 6 reuses step 4's final review, and `token-report.py --ship` measures runs.

**Architecture:** `/ship` (`plugin/commands/ship.md`), `spec-gate` and `parallel-tasks` are Markdown prompts whose text tests pin with string assertions. The change rewrites `ship.md` steps 3, 4, 6 and 12, the spec gate's step-7 pass message and three inline paths of `parallel-tasks`, adds a `--ship` mode to the standard-library script `plugin/scripts/token-report.py`, writes ADR 0037 (amending ADR 0017), updates one conventions section and bumps the plugin to 0.26.0.

**Tech Stack:** Markdown, Python 3 (standard library; pytest, ruff), JSON.

**Spec:** `docs/superpowers/specs/2026-10-20-lean-ship-orchestrator-design.md`

## Context for the executor

This repo is claude-kit: a Claude Code plugin under `plugin/` plus workspace
conventions under `conventions/` and ADRs under `knowledge/decisions/`.
`tests/helpers.py` exports `PLUGIN` (`REPO / "plugin"`), `REPO`,
`load_module(path, name)` and `run_script(script, *args)` (returns a
`subprocess.CompletedProcess` with text `stdout`/`stderr`).

In `tests/test_ship_command.py`, `_step(n)` returns step `n` of `ship.md` with
whitespace collapsed to single spaces; steps split on lines that start, at
column 0, with `<digits>. `. Steps are numbered lists whose continuation lines
are indented 3 spaces (4 for steps 10–12). Block-quoted lines inside a step
start, after that indentation, with `> `.

SDD means `superpowers:subagent-driven-development`: a skill that runs each
plan task through a fresh implementer subagent plus a per-task review, writes
`Task N: complete` ledger lines in the same ledger workspace as
`superpowers:executing-plans`, and ends with a whole-branch final review and
`superpowers:finishing-a-development-branch`.

Decided in the spec (do not relitigate): `/ship-fast` and `/ship-many` are not
edited; the gates' rubrics and records are not edited; no superpowers skill is
edited; `/ship` steps 0–2, 5 and 7–11 are not edited.

## Global Constraints

- Python: standard library only in `plugin/scripts/token-report.py`.
- Every line of Python must fit ruff's 88-character limit; split long string literals by hand.
- `ruff check plugin tests` and `ruff format --check plugin tests` must be clean; run `ruff format <file>` on any Python file you touch.
- `pytest` must pass in full before every commit.
- Plugin version: `0.25.0` → `0.26.0`.
- New ADR number: `0037`, file `knowledge/decisions/0037-lean-ship-orchestrator.md`.
- `git grep -n "executing-plans" plugin/commands/ship.md` must return no match (success criterion 4).
- `spec-lint.py --verify-record` prints `ok:` on the spec and on this plan (success criterion 3; the plan's gate record is committed before implementation starts).
- The repo is public: no private repo names or machine usernames in tracked files.
- A Markdown link must resolve (`test_relative_markdown_links_resolve`): never write a bracketed name followed by a parenthesised `.md` path as an example.
- Cost-weighted tokens = `input_tokens` + 1.25 × `cache_creation_input_tokens` + 0.1 × `cache_read_input_tokens` + 5 × `output_tokens`.

## Review Focus

- A transcript record repeated with the same `message.id` (Claude Code writes one API message on several records) must count once in `--ship` costs (Task 2 test `test_ship_rows_cost_main_subagents_and_peak`).
- A session that never invokes `/ship` must not appear in the `--ship` table (Task 2 test `test_cli_ship_lists_only_ship_sessions`).
- A `/ship` session with no `subagents` folder must still get a row, with subagent cost 0 (Task 2 test `test_ship_row_without_subagents`).
- `parallel-tasks` run by `/ship-fast` or by hand must keep implementing inline (Task 3 tests assert "any other caller" in each of the three places).
- Step 3 must not lose the existing behaviours its tests pin (resume by `**Spec:**` line, `decisions not approved`, 3a–3e, Plan questions path); the full `tests/test_ship_command.py` run covers them (Task 4).

## Plan questions (answered from the spec gate record)

- **Red suite after an SDD task:** fixed in the main session with `superpowers:systematic-debugging` before the next task, not by resuming the implementer; step 4's "Before every commit run the full test suite and lint" sentence stays (Task 4).
- **SDD's rulings and parked findings:** listed in the step-12 report only, under "anything left out and why"; the PR body is unchanged (Task 4).
- **Evidence that step 4's final review ran:** this session received that review's report during step 4 of this run; a run resumed in another session has no such report and runs step 6 as today (Task 4).
- **Criterion 4 wording:** step 4 names only SDD and `claude-kit:parallel-tasks`; neither `executing-plans` nor `test-driven-development` appears anywhere in `ship.md` (Task 4).
- **How `parallel-tasks` knows its caller is `/ship`:** from the session's command context (the run was started by `/ship` or `/claude-kit:ship`); its argument stays the plan path (Task 3).
- **Retry with an existing plan:** `/ship` copies the existing plan and its record to the scratchpad before the first dispatch; before the retry it restores them from those copies (the plan may be untracked) and deletes files the subagent created (Task 4).
- **`--ship` matching:** a session matches when any user record contains a `<command-name>` tag of `ship`, `/ship` or `/claude-kit:ship`; a headless `/ship-many` child matches when its transcript carries that tag; each session file is one row, so a run resumed across sessions gives several rows (Task 2).
- **`--ship` details:** peak context is the largest `input + cache_creation + cache_read` of any main-session assistant record; the date is the first record's `timestamp` (first 10 characters), else `-`; `--ship` uses the same file set as `--project`/`--all` and prints only the ship table instead of the normal report; the median line shows `median` and `-` in the id and date columns (Task 2).

---

### Task 1: Spec gate sends the user to a fresh session

**Files:**
- Modify: `plugin/skills/spec-gate/SKILL.md` (step 7, `**pass:**` bullet)
- Test: `tests/test_spec_gate_skill.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing test** (append to `tests/test_spec_gate_skill.py`)

```python
def test_pass_message_sends_the_user_to_a_fresh_ship_session():
    body = read("SKILL.md")
    step7 = body.split("7. **Report to the user.**", 1)[1]
    passed = step7.split("**pass:**", 1)[1].split("**fail:**", 1)[0]
    passed = " ".join(passed.split())
    assert "/clear" in passed
    assert "/claude-kit:ship docs/superpowers/specs/" in passed
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_spec_gate_skill.py::test_pass_message_sends_the_user_to_a_fresh_ship_session`
Expected: FAIL (assert "/clear" in passed).

- [ ] **Step 3: Edit the `**pass:**` bullet**

After "On yes, set the spec's Status bullet to `approved` (the hash ignores
that line, so the record stays valid)." add: the reply confirming it ends with
this line, the spec's repo-relative path filled in:
`Next: run /clear, then /claude-kit:ship docs/superpowers/specs/<file>.`
(write the commands in backticks as the spec does). The existing closing
sentence "When `/ship` runs this skill, it skips step 7's question" stays;
extend it with "and prints nothing".

- [ ] **Step 4: Run the test file**

Run: `pytest tests/test_spec_gate_skill.py`
Expected: all pass.

- [ ] **Step 5: Full suite, lint, commit**

Run `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`; all green.

```bash
git add plugin/skills/spec-gate/SKILL.md tests/test_spec_gate_skill.py
git commit -m "spec-gate: approval reply points to /clear and /claude-kit:ship"
```

### Task 2: `token-report.py --ship`

**Files:**
- Modify: `plugin/scripts/token-report.py`
- Test: `tests/test_token_report.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces (module-level, in `token-report.py`):
  - `SHIP_COMMANDS = {"ship", "/ship", "/claude-kit:ship"}`
  - `message_cost(usage: dict) -> float` — cost-weighted tokens of one usage dict (missing keys count 0).
  - `is_ship_session(path: Path) -> bool` — any `type == "user"` record whose message content (a string, or the `text` of list blocks) contains `<command-name>X</command-name>` with `X` in `SHIP_COMMANDS`.
  - `@dataclass ShipRow(sid: str, date: str, main: float, subagents: float, peak: int)` with property `total -> float` (`main + subagents`).
  - `transcript_cost(path: Path) -> tuple[float, int, str]` — (cost, peak context, date) of one transcript, counting each `message.id` once (assistant records without an id each count).
  - `ship_rows(files: list[Path]) -> list[ShipRow]` — one row per file for which `is_ship_session` is true, `sid = path.stem[:8]`; subagent cost is the sum of `transcript_cost` over `<file parent>/<file stem>/subagents/*.jsonl`.
  - `render_ship(rows: list[ShipRow]) -> str`.
  - CLI flag `--ship`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_token_report.py`)

```python
def ship_assistant(mid: str, inp: int, cc: int, cr: int, out: int) -> str:
    usage = {
        "input_tokens": inp,
        "cache_creation_input_tokens": cc,
        "cache_read_input_tokens": cr,
        "output_tokens": out,
    }
    message = {"id": mid, "usage": usage, "content": []}
    return json.dumps({"type": "assistant", "message": message})


def ship_user(text: str) -> str:
    record = {
        "type": "user",
        "timestamp": "2026-10-20T10:00:00Z",
        "message": {"content": text},
    }
    return json.dumps(record)


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def make_ship_project(root: Path, subagents: bool = True) -> Path:
    folder = root / "C--proj"
    write_lines(
        folder / "ship1.jsonl",
        [
            ship_user("<command-name>/claude-kit:ship</command-name> spec.md"),
            ship_assistant("m1", 100, 1_000, 10_000, 10),
            ship_assistant("m1", 100, 1_000, 10_000, 10),
            ship_assistant("m2", 200, 0, 20_000, 20),
        ],
    )
    if subagents:
        write_lines(
            folder / "ship1" / "subagents" / "agent-a.jsonl",
            [ship_assistant("m3", 1_000, 2_000, 0, 100)],
        )
    write_lines(
        folder / "plain.jsonl",
        [ship_user("hello"), ship_assistant("m9", 5, 0, 0, 1)],
    )
    return folder


def test_message_cost_weights_usage():
    mod = load_module(SCRIPT, "token_report")
    usage = {
        "input_tokens": 100,
        "cache_creation_input_tokens": 1_000,
        "cache_read_input_tokens": 10_000,
        "output_tokens": 10,
    }
    assert mod.message_cost(usage) == 2_400


def test_ship_rows_cost_main_subagents_and_peak(tmp_path):
    mod = load_module(SCRIPT, "token_report")
    folder = make_ship_project(tmp_path)
    rows = mod.ship_rows(sorted(folder.glob("*.jsonl")))
    assert [r.sid for r in rows] == ["ship1"]
    row = rows[0]
    assert row.date == "2026-10-20"
    assert row.main == 2_400 + 2_300  # m1 counted once
    assert row.subagents == 4_000
    assert row.total == 8_700
    assert row.peak == 20_200


def test_ship_row_without_subagents(tmp_path):
    mod = load_module(SCRIPT, "token_report")
    folder = make_ship_project(tmp_path, subagents=False)
    (row,) = mod.ship_rows(sorted(folder.glob("*.jsonl")))
    assert row.subagents == 0
    assert row.total == row.main


def test_cli_ship_lists_only_ship_sessions(tmp_path):
    make_ship_project(tmp_path)
    out = run_script(SCRIPT, "--all", "--root", str(tmp_path), "--ship")
    assert out.returncode == 0, out.stderr
    assert "ship1" in out.stdout and "plain" not in out.stdout
    for value in ("4,700", "4,000", "8,700", "20,200"):
        assert value in out.stdout, value
    assert out.stdout.strip().splitlines()[-1].startswith("median")
    assert "restart simulation" not in out.stdout
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_token_report.py`
Expected: the four new tests FAIL (`AttributeError: ... message_cost`, and the CLI rejects `--ship`); the five existing tests pass.

- [ ] **Step 3: Implement the interfaces above in `token-report.py`**

- `transcript_cost`: read JSONL as `scan` does (skip bad lines and non-dicts); date from the first record that has a string `timestamp` (`[:10]`); for `type == "assistant"` records with a dict `usage`, skip a `message.id` already seen in this file, else add `message_cost(usage)` and track the max of `sum(usage[k] for k in USAGE_KEYS)` as peak.
- `render_ship`: a header line `id        date          main  subagents      total   peak ctx`, then one line per row sorted by date then id, numbers as integers with thousands separators (`f"{round(x):,}"`), right-aligned; then a line starting with `median` (date column `-`) holding `statistics.median` of main, subagents, total and peak. With no rows, return `no /ship sessions found`.
- `main()`: add `--ship` (`action="store_true"`, help "one row per /ship session: main, subagent and total cost, peak context"). After the file list is built and found non-empty, print `render_ship(ship_rows(files))` instead of the normal report when `--ship` is set.
- Add one usage line to the module docstring: `token-report.py --ship [--project DIR | --all] [--root DIR]   cost of each /ship run`.

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_token_report.py`
Expected: all 9 pass.

- [ ] **Step 5: Full suite, lint, commit**

Run `ruff format plugin/scripts/token-report.py tests/test_token_report.py`, then `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`; all green.

```bash
git add plugin/scripts/token-report.py tests/test_token_report.py
git commit -m "token-report: --ship lists each /ship run's main, subagent and total cost"
```

### Task 3: `parallel-tasks` uses SDD's task loop under `/ship`

**Files:**
- Modify: `plugin/skills/parallel-tasks/SKILL.md` (steps 2 and 3)
- Test: `tests/test_parallel_tasks_skill.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: the three caller conditions Task 4's step 4 relies on (no names to share).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_parallel_tasks_skill.py`)

```python
SDD = "superpowers:subagent-driven-development"


def _flat(text):
    return " ".join(text.split())


def test_one_task_wave_uses_sdd_under_ship():
    part = body().split("**One task:**", 1)[1].split("**Several tasks:**", 1)[0]
    part = _flat(part)
    assert "`/ship`" in part and SDD in part
    assert "any other caller" in part


def test_failed_task_fallback_uses_sdd_under_ship():
    text = body()
    part = text.split("A failed task's branch is not merged", 1)[1]
    part = _flat(part.split("**After the wave:**", 1)[0])
    assert "`/ship`" in part and SDD in part
    assert "any other caller" in part


def test_non_zero_script_fallback_uses_sdd_under_ship():
    part = body().split("2. **Waves.**", 1)[1].split("3. **Each wave", 1)[0]
    part = _flat(part)
    assert "non-zero" in part
    assert "`/ship`" in part and SDD in part
    assert "any other caller" in part
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_parallel_tasks_skill.py`
Expected: the three new tests FAIL; the others pass.

- [ ] **Step 3: Edit the skill**

- Setup section: add a bullet: **Caller.** The caller is `/ship` when this
  session's run was started by `/ship` or `/claude-kit:ship`; otherwise
  (`/ship-fast` or a manual run) it is any other caller. SDD and
  `executing-plans` share one ledger workspace, so the ledger step 1 sets up
  is the one SDD's task loop writes to.
- Step 2 (non-zero exit): after the `Ruling:` line, when the caller is
  `/ship`, the remaining tasks run one at a time through
  `superpowers:subagent-driven-development`'s task loop (one implementer
  subagent per task, its task review and fix rounds, and its
  `Task N: complete` ledger line) in the feature worktree; for any other
  caller, one at a time with `superpowers:executing-plans`, as today.
- Step 3 "One task": when the caller is `/ship`, run it through SDD's task
  loop (same wording) in the feature worktree; for any other caller,
  implement it inline exactly as `executing-plans` does, as today.
- Step 3 failed-task sentence: when the caller is `/ship`, run that task
  through SDD's task loop in the feature worktree from the merged HEAD; for
  any other caller, implement it inline from the merged HEAD, as today;
  either way write its `complete` line after its commit. Keep the sentence
  opening "A failed task's branch is not merged" and the `**After the wave:**`
  label (the test splits on both).
- Each of the three passages (step 2, "One task", failed task) names
  `superpowers:subagent-driven-development` in full and the words "any other
  caller"; the abbreviation SDD alone is not enough. The Caller bullet
  defines SDD at first use.
- Step 4 (final review) is unchanged. Keep every existing command string
  (`superpowers:executing-plans` must stay in the file).

- [ ] **Step 4: Run the test file**

Run: `pytest tests/test_parallel_tasks_skill.py`
Expected: all pass.

- [ ] **Step 5: Full suite, lint, commit**

Run `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`; all green.

```bash
git add plugin/skills/parallel-tasks/SKILL.md tests/test_parallel_tasks_skill.py
git commit -m "parallel-tasks: under /ship, inline tasks run through SDD's task loop"
```

### Task 4: `/ship` steps 3, 4, 6 and 12

**Files:**
- Modify: `plugin/commands/ship.md` (steps 3, 4, 6, 12 only)
- Test: `tests/test_ship_command.py`

**Depends on:** none

**Interfaces:**
- Consumes: Task 3's caller condition (by name only: `claude-kit:parallel-tasks`).
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_ship_command.py`)

```python
def _raw_step(n):
    match = re.search(rf"^{n}\. (.*?)(?=^\d+\. |\Z)", SHIP, re.M | re.S)
    assert match, n
    return match.group(1)


def _quoted(n):
    lines = [line.strip() for line in _raw_step(n).splitlines()]
    return " ".join(" ".join(x[1:] for x in lines if x.startswith(">")).split())


def _unquoted(n):
    lines = [line.strip() for line in _raw_step(n).splitlines()]
    return " ".join(" ".join(x for x in lines if not x.startswith(">")).split())


def test_step_three_dispatches_a_plan_subagent():
    assert "general-purpose subagent" in _step(3)
    prompt = _quoted(3)
    for needle in (
        "superpowers:writing-plans",
        "claude-kit:plan-gate",
        "steps 1–6",
        "Verdict:",
        "Record:",
    ):
        assert needle in prompt, needle


def test_step_three_does_not_write_the_plan_itself():
    assert "superpowers:writing-plans" not in _unquoted(3)


def test_step_four_always_implements_in_subagents():
    step = _step(4)
    assert "superpowers:subagent-driven-development" in step
    assert "claude-kit:parallel-tasks" in step
    assert "non-zero" in step and "not a stop rule" in step
    assert "executing-plans" not in step
    assert "finishing-a-development-branch" in step and "not run" in step


def test_step_six_reuses_step_four_final_review():
    step = _step(6)
    assert "final whole-branch review" in step
    assert "superpowers:requesting-code-review" in step


def test_ship_never_names_executing_plans():
    assert "executing-plans" not in SHIP
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_ship_command.py`
Expected: the five new tests FAIL; every existing test passes.

- [ ] **Step 3: Rewrite step 3's plan-writing part**

Keep step 3's resume logic (existing plan by `**Spec:**` line,
`--verify-record`, `ok:` → step 4, `decisions not approved` handling) and
everything from "On `pass`, set the plan's Status to `approved`" through (3e)
unchanged. Replace the text from "If there is no plan, use
`superpowers:writing-plans` ..." up to and including "...run the
`claude-kit:plan-gate` skill on the plan, steps 1–6 (step 7 is not shown)."
with:

1. Whenever step 3 would write a plan or run the plan gate (no plan exists,
   or `--verify-record` on the existing plan prints neither `ok:` nor
   `decisions not approved`), `/ship` does neither itself: it dispatches one
   **new** general-purpose subagent on the session's own model (no `model`
   override), with no conversation, summary or other context, and only this
   prompt (absolute paths), block-quoted (every line starts with `> `),
   copied verbatim from the spec's Design §2:

   > In the git worktree at `<feature worktree root>`, the approved spec is
   > `<spec>` and its gate record is `<spec gate record>`. Existing plan:
   > `<plan>` (or `none`).
   >
   > If the existing plan is `none`, write the implementation plan for the
   > spec using the `superpowers:writing-plans` skill, saved as
   > `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md`. Where the spec leaves a
   > choice open, prefer one the spec, its ADRs or the existing code already
   > imply. Answer every question under `## Plan questions` in the spec gate
   > record in the task it affects (none if the section is missing). Add a
   > `**Depends on:**` line under each task's `**Files:**` block: `none`, or
   > the earlier tasks whose results it uses (`Task 1, Task 3`); a task whose
   > only link to earlier tasks is shared files gets `none`. Do not write a
   > new plan over an existing one; the plan gate's own fixes to it are
   > expected.
   >
   > Then run the `claude-kit:plan-gate` skill on the plan, steps 1–6 only (do
   > not run step 7 and do not ask anything). Do not commit and do not offer
   > an execution choice. Return exactly three lines: `Plan: <repo-relative
   > path>`, `Verdict: pass | pass-with-decisions | fail`, and `Record:
   > <repo-relative path of the plan gate record>` (`Record: none` when the
   > gate stopped at `P4-spec-gated` and wrote no record).

2. After the prompt: `<feature worktree root>` is the absolute path of the
   feature worktree from step 2 (never the main checkout); `<spec>`,
   `<spec gate record>` (`docs/superpowers/gates/<spec file name>`) and
   `<plan>` are absolute paths inside it.
3. The check: in that worktree, the plan file exists, its `**Spec:**` line
   names the spec, and the reported verdict matches the record's `Verdict`
   line (for `Record: none`: the plan exists and no record was written).
   Before the first dispatch with an existing plan, copy that plan and its
   record (if any) to the scratchpad. On a
   failed check, delete any plan file and record the subagent created,
   restore an existing plan it was given and that plan's existing record from
   those copies, and dispatch it once more with the same
   prompt; a second failure is debugged with
   `superpowers:systematic-debugging`, not a stop rule.
4. Then "From here `/ship` acts on the reported verdict, reading the
   Plan-introduced decisions and Open items from the record file, and makes
   every commit itself." followed by the unchanged "On `pass`, set the
   plan's Status to `approved`, commit the plan and its record
   (`docs/superpowers/gates/plans/<plan file name>`) ..." text through (3e).

Items 1–4 are prose inside step 3, indented 3 spaces like the rest of the
step (the block quote as `   > `); never write them as a numbered list or
start any line at column 0 with `<digits>. `, because `_step(n)` splits
steps there. The phrase `superpowers:writing-plans` must appear only inside the
block-quoted prompt. Keep `**Plan gate:**` in step 3 (an existing test pins
it): put it at the start of item 4's sentence.

- [ ] **Step 4: Rewrite step 4's implementation choice**

Keep the opening `--verify-record` sentence, the `parallel-plan.py waves`
command and its fallback path, the "review checkpoints are progress notes"
sentence, "Before every commit run the full test suite and lint from
`CLAUDE.md`; commit per task.", and the Docker sentences. Replace the choice
with:
- The script exits non-zero: write a `Ruling:` ledger line with its messages,
  then implement with `superpowers:subagent-driven-development` on the plan;
  this is not a stop rule, because the plan is still executable one task at a
  time.
- Every wave has one task: `superpowers:subagent-driven-development`.
- Otherwise: `claude-kit:parallel-tasks` with `<plan>` as its argument (under
  `/ship` its inline paths use SDD's task loop).

Then add:
- `/ship`'s override applies to SDD as to every skill: no question, menu or
  checkpoint inside it pauses the run; an SDD stop reason that is not a
  `/ship` stop rule is settled with a `Ruling:` ledger line; a ruling on an
  irreversible, destructive or security-sensitive action never carries the
  action out unless the spec requires it: it declines the action and records
  why.
- SDD's closing `superpowers:finishing-a-development-branch` is not run:
  step 11 does the clean-up.
- After each task SDD marks complete, the main session runs the full test
  suite and lint from `CLAUDE.md` with quiet output and confirms the task's
  commit is on the branch; a red suite is debugged and fixed in the main
  session with `superpowers:systematic-debugging` (not by resuming the
  implementer) before the next task.
- Keep "A failing test or an unclear instruction is debugged with
  `superpowers:systematic-debugging`, not escalated."
Remove every mention of `executing-plans` and `test-driven-development`.

- [ ] **Step 5: Rewrite step 6**

- If this session received, during step 4 of this run, the report of the
  final whole-branch review that step 4's skill runs (SDD's final review or
  `parallel-tasks`' final review), step 6 does not run
  `superpowers:requesting-code-review`; the findings that review fixed are
  the review findings for the PR and the report.
- Otherwise (for example a run resumed in another session that found every
  task complete and did not reach a final review), step 6 runs as today:
  `superpowers:requesting-code-review` on `origin/main..HEAD`, then
  `superpowers:receiving-code-review`; fix every finding you can verify;
  commit, re-run tests, push.
- A finding that needs a scope, product or behaviour decision the spec does
  not settle is a stop rule, whichever review raised it.

- [ ] **Step 6: Edit step 12**

"the review findings you fixed" becomes "the review findings you fixed (from
whichever review ran in step 4 or step 6)", and "anything left out and why"
gains "(including SDD's rulings and any findings it parked or deferred)".
Keep "Plan decisions (auto-approved)" and "Learnings summary from step 7".

- [ ] **Step 7: Run the tests and the grep**

Run: `pytest tests/test_ship_command.py` → all pass.
Run: `git grep -n "executing-plans" plugin/commands/ship.md` → no output (exit 1).

- [ ] **Step 8: Full suite, lint, commit**

Run `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`; all green.

```bash
git add plugin/commands/ship.md tests/test_ship_command.py
git commit -m "/ship: subagent writes the plan, SDD implements, one final review"
```

### Task 5: ADR 0037, conventions, ADR 0017 amendment, version 0.26.0

**Files:**
- Create: `knowledge/decisions/0037-lean-ship-orchestrator.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `knowledge/decisions/0017-parallel-plan-tasks.md`
- Modify: `conventions/spec-driven-development.md` (`## Parallel plan tasks`)
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `docs/superpowers/README.md`
- Test: `tests/test_plugin_manifest.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing test**

In `tests/test_plugin_manifest.py`, rename `test_version_is_0_25_0` to
`test_version_is_0_26_0` and assert `data["version"] == "0.26.0"`.

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_plugin_manifest.py::test_version_is_0_26_0`
Expected: FAIL (`'0.25.0' == '0.26.0'`).

- [ ] **Step 3: Bump the version**

`plugin/.claude-plugin/plugin.json`: `"version": "0.26.0"`.

- [ ] **Step 4: Write ADR 0037**

Format as ADR 0036: `# ADR 0037: /ship's main session coordinates; subagents write the plan and the code`,
`- **Status:** accepted`, `- **Date:** 2026-10-20`, then `## Context`,
`## Decision`, `## Consequences` with the content of the spec's "ADR 0037"
paragraph (Context: tokens go mostly to the main session, whose context grows
through brainstorming, plan writing and inline implementation and is re-read
every turn; median run 18.0M cost-weighted tokens, 391k peak context, over 66
runs, figures that overstate cost because repeated records were counted.
Decision: the four bullets: fresh session from the spec gate's approval
message; a fresh subagent writes and gates the plan while `/ship` acts on the
verdict and commits; step 4 always implements through SDD or
`claude-kit:parallel-tasks`, whose inline paths under `/ship` use SDD's task
loop; step 6 reuses step 4's final review. Consequences: as the spec states,
including that runs are judged on total cost with `token-report.py --ship`,
that it amends ADR 0017 for inline tasks under `/ship`, and that `/ship-fast`
is not affected).

- [ ] **Step 5: Index and amend**

- `knowledge/decisions/README.md`: add after the 0036 row:
  `| [0037](0037-lean-ship-orchestrator.md) | `/ship`'s main session coordinates; subagents write the plan and the code | accepted | 2026-10-20 |`
  and change the 0017 row's status cell to `accepted; amended by 0037`.
- `knowledge/decisions/0017-parallel-plan-tasks.md`: Status line becomes
  `- **Status:** accepted; amended by 0037 ([ADR 0037](0037-lean-ship-orchestrator.md): under `/ship`, one-task waves and inline fallbacks run through SDD's task loop)`.

- [ ] **Step 6: Conventions**

In `conventions/spec-driven-development.md`, `## Parallel plan tasks`: the
sentence "Under `/ship`, a wave with more than one task runs through
`claude-kit:parallel-tasks`: one subagent and git worktree per task, merged
back in task order (ADR 0017 link)." gains, before the ADR 0017 link or as a
following clause, that every other task under `/ship` runs through
`superpowers:subagent-driven-development` (ADR 0037 link,
`../knowledge/decisions/0037-lean-ship-orchestrator.md`). Add one new sentence
to the section: under `/ship`, a fresh subagent writes the plan and runs the
plan gate on it, and `/ship` acts on the verdict.

- [ ] **Step 7: Spec index**

Run: `python plugin/scripts/spec-index.py docs/superpowers` (adds the plan's
row to `docs/superpowers/README.md`; it may already be there).

- [ ] **Step 8: Check both gate records (success criterion 3)**

Run: `python plugin/scripts/spec-lint.py --verify-record docs/superpowers/specs/2026-10-20-lean-ship-orchestrator-design.md`
Run: `python plugin/scripts/spec-lint.py --verify-record docs/superpowers/plans/2026-10-20-lean-ship-orchestrator.md`
Expected: each prints a line starting `ok:`.

- [ ] **Step 9: Full suite, lint, commit**

Run `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`; all green.

```bash
git add knowledge/decisions conventions/spec-driven-development.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py docs/superpowers/README.md
git commit -m "ADR 0037: /ship's main session coordinates; version 0.26.0"
```
