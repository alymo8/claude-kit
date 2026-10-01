# Plan gate: linter rules and independent plan reviewer

- **Status:** approved
- **Date:** 2026-09-30

## Purpose

The spec gate (`docs/superpowers/specs/2026-09-30-spec-gate-design.md`)
checks a spec on the user's behalf, because the user does not read specs in
full. The user does not read implementation plans either. A plan is the only
context its executor gets, so a gap in a plan (a spec requirement that no
task covers, a task that cannot be carried out from the plan alone, a choice
the spec never made) reaches the build unchecked. Then it is either guessed
silently or fires a `/ship` stop rule partway through.

This work adds a **plan gate**, built on the spec gate's pieces:

1. **Plan rules in the linter.** `spec-lint.py` applies a plan rule set to
   files under `docs/superpowers/plans/`.
2. **A fresh-context plan reviewer.** A new subagent reads the plan, its spec
   and the repo. It checks coverage of the spec, whether each task can be done
   cold, task order and code claims, and it lists the decisions the plan makes
   that the spec did not settle.

The user signs off only on **plan-introduced decisions**. A plan that passes
and introduces none goes straight on to execution, with a one-line notice.

This spec also changes how design review works during spec creation. The
author no longer pauses for the user's approval after each design section,
because the gates do that review. The user still takes part by answering
decision questions and giving instructions.

**Prerequisite:** the spec gate is implemented and merged (PR #18). This spec
extends `plugin/scripts/spec-lint.py`, `/ship` and the gate records under
`docs/superpowers/gates/`, and mirrors the `claude-kit:spec-gate` skill.

## Scope

**In:**

- `plugin/scripts/spec-lint.py`: a plan rule set, chosen when the file is
  in a folder named `plans`; plan hashing; plan gate-record verification.
- `plugin/skills/plan-gate/SKILL.md` (new): the gate procedure, invocable as
  `/plan-gate <plan.md>`.
- `plugin/skills/plan-gate/rubric.md` (new): the plan reviewer's rubric and
  finding format.
- Plan gate records under `docs/superpowers/gates/plans/` (new).
- `plugin/commands/ship.md`: step 3 runs the plan gate after writing the plan;
  step 4 verifies the plan record before implementing; a new stop rule; step 7
  links the plan gate record in the PR body.
- Workspace `CLAUDE.md`:
  - "Specs and plans": run `claude-kit:plan-gate` on a plan after writing it,
    before offering an execution choice.
  - A new rule: during spec creation, present the design once and write the
    spec, with no approval pause between design sections.
- `conventions/spec-driven-development.md`: a "Plan gate" section next to the
  "Spec gate" section, and the plan shape the linter enforces.
- ADR 0016 (new):
  `knowledge/decisions/0016-plan-gate-signs-off-on-new-decisions-only.md` (new),
  plus its row in `knowledge/decisions/README.md`.
- Tests: additions to `tests/test_spec_lint.py` and
  `tests/test_ship_command.py`, `tests/test_plan_gate_skill.py` (new) in the
  style of `tests/test_spec_gate_skill.py`, and a check in `tests/test_docs.py` for the
  two `CLAUDE.md` rules.
- A reviewer eval: `tests/fixtures/plan-gate/` (new) with seeded-defect plans,
  their specs, and a `README.md` describing the manual eval.
- `plugin/.claude-plugin/plugin.json`: version 0.6.0 → 0.7.0, and the
  description gains "spec and plan gates".

**Out:**

- Editing the superpowers plugin (`superpowers:writing-plans`,
  `superpowers:brainstorming`). The gate and the no-pause rule are enforced
  through `CLAUDE.md` and `/ship`.
- Re-gating a plan while it is being executed. The gate runs before execution
  starts. Checking off steps does not make the record stale (see Plan hashing).
  Other edits made during execution follow the existing "update the spec or add
  an ADR" rule.
- Running the LLM reviewer eval in CI (same reason as the spec gate).
- Retrofitting the five existing plans to pass the linter. They are used only
  for a back-test.
- Parallel execution (the parallel runner spec).
- Editing the merged spec-gate spec (for example, its Out line about plans).
  Any edit would change its hash and invalidate its gate record.

## Design

### Required plan shape

The shape that `superpowers:writing-plans` produces, plus the kit's Status and
Date bullets (`conventions/spec-driven-development.md`), as in
`docs/superpowers/plans/2026-09-29-repo-audit-skills.md`:

- A `# Title` H1, plus `- **Status:**` and `- **Date:**` bullets (the same
  values as specs).
- `**Goal:**` and `**Spec:**` lines before the first task. `**Spec:**` holds
  one backticked repo path to a spec.
- Tasks as `### Task N: <name>` headings, numbered 1, 2, 3… with no gaps or
  repeats.
- In each task: a `**Files:**` line followed by `- Create:`, `- Modify:` or
  `- Test:` bullets with backticked paths; at least one step containing
  `Run:` (or a fenced command block) followed later in the same step by
  `Expected:`; and a step whose bold label contains `Commit`.
- A **step** is the lines from a `- [ ] **Step N:` bullet (checked or not)
  up to the next such bullet, the next `###` or higher heading, or end of
  file. A **fenced command block** is a fence with no info string or one
  tagged `bash`, `sh`, `shell`, `powershell`, `pwsh` or `console`. File-content
  fences such as `~~~~python file=...` are not command blocks. `Run:` and
  `Expected:` count only outside fences.

### Plan rules in `plugin/scripts/spec-lint.py`

A file is linted as a plan when its parent folder is named `plans`; otherwise
the spec rules apply, unchanged. The CLI does not change:

```
python spec-lint.py PLAN.md [--root DIR]
python spec-lint.py --hash PLAN.md
python spec-lint.py --verify-record PLAN.md
```

Output, exit codes, line-number conventions and fenced-code handling are the
same as the spec rules.
Plan rules:

| Rule | Check |
|---|---|
| `P1-status` | Same as `L1-status`. |
| `P2-date` | Same as `L2-date`. |
| `P3-header` | `**Goal:**` and `**Spec:**` lines exist before the first `### Task` heading, and the `**Spec:**` line holds exactly one backticked path. When P3 reports the `**Spec:**` line, P4 is skipped. |
| `P4-spec-gated` | The `**Spec:**` path exists under `--root`, and `--verify-record` on that spec would exit 0. The message carries the spec's reason (`missing`, `not passed`, `stale`), or `spec not found: <path>` when the path does not exist. |
| `P5-tasks` | At least one `### Task N:` heading; numbers run 1..N in order. Each heading is compared with the previous heading's number + 1 (the first with 1); a heading that differs is one violation at its line, and a heading that matches is not a violation. |
| `P6-task-parts` | Each task has a `**Files:**` line, a `Run:`/`Expected:` pair (or fenced block plus `Expected:`), and a `Commit` step. One violation per missing part, at the task heading's line. |
| `P7-placeholder` | `L5-placeholder`'s word list and exceptions (backticked spans, double-quoted text) apply to the whole plan; the `etc.` part does not apply to plans. |
| `P8-empty` | Same as `L6-empty`. |
| `P9-path` | Every backticked path in a `- Modify:` bullet under a task's `**Files:**` line exists under `--root`, or appears in a `- Create:` or `- Test:` bullet of the same or an earlier task. "Path" uses `L8-path`'s definition, after stripping a `:N` or `:N-M` line suffix. `- Create:` and `- Test:` paths are not checked, because the writing-plans template lists a new test file under `- Test:`. |

### Plan hashing and records

**Hash mode** for a plan normalises line endings, removes the first Status
bullet outside fences (as for specs), and rewrites every `- [x]` / `- [X]` at
line start (leading spaces allowed) outside fences to `- [ ]` before
hashing. So approving a plan and ticking steps during execution both keep the
record valid. Any other edit invalidates it.

**Plan gate record:** `docs/superpowers/gates/plans/<plan-basename>`. Plans
get their own folder so a plan and a spec can never share a record name.

```
# Plan gate: <plan title>

- **Plan:** docs/superpowers/plans/<plan-basename>
- **Plan SHA-256:** <spec-lint.py --hash PLAN>
- **Spec:** <spec path from the plan>
- **Spec SHA-256:** <spec-lint.py --hash SPEC>
- **Verdict:** pass | pass-with-decisions | fail
- **Date:** YYYY-MM-DD
- **Rounds:** <n>

## Plan-introduced decisions
## Findings fixed
## Open
```

**`--verify-record PLAN.md`** exits 0 only when the record exists, its
Verdict is `pass`, or `pass-with-decisions` with a line
`- **Decisions approved:** YYYY-MM-DD`, and both recorded hashes equal the
current hashes of the plan and of the spec named in the plan's current
`**Spec:**` line (a change to that line already changes the plan hash).
Reasons are checked in this order, and the first that applies is printed:
`missing` → `not passed` → `stale` → `decisions not approved`. A missing or
unreadable spec counts as `stale`. On success it prints `ok: <record path>`, as for specs. Otherwise it prints
`missing`, `not passed`, `stale` or `decisions not approved`, then `: ` and
the record path, and exits 1. So a spec
edit after planning invalidates the plan's record.

### `plugin/skills/plan-gate/rubric.md`

The reviewer gets the plan path, the spec path, the repo and this file, never
the conversation. It must:

1. **Coverage map.** For each In-scope item and each success criterion in the
   spec, name the task(s) that deliver it. An unmapped item is `blocking`.
   Plan work that no spec item asks for is `blocking` (scope creep).
2. **Cold execution.** For each task, list what an executor with only the
   repo and this plan would have to ask before doing it. Each unanswered
   question is `blocking`.
3. **Order.** A task that uses a file, function or command that only a later
   task creates is `blocking`.
4. **Code claims.** Each existing path, function, command or behaviour the
   plan relies on is checked against the repo. A false claim is `blocking`.
5. **Verification.** Each task writes a failing test before its
   implementation, unless it changes only docs or config. Each run step states
   its expected output. Some task checks each of the spec's success criteria.
   A gap is `blocking`.
6. **Plan-introduced decisions.** List the choices the plan makes that the
   spec does not settle and that concern scope, architecture, product
   boundary, data or irreversible actions, or the interpretation of the spec.
   File names, helper structure and test layout are not decisions. These are
   not findings; they drive the sign-off.

Output format, parsed by hand like the spec rubric:

```
## Coverage
- <spec item> → Task <n>[, <m>] | UNMAPPED

## Findings
### [blocking] <title>
- **Line:** <plan line number or task>
- **Problem:** <what is wrong, quoting the plan>
- **Fix:** <a concrete change to the plan>

### [minor] <title>
...

## Plan-introduced decisions
- <decision> (Task <n>) — spec says: <nothing | quote>
```

### `plugin/skills/plan-gate/SKILL.md`

`/plan-gate <plan.md>` (default: the newest plan under
`docs/superpowers/plans/`). The procedure mirrors the spec gate:

1. **Lint** the plan. If it has no Status bullet, add `- **Status:** draft`.
   Fix every other violation until the linter exits 0; if `P4-spec-gated` is
   then the only one left, stop with verdict `fail`: the spec must be gated
   first. Write no record; report that the spec must pass
   `claude-kit:spec-gate` first. Never edit the spec from the plan gate.
2. **Review round** with a new general-purpose subagent given the plan path,
   the spec path and `rubric.md`.
3. **Fix** each `blocking` finding in the plan (and `minor` ones when clear),
   then re-lint. A finding whose fix would change what the spec asks for is a
   **spec finding**. Do not fix it in the plan; it goes to Open.
4. **Repeat** steps 2–3 until a round has no `blocking` findings, up to 3
   rounds.
5. **Verdict.**
   - **pass:** clean lint, last round has no `blocking` findings, no spec
     findings, and no plan-introduced decisions.
   - **pass-with-decisions:** the same, but the last round listed
     plan-introduced decisions.
   - **fail:** anything else.
6. **Record:** write the gate record, with hashes computed after the last
   plan edit. Its `## Plan-introduced decisions` section holds the last
   round's list; that exact list is what the user approves.
7. **Report to the user:**
   - **pass:** one line, "Plan gate passed in N rounds; no new decisions",
     plus the plan path (path only; never open it). Set the plan's Status to
     `approved` (the hash ignores it). Continue straight to the
     execution choice, with no further sign-off.
   - **pass-with-decisions:** "Plan gate passed in N rounds. The plan makes
     these decisions the spec doesn't:", then the list, then "OK?". On yes,
     add `- **Decisions approved:** <today>` to the record and set the plan's
     Status to `approved`. Neither changes either hash. On a change request, edit the plan and rerun the
     gate from step 1.
   - **fail:** each open item as a direct question with options and a
     recommendation. Spec findings name the spec section to change. After the
     user answers, update the plan (or the spec, which is then re-gated) and
     rerun.

### `/ship` changes (`plugin/commands/ship.md`)

- **Step 3, Plan.** After writing the plan, run the `claude-kit:plan-gate`
  procedure (steps 1–6; step 7 is not shown). On `pass`, set the plan's Status
  to `approved`, commit the plan and its record, and continue. On `pass-with-decisions` or `fail`, the new stop
  rule fires.
- **New stop rule.** The plan gate in step 3 returns `pass-with-decisions` or
  `fail`. Write the handoff and report the record's decisions and Open items
  as questions. If the gate stopped at `P4-spec-gated` (no record), report
  the P4 reason and that the spec must pass `claude-kit:spec-gate`, and commit
  the plan only. `/ship` approves the spec, not decisions the plan adds later,
  so it stops instead of deciding.
- **Step 3, writing the plan.** When the spec leaves a choice open, prefer
  one the spec, its ADRs or the existing code already imply, so that a
  routine plan passes without stopping.
- **Stopping and resuming.** Before the stop rule fires, commit the plan
  and its record on the feature branch. The user then answers in the session.
  On approval of `pass-with-decisions`, add
  `- **Decisions approved:** <today>` to the record. On a `fail` or a change
  request, update the plan (or the spec, which is re-gated) and rerun the
  plan gate. Commit, and continue `/ship`. A rerun of `/ship` that resumes in
  the feature worktree does not rewrite the plan at step 3. It finds the
  existing plan by its spec, not by date: a plan under
  `docs/superpowers/plans/` on the feature branch whose `**Spec:**` line names
  this spec (the newest by file name if several match). Step 4 uses the same
  lookup. If that plan exists and `--verify-record` on it exits 0, step 3 is
  skipped. If `--verify-record` prints
  `decisions not approved`, it does not rerun the gate: it shows the record's
  Plan-introduced decisions and stops again. Rerunning `/ship` is never
  approval; only the user's answer is. Any other failure reason (`missing`,
  `not passed`, `stale`) runs the plan gate on the existing plan.
- **Step 4.** Before implementing, `spec-lint.py --verify-record <plan>`
  must exit 0. This catches a resumed `/ship` whose plan or spec changed after
  gating.
- **Step 7.** The PR body links the plan gate record next to the plan.

### `CLAUDE.md` and convention changes

- "Specs and plans": after writing or revising a plan, run
  `claude-kit:plan-gate` on it before offering an execution choice. A `pass`
  goes straight to the choice; `pass-with-decisions` needs the user's one-line
  OK first.
- New section `## Designing a spec`, containing the phrase "no approval pause
  between design sections": present the design once, in full, then write
  the spec. Do not stop for approval between design sections. Ask the user
  only the questions the design needs (decisions under "Verify key decisions
  with me"). The spec and plan gates review the documents. The user's sign-off
  is the gate verdict and its key decisions.
- `conventions/spec-driven-development.md`: a "Plan gate" section stating the
  plan shape, the three verdicts, and who signs off on what.

## Decisions

- **Separate follow-up spec, not an amendment to the spec gate.** The user
  chose it. The spec gate ships as written, and this spec extends its pieces.
- **Sign off only on plan-introduced decisions.** The user already approved
  the spec. A plan that adds no decisions has nothing new for the user to
  confirm. Asking anyway would bring back a read the user does not do.
- **One linter, chosen by folder** (approach 1) over a separate
  `plan-lint.py` (duplicated hash and record code) or a reviewer-only gate (no
  deterministic floor).
- **A plan can only pass on a gated spec (`P4`), and its record pins the
  spec hash.** Coverage is measured against the spec, so an unchecked or
  changed spec would make the coverage check meaningless.
- **Checked boxes don't affect the hash.** Execution ticks steps, and that
  must not invalidate the record mid-build.
- **Plan records in `gates/plans/`**, so plan and spec records cannot collide.
- **The plan gate never edits the spec.** Spec-level problems go to the user,
  as with the spec gate's decision findings.
- **Under `/ship`, plan-introduced decisions stop the run.** `/ship`'s
  approval covers the spec, not choices made after it.
- **The no-pause design rule ships with the plan gate on purpose.** Both
  remove a full read by the user, so they land together.
- **No per-section design approval during spec creation.** The user chose
  this. The gates replace the per-section read, and the user's role during
  creation is answering questions and giving instructions.

## Success criteria

1. **Plan linter tests pass.** `pytest tests/test_spec_lint.py` passes with,
   for each rule `P1`–`P9`, a plan fixture under a `plans/` folder that
   violates only that rule and asserts the exact rule ID, line number and exit
   code 1. A compliant plan (with a valid gated spec fixture) exits 0. The
   existing spec-rule tests still pass, showing spec files are not affected.
2. **Hash and record behaviour is tested.** Tests assert that changing a plan's
   Status line or ticking `- [ ]` → `- [x]` keeps `--hash` the same, and any
   other edit changes it. `--verify-record` on a plan returns `missing`,
   `not passed`, `decisions not approved`, `stale` (plan edited) and `stale`
   (spec edited) with exit 1, and exits 0 for a valid `pass` record and for an
   approved `pass-with-decisions` record.
3. **`/ship` wiring is tested.** `tests/test_ship_command.py` asserts that
   step 3 runs `claude-kit:plan-gate`, step 4 runs `--verify-record` on the
   plan, the Stop rules include the plan gate, and step 7 mentions the plan
   gate record.
4. **The skill is wired.** `tests/test_plan_gate_skill.py` asserts `plugin/skills/plan-gate/SKILL.md`
   has `name: plan-gate` frontmatter and references `rubric.md` and
   `spec-lint.py`, and that `rubric.md` defines `[blocking]` and `[minor]`
   headings and a `## Plan-introduced decisions` section.
5. **Docs and manifest are updated.** `tests/test_plan_gate_skill.py` also
   asserts that `conventions/spec-driven-development.md` has a `## Plan gate`
   section, that the ADR 0016 file exists and has a row in
   `knowledge/decisions/README.md`, and that `plugin/.claude-plugin/plugin.json`
   has version `0.7.0` and a description containing "spec and plan gates".
   **Rules are in `CLAUDE.md`.** A `tests/test_docs.py` check asserts the
   workspace `CLAUDE.md` mentions `claude-kit:plan-gate` under "Specs and
   plans" and has a `## Designing a spec` section containing "no approval pause between
   design sections".
6. **Back-test.** Run `spec-lint.py` on each of the five existing plans in
   `docs/superpowers/plans/` and report the output in the PR. `P4` is expected
   to fail for the four older plans (their specs have no gate records) and
   pass for `docs/superpowers/plans/2026-09-30-spec-gate.md`; every other
   violation is classified as a real gap or a false alarm. Any rule with a
   false alarm is loosened, with a test added, before merge.
7. **Reviewer eval: catches seeded defects.** `tests/fixtures/plan-gate/`
   holds six plans, each for a small hypothetical kit feature that does not
   exist in the repo (as the spec-gate fixtures do), with exactly one seeded
   defect, plus the spec each plan implements:
   1. a spec success criterion no task covers
   2. a task that needs a fact the plan never gives
   3. a task that uses a file created by a later task
   4. a false code claim (a named function that does not exist)
   5. scope creep (a task the spec does not ask for)
   6. an architecture choice the spec does not settle (must appear under
      Plan-introduced decisions, not as a finding)

   Plus one clean control plan with its spec. The `README.md` names each
   defect and the manual steps. Run one reviewer pass on each of the seven,
   twice, using the same method as `tests/fixtures/spec-gate/README.md`:
   reviewers run in a detached checkout of the branch without
   `tests/fixtures/plan-gate/`, on copies with neutral, shuffled names, so they
   cannot read the defect list. When copying, each plan's `**Spec:**` line is
   rewritten to its spec copy's neutral name. Defect 6 is a hit only if it is
   listed under Plan-introduced decisions and not as a `[blocking]` finding.
   Pass when
   the seeded defect is reported (as `blocking` for 1–5, as a decision for 6)
   in at least 5 of the 6 on both runs, and the control gets at most 1
   `blocking` finding per run. The table of hits is reported in the PR.
8. **End-to-end check.** After implementation, in the feature worktree,
   follow the worktree's `plugin/skills/plan-gate/SKILL.md` with the
   worktree's `spec-lint.py` on the plan written for this spec. (The `/ship`
   building this spec is the pre-change one, and the slash command is not
   loaded until merge.) Each reviewer gets the absolute path of the worktree's
   `rubric.md`, and as the repository a detached worktree at the commit that
   added the plan. Plan edits from the fix rounds are committed as plan
   revisions; they do not re-run implementation. If the verdict is
   `pass-with-decisions`, stop and ask the user as the new stop rule describes,
   then add and commit the `Decisions approved` line. Report the verdict and
   round count in the PR and commit the record. Before the PR is merged,
   `spec-lint.py --verify-record` on that plan prints `ok:` and exits 0.
9. **The suite and lint pass.** `pytest` and
   `ruff check plugin tests; ruff format --check plugin tests` pass, locally
   and in CI.
