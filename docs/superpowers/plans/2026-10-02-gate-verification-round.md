# Gates Converge Implementation Plan

- **Status:** approved
- **Date:** 2026-10-02

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the spec gate and plan gate converge: the spec rubric limits
`blocking` to six classes and adds a `[plan]` severity whose questions go to
the plan; both gates end with up to 2 verification rounds that check only the
last fixes; `/ship` step 3 and the plan gate carry the Plan questions forward.

**Architecture:** All changes are Markdown instructions read by the model
(skills, rubrics, a command) plus structure tests that pin their key phrases.
A new shared `plugin/skills/spec-gate/verify.md` is the verification
rubric for both gates. No Python script changes. Docs: the spec-driven
convention, ADR 0020, plugin 0.12.0.

**Tech Stack:** Markdown skill files, Python 3.11+ pytest structure tests,
ruff.

**Spec:** `docs/superpowers/specs/2026-10-02-gate-verification-round-design.md`

## Context for a cold start

- Work in the worktree `C:\Users\alymo\Desktop\Github\.worktrees\gate-verification-round`
  on branch `feat/gate-verification-round`, cut from `origin/main` at
  `597663d`. The spec and its gate record are committed on this branch. Run
  every command from the worktree root.
- Setup once per machine: `pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`.
- Full checks: `python -m pytest -q`, `ruff check plugin tests`,
  `ruff format --check plugin tests`. Baseline on this branch: all green.
- The plugin is loaded into Claude Code through a junction
  `~/.claude/skills/claude-kit` → the **main checkout's** `plugin/` folder
  (ADR 0005). So invoking `claude-kit:spec-gate` during this work runs main's
  old files, not this worktree's. Tasks 6 and 7 therefore name worktree paths
  explicitly and never invoke the installed skill.
- Why this work exists (from the spec's Purpose): fresh reviewers each
  sample a different subset of an unbounded set of "how" questions, fixes add
  surface, and round 3's fixes were never re-reviewed, so the gate failed
  with nothing for the user to decide.
- Decisions already made by the user (do not relitigate): spec gate gets both
  the classes/`[plan]` change and verification rounds; plan gate gets
  verification rounds and a Plan-questions check only; Plan questions live in
  the spec's gate record, not in the spec; at most 2 verification rounds, 5
  rounds in total; one shared `verify.md`; step numbers 1–7 stay the same in
  both gates so `/ship` and `/ship-many` references do not change.
- The version test in `tests/test_plugin_manifest.py`
  (`test_description_mentions_grill`) pins `"0.11.0"`; the bump to 0.12.0
  requires loosening that pin to `>=` (Task 5).

## Global Constraints

- Step numbering in both `SKILL.md` files stays 1–7 with the names Lint,
  Review round, Fix, Repeat (then verify), Verdict, Record, Report.
- The trailer sentences stay: spec gate "When `/ship` runs this skill, it
  skips step 7's question: invoking `/ship` is the approval."; plan gate
  "When `/ship` runs this skill, it runs steps 1–6 only; `/ship` decides what
  happens after the verdict."
- Six blocking classes, exact names: `wrong-build`, `contradiction`,
  `false-claim`, `uncheckable`, `open-what`, `too-large`.
- Record `Rounds` line format: `- **Rounds:** <D> discovery + <V> verification`.
- Scratchpad file names: `<name>.before-round-<N>.md`,
  `<name>.before-verify-<N>.md`, `<name>.fixes-<R>.md`, `<name>.diff-<R>.txt`
  where `<R>` is `round-<N>` or `verify-<N>`.
- `plugin/scripts/spec-lint.py` is not changed. Existing gate records are not
  rewritten. ADRs 0015 and 0016 are not edited.
- Plugin version 0.12.0.

## Review Focus

- A spec gate run where discovery round 1 or 2 returns no blocking findings:
  no verification round runs, and the record says `<N> discovery + 0
  verification` (Task 2 text, step 4).
- A run with decision findings after discovery: verification is skipped and
  the verdict is `fail` (Task 2 and Task 3 text, step 4; pinned by tests on
  "skip verification").
- A plan gate run where verification runs: plan-introduced decisions still
  come from the last discovery round plus `## Decisions changed`, so
  `pass-with-decisions` still fires (Task 3; pinned by a test on
  `## Decisions changed`).
- A spec gate record with no plan questions: `## Plan questions` holds
  `- none`, and plan-gate check 7 treats a missing section or `- none` as
  nothing to check (Tasks 2 and 3).
- `git diff --no-index` exits 1 when files differ; the instructions say this
  is expected (Task 2; pinned by a test on "exit status 1").

---

### Task 1: Spec rubric classes and the shared verify rubric

**Files:**
- Modify: `plugin/skills/spec-gate/rubric.md`
- Create: `plugin/skills/spec-gate/verify.md`
- Test: `tests/test_spec_gate_skill.py`

**Depends on:** none

- [ ] **Step 1: Write the failing tests.** In `tests/test_spec_gate_skill.py`,
  add after `test_rubric_defines_finding_format_and_probes`:

```python
CLASSES = (
    "wrong-build",
    "contradiction",
    "false-claim",
    "uncheckable",
    "open-what",
    "too-large",
)


def test_rubric_limits_blocking_to_classes_and_adds_plan_severity():
    rubric = read("rubric.md")
    for text in ("### [plan]", "**Class:**", "**Question:**", "six classes"):
        assert text in rubric
    for name in CLASSES:
        assert f"`{name}`" in rubric


def test_verify_rubric_is_scoped_to_the_diff():
    verify = read("verify.md")
    for text in (
        "## Fixes",
        "## Findings",
        "### [blocking]",
        "## Decisions changed",
        "outside the diff",
        "not resolved",
    ):
        assert text in verify
```

- [ ] **Step 2: Run the tests to see them fail.**
  Run: `python -m pytest -q tests/test_spec_gate_skill.py`
  Expected: 2 failed (`FileNotFoundError` for `verify.md`, and the
  `### [plan]` assertion), the rest pass.

- [ ] **Step 3: Replace `plugin/skills/spec-gate/rubric.md`** with exactly:

````markdown
# Spec gate rubric

You are reviewing a design spec cold. You have the spec, the repository, and
this file, and nothing else: no conversation, no plan. That is deliberate. A
later session will build from this spec with exactly that context, and every
question you cannot answer from it is a question that session would have to
guess at.

Read the whole spec, then read the code it talks about. Flag problems only;
never edit the spec.

## What to check

1. **Dry-run plan.** Write the ordered list of implementation tasks you would
   plan from this spec. Under each, list every question you would have to ask
   before building it. Each question the spec does not answer is a finding:
   `blocking` (class `open-what`) when it is about *what* to build, `plan`
   when it is about *how* (see Severity).
2. **Ambiguity.** Find requirements with two reasonable readings that lead to
   different code or behaviour. Quote the requirement and state both readings.
   It is `blocking` (class `open-what`) when the readings build different
   things, and `plan` when both readings meet the spec.
3. **Contradictions** between sections, including Design versus Decisions
   versus Success criteria versus Scope (class `contradiction`).
4. **Code claims.** Check every statement about existing code, files,
   functions, commands or behaviour against the repository (open the files,
   search for the names). A false claim is `blocking` (class `false-claim`).
5. **Checkability.** For each success criterion, say how it would be checked.
   A criterion with no objective check is `blocking` (class `uncheckable`).
6. **Scope size.** If the dry-run plan has more than 15 tasks, or covers two
   or more independent subsystems that could ship separately, raise a
   `blocking` finding (class `too-large`) proposing the split.
7. **Key decisions.** List the decisions the spec makes about scope,
   architecture, product boundary, data or irreversible actions, or the
   interpretation of the request. These are not findings; the user confirms
   them.

## Severity

- `blocking`: only when the finding fits one of these six classes, named in
  its `**Class:**` field:
  1. `wrong-build`: as written, the spec leads to the wrong behaviour or to
     harm (data loss, an unsafe rerun, a change to something that must not
     change).
  2. `contradiction`: two parts of the spec disagree.
  3. `false-claim`: a statement about existing code, files, commands or
     behaviour is untrue.
  4. `uncheckable`: a success criterion has no objective check.
  5. `open-what`: a question about *what* to build (behaviour, scope,
     interface, data) that the spec does not answer.
  6. `too-large`: check 6 (scope size) fires; the finding proposes the split.
- `plan`: a *how* question the plan can settle without changing what gets
  built. Test: if two implementers answered it differently, would both still
  meet the spec? Yes means `plan`. Examples: test file placement, helper
  structure, exact constants the spec does not constrain, step order inside
  one task. The gate does not fix these in the spec; it hands the question
  to the plan.
- `minor`: wording or clarity that does not change what gets built.

A problem that fits none of the six classes is `plan` or `minor`, never
`blocking`. Do not pad. A spec with no blocking problems gets no blocking
findings.

## Output format

Return exactly this, and nothing before or after it:

```
## Dry-run plan
1. <task> — questions: <q1>; <q2> | none

## Findings
### [blocking] <title>
- **Class:** wrong-build | contradiction | false-claim | uncheckable | open-what | too-large
- **Line:** <spec line number or section>
- **Problem:** <what is wrong, quoting the spec>
- **Fix:** <a concrete change to the spec>

### [plan] <title>
- **Line:** <spec line number or section>
- **Problem:** <what the spec leaves open>
- **Question:** <the question the plan must answer>

### [minor] <title>
- **Line:** ...
- **Problem:** ...
- **Fix:** ...

## Key decisions
- <decision> (<section>)
```

Write `none` under Findings when there are no findings.
````

- [ ] **Step 4: Create `plugin/skills/spec-gate/verify.md`** with exactly:

````markdown
# Gate verification rubric

You are verifying fixes to a document: a design spec or an implementation
plan (the prompt says which, and for a plan names its spec). You have the
document, the repository, a list of the findings that were just fixed, and a
unified diff of the document from before those fixes to now. Nothing else.
Flag problems only; never edit the document.

## What to check

1. **Each fix.** Does the changed text resolve the finding it names?
2. **The diff.** Do the changed or added lines contradict another part of the
   document, make a false claim about the code (check the repository), or
   lead to the wrong behaviour?

Do not search for problems outside the diff, and do not raise problems that
the changed lines did not introduce, and do not re-raise problems an earlier
round did not raise. Earlier review rounds covered the rest.

## Decisions

List under `## Decisions changed` every decision the diff adds or changes.
For a spec, a decision is a choice about scope, architecture, product
boundary, data or irreversible actions, or the interpretation of the request.
For a plan, it is a choice the plan makes that its spec does not settle,
about the same subjects; file names, helper structure and test layout are
not decisions.

## Output format

Return exactly this, and nothing before or after it:

```
## Fixes
- <finding title> — resolved | not resolved: <why>

## Findings
### [blocking] <title>
- **Line:** <line or section>
- **Problem:** <what is wrong, quoting the changed text>
- **Fix:** <a concrete change>

## Decisions changed
- <decision added or changed by the diff> (<section>)
```

Write `none` under Findings and under Decisions changed when there are none.
List each `not resolved` fix also as a `[blocking]` finding.
````

- [ ] **Step 5: Run the tests.**
  Run: `python -m pytest -q tests/test_spec_gate_skill.py`
  Expected: all passed.

- [ ] **Step 6: Lint and commit.**
  Run: `ruff check plugin tests && ruff format --check plugin tests`
  Expected: `All checks passed!` and no files would be reformatted (run
  `ruff format plugin tests` first if it reports a file). Then commit:

```bash
git add plugin/skills/spec-gate/rubric.md plugin/skills/spec-gate/verify.md tests/test_spec_gate_skill.py
git commit -m "spec-gate: six blocking classes, [plan] severity, shared verify rubric

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: Spec gate verification rounds and Plan questions

**Files:**
- Modify: `plugin/skills/spec-gate/SKILL.md`
- Test: `tests/test_spec_gate_skill.py`

**Depends on:** Task 1

- [ ] **Step 1: Write the failing test.** In `tests/test_spec_gate_skill.py`,
  in `test_skill_uses_linter_rubric_and_records`, replace the line
  `assert "3 rounds" in body` with:

```python
    assert "3 discovery rounds" in body
    for text in (
        "verify.md",
        "verification round",
        "## Plan questions",
        "3 discovery + 2 verification",
        "--no-index",
        "exit status 1",
        "skip verification",
        "<D> discovery + <V> verification",
        "skips step 7's question",
    ):
        assert text in body
    assert "3 discovery rounds" in frontmatter(body)["description"]
```

- [ ] **Step 2: Run it to see it fail.**
  Run: `python -m pytest -q tests/test_spec_gate_skill.py::test_skill_uses_linter_rubric_and_records`
  Expected: 1 failed (`assert "3 discovery rounds" in body`).

- [ ] **Step 3: Replace `plugin/skills/spec-gate/SKILL.md`** with exactly:

````markdown
---
name: spec-gate
description: Use when a design spec has just been written or revised, before asking the user to review it, or when /ship finds no valid gate record. Lints the spec, runs up to 3 discovery rounds of a fresh-context reviewer subagent, then up to 2 verification rounds of its fixes, fixes what it finds, and writes a gate record under docs/superpowers/gates/. The user then confirms a short verdict instead of reading the spec.
argument-hint: [path-to-spec.md]
---

# Spec gate

A spec is the contract `/ship` builds against without check-ins, and the user
does not read specs in full. This gate does that reading. It passes only when
the linter is clean, a reviewer that never saw the conversation finds nothing
blocking, and the last fixes have been verified. "How" questions that the plan
can settle do not block: they are handed to the plan.

## Setup

- **Spec:** `$ARGUMENTS` if given, else the `*.md` under `docs/superpowers/specs/`
  whose file name sorts last (the newest date prefix). Name it in one line.
- **Linter:** `python <this skill's directory>/../../scripts/spec-lint.py`
  (fallback: `~/.claude/skills/claude-kit/scripts/spec-lint.py`).
- **Rubric:** `rubric.md` in this skill's directory (discovery rounds).
- **Verify rubric:** `verify.md` in this skill's directory (verification
  rounds).
- **Scratchpad:** the session's scratchpad directory, or a temporary
  directory outside the repository. Snapshots, fixes files and diff files go
  there; `<name>` below is the spec's file name.

## Steps

1. **Lint.** Run the linter on the spec. Fix every violation in the spec and
   re-run until it exits 0. A violation the spec cannot fix without a product
   choice is a decision finding (step 3).
2. **Review round.** This is a **discovery round**. Dispatch a **new**
   general-purpose subagent every round (never reuse one; a reviewer anchors
   on its own earlier findings). Give it only this prompt, with absolute
   paths:

   > Review the design spec at `<spec>` in the repository at `<repo root>`.
   > Read `<rubric.md>` first and follow it exactly. Return only the output
   > format it defines.

   Do not pass it any conversation, summary or plan.
3. **Fix.** Before applying this round's fixes, copy the spec to the
   scratchpad as `<name>.before-round-<N>.md`. For each `[blocking]` finding:
   - If fixing it needs a scope, product or behaviour choice that the spec
     and the conversation do not settle, it is a **decision finding**. Do not
     guess. Collect it for the user.
   - Otherwise, edit the spec to fix it. Fix `[minor]` findings too when the
     fix is clear.

   Do **not** fix `[plan]` findings in the spec. Collect each one's question
   and spec section for the record, dropping duplicates by question. Re-run
   the linter after editing.
4. **Repeat, then verify.** Repeat steps 2 and 3 until a discovery round
   returns no `[blocking]` findings, for at most 3 discovery rounds.

   If there are decision findings, skip verification: the verdict is `fail`,
   and the rerun after the user answers starts from step 1.

   Otherwise, if the last discovery round had `[blocking]` findings (all now
   fixed), run up to 2 **verification rounds**. For each:

   1. Write the fixes file `<name>.fixes-<R>.md` to the scratchpad: each
      fixed `[blocking]` finding's title and what changed. `<R>` names the
      round whose fixes are verified: `round-<N>` for the last discovery
      round, `verify-<N>` for a verification round.
   2. Write the diff file: `git diff --no-index <snapshot> <spec>` into
      `<name>.diff-<R>.txt` in the scratchpad, where the snapshot is the copy
      taken before those fixes (exit status 1 means the files differ and is
      expected).
   3. Dispatch a **new** general-purpose subagent with only this prompt,
      with absolute paths:

      > Verify fixes to the design spec at `<spec>` in the repository at
      > `<repo root>`. Read `<verify.md>` first and follow it exactly. The
      > document is a spec. The fixed findings are listed in `<fixes file>`;
      > the diff of the fixes is in `<diff file>`. Return only the output
      > format it defines.

   4. No `[blocking]` findings: stop verifying. A finding that needs a choice
      the spec and conversation do not settle is a decision finding: stop
      verifying; the verdict is `fail`. Otherwise copy the spec to
      `<name>.before-verify-<N>.md`, fix the findings, re-run the linter, and
      run the next verification round on those fixes only.

   At most 5 review rounds in total (3 discovery + 2 verification).
5. **Verdict.** `pass` when the linter is clean, the last round (discovery or
   verification) returned no `[blocking]` findings, and there are no decision
   findings. Otherwise `fail`. `[plan]` findings never affect the verdict.
6. **Record.** Run the linter with `--hash` on the spec after its last edit.
   Write `docs/superpowers/gates/<spec file name>` (create the folder if
   needed; overwrite an older record):

   ```
   # Gate: <spec title>

   - **Spec:** docs/superpowers/specs/<spec file name>
   - **Spec SHA-256:** <the --hash output>
   - **Verdict:** pass | fail
   - **Date:** YYYY-MM-DD
   - **Rounds:** <D> discovery + <V> verification

   ## Key decisions

   - <the discovery rounds' Key decisions merged, plus each verification
     round's Decisions changed (a changed decision replaces the old wording)>

   ## Findings fixed

   - <round N | verify N> [blocking|minor] <title>: <what changed in the spec>

   ## Plan questions

   - <question> (<spec section>), or "none"

   ## Open

   - <each decision finding and each unresolved blocking finding, or "none">
   ```

   Then run the linter with `--verify-record` on the spec. On a pass verdict
   it must print `ok:`.
7. **Report to the user.** One short message. Name the spec by path only;
   never open or render it.
   - **pass:** "Gate passed in D discovery + V verification rounds; M
     findings fixed.", plus "K plan questions handed to the plan." when K is
     more than 0. Then the key decisions as a list, then "OK to mark it
     approved?". On yes, set the spec's Status bullet to `approved` (the hash
     ignores that line, so the record stays valid).
   - **fail:** "Gate failed." Then each Open item as a direct question with
     the options and your recommendation. After the user answers, update the
     spec and run the gate again from step 1.

When `/ship` runs this skill, it skips step 7's question: invoking `/ship` is
the approval.
````

- [ ] **Step 4: Run the tests.**
  Run: `python -m pytest -q tests/test_spec_gate_skill.py`
  Expected: all passed.

- [ ] **Step 5: Commit.**
  Run: `ruff check plugin tests && ruff format --check plugin tests`
  Expected: `All checks passed!`, nothing to reformat. Then:

```bash
git add plugin/skills/spec-gate/SKILL.md tests/test_spec_gate_skill.py
git commit -m "spec-gate: verification rounds after discovery; Plan questions in the record

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: Plan gate verification rounds and Plan-questions check

**Files:**
- Modify: `plugin/skills/plan-gate/SKILL.md`
- Modify: `plugin/skills/plan-gate/rubric.md`
- Test: `tests/test_plan_gate_skill.py`

**Depends on:** Task 1

- [ ] **Step 1: Write the failing tests.** In `tests/test_plan_gate_skill.py`,
  in `test_skill_uses_linter_rubric_and_records`, replace the line
  `assert "3 rounds" in body` with:

```python
    assert "3 discovery rounds" in body
    assert "../spec-gate/verify.md" in body
    assert (GATE / "../spec-gate/verify.md").resolve().is_file()
    for text in (
        "verification round",
        "Plan questions",
        "## Decisions changed",
        "3 discovery + 2 verification",
        "skip verification",
        "runs steps 1–6 only",
    ):
        assert text in body
    assert "3 discovery rounds" in frontmatter(body)["description"]
```

  and in `test_rubric_defines_finding_format_and_probes`, add to the end:

```python
    assert "Plan questions" in rubric
```

- [ ] **Step 2: Run them to see them fail.**
  Run: `python -m pytest -q tests/test_plan_gate_skill.py`
  Expected: 2 failed (`"3 discovery rounds"` and `"Plan questions"`).

- [ ] **Step 3: Edit `plugin/skills/plan-gate/rubric.md`.** After check 6
  (the paragraph ending "unless it contradicts something the spec does
  settle.") and before `## Severity`, insert:

```markdown
7. **Plan questions.** Read the spec's gate record (the prompt names it). For
   each question under its `## Plan questions` section, name the task that
   answers it. A question no task answers is `blocking`. A missing section
   or `- none` means there is nothing to check.
```

- [ ] **Step 4: Replace `plugin/skills/plan-gate/SKILL.md`** with exactly:

````markdown
---
name: plan-gate
description: Use when an implementation plan has just been written or revised, before offering an execution choice, or when /ship has written a plan. Lints the plan, runs up to 3 discovery rounds of a fresh-context reviewer subagent that checks it against its spec, then up to 2 verification rounds of its fixes, fixes what it finds, and writes a gate record under docs/superpowers/gates/plans/. The user signs off only on decisions the plan adds that the spec did not settle.
argument-hint: [path-to-plan.md]
---

# Plan gate

A plan is the only context its executor gets, and the user does not read
plans. This gate does that reading. It passes only when the linter is clean,
a reviewer that never saw the conversation finds every spec item covered and
every task executable from the plan alone, and the last fixes have been
verified. The user signs off only on decisions the plan makes that its spec
did not settle.

## Setup

- **Plan:** `$ARGUMENTS` if given, else the `*.md` under
  `docs/superpowers/plans/` whose file name sorts last. Name it in one line.
- **Spec:** the path on the plan's `**Spec:**` line.
- **Spec gate record:** `docs/superpowers/gates/<spec file name>`.
- **Linter:** `python <this skill's directory>/../../scripts/spec-lint.py`
  (fallback: `~/.claude/skills/claude-kit/scripts/spec-lint.py`).
- **Rubric:** `rubric.md` in this skill's directory (discovery rounds).
- **Verify rubric:** `../spec-gate/verify.md` from this skill's directory
  (verification rounds).
- **Scratchpad:** the session's scratchpad directory, or a temporary
  directory outside the repository. Snapshots, fixes files and diff files go
  there; `<name>` below is the plan's file name.

## Steps

1. **Lint.** If the plan has no `- **Status:**` bullet, add
   `- **Status:** draft`. Run the linter on the plan and fix every other
   violation in the plan, re-running until it exits 0. If `P4-spec-gated` is
   then the only violation left, stop with verdict `fail`: write no record,
   and report that the spec must pass `claude-kit:spec-gate` first. Never
   edit the spec from this gate.
2. **Review round.** This is a **discovery round**. Dispatch a **new**
   general-purpose subagent every round (never reuse one; a reviewer anchors
   on its own earlier findings). Give it only this prompt, with absolute
   paths:

   > Review the implementation plan at `<plan>` against its spec at `<spec>`
   > in the repository at `<repo root>`. The spec's gate record is at
   > `<spec gate record>`; its `## Plan questions` section lists questions
   > the plan must answer. Read `<rubric.md>` first and follow it exactly.
   > Return only the output format it defines.

   Do not pass it any conversation or summary.
3. **Fix.** Before applying this round's fixes, copy the plan to the
   scratchpad as `<name>.before-round-<N>.md`. For each `[blocking]` finding,
   edit the plan to fix it, unless the fix would change what the spec asks
   for: that is a **spec finding**. Do not fix it in the plan; collect it for
   the Open list. Fix `[minor]` findings too when the fix is clear. Re-run
   the linter after editing.
4. **Repeat, then verify.** Repeat steps 2 and 3 until a discovery round
   returns no `[blocking]` findings, for at most 3 discovery rounds.

   If there are spec findings, skip verification: the verdict is `fail`.

   Otherwise, if the last discovery round had `[blocking]` findings (all now
   fixed), run up to 2 **verification rounds**. For each:

   1. Write the fixes file `<name>.fixes-<R>.md` to the scratchpad: each
      fixed `[blocking]` finding's title and what changed. `<R>` names the
      round whose fixes are verified: `round-<N>` for the last discovery
      round, `verify-<N>` for a verification round.
   2. Write the diff file: `git diff --no-index <snapshot> <plan>` into
      `<name>.diff-<R>.txt` in the scratchpad, where the snapshot is the copy
      taken before those fixes (exit status 1 means the files differ and is
      expected).
   3. Dispatch a **new** general-purpose subagent with only this prompt,
      with absolute paths:

      > Verify fixes to the implementation plan at `<plan>` in the repository
      > at `<repo root>`. Read `<verify.md>` first and follow it exactly. The
      > document is a plan; its spec is at `<spec>`. The fixed findings are
      > listed in `<fixes file>`; the diff of the fixes is in `<diff file>`.
      > Return only the output format it defines.

   4. No `[blocking]` findings: stop verifying. A finding whose fix would
      change what the spec asks for is a spec finding: stop verifying; the
      verdict is `fail`. Otherwise copy the plan to
      `<name>.before-verify-<N>.md`, fix the findings, re-run the linter, and
      run the next verification round on those fixes only.

   At most 5 review rounds in total (3 discovery + 2 verification).

   The **plan-introduced decisions** are the last discovery round's list plus
   every verification round's `## Decisions changed` entries (a changed
   decision replaces the old wording).
5. **Verdict.**
   - `pass`: the linter is clean, the last round (discovery or verification)
     returned no `[blocking]` findings, there are no spec findings, and the
     plan-introduced decisions are empty.
   - `pass-with-decisions`: the same, but the plan-introduced decisions are
     not empty.
   - `fail`: anything else.
6. **Record.** Run the linter with `--hash` on the plan and on the spec after
   the last plan edit. Write `docs/superpowers/gates/plans/<plan file name>`
   (create the folder if needed; overwrite an older record):

   ```
   # Plan gate: <plan title>

   - **Plan:** docs/superpowers/plans/<plan file name>
   - **Plan SHA-256:** <--hash of the plan>
   - **Spec:** <spec path from the plan>
   - **Spec SHA-256:** <--hash of the spec>
   - **Verdict:** pass | pass-with-decisions | fail
   - **Date:** YYYY-MM-DD
   - **Rounds:** <D> discovery + <V> verification

   ## Plan-introduced decisions

   - <the plan-introduced decisions, or "none">

   ## Findings fixed

   - <round N | verify N> [blocking|minor] <title>: <what changed in the plan>

   ## Open

   - <each spec finding and each unresolved blocking finding, or "none">
   ```

   The decisions section holds the plan-introduced decisions as defined in
   step 4; that exact list is what the user approves. Then run the linter
   with `--verify-record` on the plan: on `pass` it must print `ok:`; on
   `pass-with-decisions` it prints `decisions not approved` until the user
   approves.
7. **Report to the user.** One short message. Name the plan by path only;
   never open or render it.
   - **pass:** "Plan gate passed in D discovery + V verification rounds; no
     new decisions." Set the plan's Status to `approved` (the hash ignores
     it) and continue straight to the execution choice, with no further
     sign-off.
   - **pass-with-decisions:** "Plan gate passed in D discovery + V
     verification rounds. The plan makes these decisions the spec doesn't:",
     then the list, then "OK?". On yes, add
     `- **Decisions approved:** <today>` to the record and set the plan's
     Status to `approved` (neither changes a hash). On a change request, edit
     the plan and run the gate again from step 1.
   - **fail:** "Plan gate failed." Then each Open item as a direct question
     with the options and your recommendation; a spec finding names the spec
     section to change. After the user answers, update the plan (or the spec,
     which is then gated again with `claude-kit:spec-gate`) and run this gate
     again from step 1.

When `/ship` runs this skill, it runs steps 1–6 only; `/ship` decides what
happens after the verdict.
````

- [ ] **Step 5: Run the tests.**
  Run: `python -m pytest -q tests/test_plan_gate_skill.py`
  Expected: all passed.

- [ ] **Step 6: Commit.**
  Run: `ruff check plugin tests && ruff format --check plugin tests`
  Expected: `All checks passed!`, nothing to reformat. Then:

```bash
git add plugin/skills/plan-gate/SKILL.md plugin/skills/plan-gate/rubric.md tests/test_plan_gate_skill.py
git commit -m "plan-gate: verification rounds; check the spec record's Plan questions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: `/ship` step 3 answers the Plan questions

**Files:**
- Modify: `plugin/commands/ship.md`
- Test: `tests/test_ship_command.py`

**Depends on:** none

- [ ] **Step 1: Write the failing test.** Append to `tests/test_ship_command.py`:

```python
def test_plan_writer_answers_the_spec_records_plan_questions():
    step = _step(3)
    assert "## Plan questions" in step
    assert "docs/superpowers/gates/<spec file name>" in step
```

- [ ] **Step 2: Run it to see it fail.**
  Run: `python -m pytest -q tests/test_ship_command.py`
  Expected: 1 failed (`assert "## Plan questions" in step`).

- [ ] **Step 3: Edit `plugin/commands/ship.md` step 3.** Replace the substring
  (line 91 continues with " Then add a `**Depends on:**` line ...", which
  stays unchanged after the inserted text)

```
   existing code already imply, so a routine plan passes without stopping. Do
   not offer an execution choice.
```

  with

```
   existing code already imply, so a routine plan passes without stopping.
   Answer every question under the `## Plan questions` section of the spec's
   gate record (`docs/superpowers/gates/<spec file name>`) in the task it
   affects. Do not offer an execution choice.
```

- [ ] **Step 4: Run the tests.**
  Run: `python -m pytest -q tests/test_ship_command.py tests/test_ship_many_command.py`
  Expected: all passed.

- [ ] **Step 5: Commit.**
  Run: `ruff check plugin tests && ruff format --check plugin tests`
  Expected: `All checks passed!`, nothing to reformat. Then:

```bash
git add plugin/commands/ship.md tests/test_ship_command.py
git commit -m "/ship: the plan answers the spec record's Plan questions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: Convention, ADR 0020 and version 0.12.0

**Files:**
- Modify: `conventions/spec-driven-development.md`
- Create: `knowledge/decisions/0020-gates-end-with-verification.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `tests/test_plugin_manifest.py`
- Test: `tests/test_spec_gate_skill.py`

**Depends on:** none

- [ ] **Step 1: Write the failing test.** Append to
  `tests/test_spec_gate_skill.py` (it already imports `REPO`; add
  `import json` after `from __future__ import annotations`, separated by a
  blank line, as in `tests/test_plan_gate_skill.py`):

```python
def test_adr_0020_and_convention_wire_the_new_rounds():
    def text(rel):
        return (REPO / rel).read_text(encoding="utf-8")

    adr = "0020-gates-end-with-verification.md"
    assert (REPO / "knowledge" / "decisions" / adr).is_file()
    assert f"]({adr})" in text("knowledge/decisions/README.md")
    conv = text("conventions/spec-driven-development.md")
    spec_gate = conv.split("## Spec gate", 1)[1].split("\n## ", 1)[0]
    plan_gate = conv.split("## Plan gate", 1)[1].split("\n## ", 1)[0]
    for section in (spec_gate, plan_gate):
        assert adr in section and "verification round" in section
    assert "[plan]" in spec_gate
    manifest = json.loads(text("plugin/.claude-plugin/plugin.json"))
    assert manifest["version"] == "0.12.0"
```

  In `tests/test_plugin_manifest.py`, `test_description_mentions_grill`,
  replace `assert data["version"] == "0.11.0"` with:

```python
    version = tuple(int(part) for part in data["version"].split("."))
    assert version >= (0, 11, 0)
```

- [ ] **Step 2: Run it to see it fail.**
  Run: `python -m pytest -q tests/test_spec_gate_skill.py::test_adr_0020_and_convention_wire_the_new_rounds`
  Expected: 1 failed (the ADR file does not exist).

- [ ] **Step 3: Edit `conventions/spec-driven-development.md`.** In
  `## Spec gate`, replace the first paragraph (from "Every spec passes the
  kit's spec gate" to "...0015-spec-gate-replaces-full-read.md))." ) with:

```markdown
Every spec passes the kit's spec gate (`claude-kit:spec-gate`) before review.
The gate lints the spec with `plugin/scripts/spec-lint.py`, then runs up to
three discovery rounds of a fresh-context reviewer that tries to plan the
work from the spec alone. A finding is `[blocking]` only in one of six
classes (wrong-build, contradiction, false-claim, uncheckable, open-what,
too-large); a "how" question the plan can settle is a `[plan]` finding, which
is not fixed in the spec but listed under `## Plan questions` in the gate
record for the plan to answer. When the last discovery round's blocking
findings were fixed, up to two verification rounds check only those fixes
and the diff they made. The user then confirms a short verdict and the key
decisions rather than reading the whole spec
([ADR 0015](../knowledge/decisions/0015-spec-gate-replaces-full-read.md),
[ADR 0020](../knowledge/decisions/0020-gates-end-with-verification.md)).
```

  In `## Plan gate`, replace the first paragraph (from "Every plan passes
  the kit's plan gate" to "...0016-plan-gate-signs-off-on-new-decisions-only.md))." ) with:

```markdown
Every plan passes the kit's plan gate (`claude-kit:plan-gate`) before it is
executed. The gate lints the plan with `plugin/scripts/spec-lint.py` (plan
rules apply to files in a `plans` folder), then runs up to three discovery
rounds of a fresh-context reviewer that maps every spec item to a task, tries
to execute each task cold, checks task order and code claims, and checks
that the plan answers the spec gate record's Plan questions
([ADR 0016](../knowledge/decisions/0016-plan-gate-signs-off-on-new-decisions-only.md)).
When the last discovery round's blocking findings were fixed, up to two
verification rounds check only those fixes
([ADR 0020](../knowledge/decisions/0020-gates-end-with-verification.md)).
```

- [ ] **Step 4: Create `knowledge/decisions/0020-gates-end-with-verification.md`** with exactly:

```markdown
# ADR 0020: Gates end with a verification round; blocking is a fixed set of classes

- **Status:** accepted
- **Date:** 2026-10-02

## Context
The spec gate escalated to the user most of the time. Of the five spec gate
records in the kit, three needed more than 3 rounds (blocking findings per
round: 3-2-1-1, 4-3-2 then a rerun, 2-4-4-2-1-1), and real projects showed
the same pattern: counts fall but rarely reach zero, and the gate fails with
nothing for the user to decide. Two causes: every unanswered implementation
question was `blocking`, so each fresh reviewer sampled a different subset of
an unbounded set of "how" questions while each fix added new surface; and
round 3's fixes were never re-reviewed, so any round-3 finding meant `fail`.

## Decision
The spec rubric limits `blocking` to six classes (wrong-build, contradiction,
false-claim, uncheckable, open-what, too-large). A "how" question the plan
can settle is a `[plan]` finding: not fixed in the spec, listed under
`## Plan questions` in the spec's gate record, answered by `/ship`'s plan
writer and checked by the plan gate. Both gates run up to 3 discovery rounds;
when the last one's blocking findings were fixed, up to 2 verification rounds
(a shared `spec-gate/verify.md`) check only those fixes and their diff, so at
most 5 rounds in all. Step numbers stay 1–7 in both gates. This supersedes
the "up to three rounds" sentences of ADRs 0015 and 0016, which are not
edited.

## Consequences
The user is asked only for real decisions or for a fix that stays wrong
after verification. A gate can cost up to 5 reviewer subagents. A question
can be misclassified as `[plan]`; the plan gate's Plan-questions check is the
backstop. Verification reviewers see the findings they verify, so they may
anchor on them; discovery reviewers stay context-free.
```

  Append this row to the table in `knowledge/decisions/README.md` (after
  the 0019 row):

```markdown
| [0020](0020-gates-end-with-verification.md) | Gates end with a verification round; blocking is a fixed set of classes | accepted | 2026-10-02 |
```

  In `plugin/.claude-plugin/plugin.json`, change `"version": "0.11.0"` to
  `"version": "0.12.0"`.

- [ ] **Step 5: Run the full suite and re-check this work's own spec
  (success criterion 8).**
  Run: `python -m pytest -q`
  Expected: all passed.
  Run: `python plugin/scripts/spec-lint.py docs/superpowers/specs/2026-10-02-gate-verification-round-design.md && python plugin/scripts/spec-lint.py --verify-record docs/superpowers/specs/2026-10-02-gate-verification-round-design.md`
  Expected: `clean`, then `ok: ...docs/superpowers/gates/2026-10-02-gate-verification-round-design.md`.

- [ ] **Step 6: Commit.**
  Run: `ruff check plugin tests && ruff format --check plugin tests`
  Expected: `All checks passed!`, nothing to reformat. Then:

```bash
git add conventions/spec-driven-development.md knowledge/decisions/0020-gates-end-with-verification.md knowledge/decisions/README.md plugin/.claude-plugin/plugin.json tests/test_spec_gate_skill.py tests/test_plugin_manifest.py
git commit -m "ADR 0020, convention and 0.12.0: gates end with verification

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: Reviewer comparison, old rubric against new

**Files:** none (results go into the PR description; nothing is committed)

**Depends on:** Task 1

- [ ] **Step 1: Save the old rubric.**
  Run: `git show main:plugin/skills/spec-gate/rubric.md > <scratchpad>/rubric-old.md && head -1 <scratchpad>/rubric-old.md`
  Expected: `# Spec gate rubric`.
- [ ] **Step 2: Run six reviewers.** For each spec in
  `docs/superpowers/specs/2026-10-01-spec-grill-design.md`,
  `docs/superpowers/specs/2026-09-30-ship-many-design.md` and
  `docs/superpowers/specs/2026-09-30-plan-gate-design.md`, dispatch two new
  general-purpose subagents (all six may run in parallel), each with only
  this prompt and absolute paths:

  > Review the design spec at `<worktree>/<spec>` in the repository at
  > `<worktree>`. Read `<rubric>` first and follow it exactly. Return only
  > the output format it defines.

  where `<rubric>` is `<scratchpad>/rubric-old.md` for the old arm and
  `<worktree>/plugin/skills/spec-gate/rubric.md` for the new arm (never the
  installed skill path, which resolves to the main checkout's old files).
  Save each output to `<scratchpad>/review-<old|new>-<spec file name>`.
- [ ] **Step 3: Count and compare.** For each output count the
  `### [blocking]` headings.
  Run: `grep -c '^### \[blocking\]' <scratchpad>/review-*`
  Expected: for each spec, new count ≤ old count. If one spec fails, rerun
  both arms once on that spec and compare the summed counts of the two runs;
  if it still fails, that is a stop under `/ship`'s stop-rule procedure:
  write the handoff, report the counts, and end without opening or merging
  the PR.
- [ ] **Step 4: Write the PR evidence.** Save to
  `<scratchpad>/comparison.md` a table of old/new blocking counts per spec,
  and a list of every old `[blocking]` finding that the new review does not
  raise as `[blocking]`, with the class or severity the new review gave the
  same problem (`[plan]`, `[minor]`, or "not raised"). This file is pasted
  into the PR description's Verification section.

### Task 7: One full new spec-gate run, then discard

**Files:** none (the run's spec and record changes are discarded)

**Depends on:** Task 2

- [ ] **Step 1: Run the gate by hand.** Follow
  `<worktree>/plugin/skills/spec-gate/SKILL.md` steps 1–6 on
  `docs/superpowers/specs/2026-10-01-spec-grill-design.md`, using the
  worktree's `plugin/skills/spec-gate/rubric.md` and
  `plugin/skills/spec-gate/verify.md` paths in the subagent prompts. Do not
  invoke the installed `claude-kit:spec-gate` skill.
- [ ] **Step 2: Check the record.**
  Run: `grep -E '^- \*\*Rounds:\*\* [0-9]+ discovery \+ [0-9]+ verification$|^## Plan questions$' docs/superpowers/gates/2026-10-01-spec-grill-design.md`
  Expected: two lines, the `Rounds:` line and `## Plan questions`. Report
  the `Rounds:` line as-is; a verification round is not required to occur.
  If the verdict is `pass`:
  Run: `python plugin/scripts/spec-lint.py --verify-record docs/superpowers/specs/2026-10-01-spec-grill-design.md`
  Expected: `ok: ...`.
- [ ] **Step 3: Discard the run.**
  Run: `git checkout -- docs/superpowers/specs/2026-10-01-spec-grill-design.md docs/superpowers/gates/2026-10-01-spec-grill-design.md && git status --short -- docs/superpowers/specs/2026-10-01-spec-grill-design.md docs/superpowers/gates/2026-10-01-spec-grill-design.md`
  Expected: no output (nothing modified). Save the verdict, `Rounds:` line
  and Plan questions count to `<scratchpad>/full-run.md` for the PR
  description.
