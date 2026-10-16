# `/ship` approves the plan gate's decisions itself Implementation Plan

- **Status:** draft
- **Date:** 2026-10-16

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/ship` approve a plan gate's `pass-with-decisions` itself and continue, stopping only on a gate `fail` or an irreversible plan-introduced decision, and record, document and test that.

**Architecture:** `/ship` is a Markdown command (`plugin/commands/ship.md`) whose text tests pin with string assertions (`tests/test_ship_command.py`). The change rewrites its plan-gate stop rule, step 3, step 7 (PR body) and step 12 (report). `spec-lint.py` is unchanged; one regression test pins that a record with the new `Approved by` line still verifies. Prose in `CLAUDE.md`, the conventions and the gotchas is updated, a new ADR 0036 amends ADRs 0016 and 0027, and the plugin version goes to 0.25.0.

**Tech Stack:** Markdown, Python 3 (pytest, ruff), JSON.

**Spec:** `docs/superpowers/specs/2026-10-16-ship-auto-approves-plan-decisions-design.md`

## Context for the executor

This repo is claude-kit: a Claude Code plugin under `plugin/` plus workspace
conventions under `conventions/`. Commands (`plugin/commands/*.md`) are prompts
whose text tests check with string assertions. `tests/helpers.py` exports
`PLUGIN` (`REPO / "plugin"`) and `run_script(script, *args, ...)`.
`tests/test_ship_command.py` has `_step(n)`, which returns step `n` of
`ship.md` with whitespace collapsed to single spaces; it splits steps on lines
that start, at column 0, with `<digits>. `. `_stops()` returns the
`## Stop rules` section.

Why: under `/ship`, the user approved plan-introduced decision lists as written,
so the stop cost a round trip for no change in outcome. Decided (do not
relitigate): only `pass-with-decisions` is auto-approved, `fail` still stops;
irreversible decisions still stop; the audit trail is the unchanged
`Decisions approved` line plus a separate `- **Approved by:** /ship (auto)`
line; decisions that hit an ADR MUST trigger are approved and `/ship` writes
their ADR; resumed records at `decisions not approved` are approved the same
way; running the plan gate by hand is unchanged.

`plugin/commands/ship.md`, `CLAUDE.md`, `conventions/spec-driven-development.md`
and `knowledge/kit-dev-gotchas.md` use
CRLF line endings: edit with the Edit tool (it keeps them), and run
`ruff format` only on Python files.

Before every commit run, from the repo root:

```bash
pytest
ruff check plugin tests
ruff format --check plugin tests
```

`pytest` must exit 0 (`pyproject.toml` sets `-q`; plain `pytest` prints the
summary). Every commit message ends with a blank line and
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Global Constraints

- Approval lines, exactly: `- **Decisions approved:** <YYYY-MM-DD>` then `- **Approved by:** /ship (auto)`.
- PR body and report section name, exactly: `Plan decisions (auto-approved)`.
- New ADR number is 0036, file `knowledge/decisions/0036-ship-auto-approves-plan-decisions.md`, dated 2026-10-16.
- ADR statuses: 0016 becomes `accepted; amended by 0036`; 0027 becomes `accepted; amended by 0032, 0036`.
- Plugin version becomes `0.25.0`.
- No private repo names or machine usernames in tracked files.

## Plan questions answered (from the spec's gate record)

- The stop-rule sentence "`/ship` approves the spec, not decisions a plan adds later" is replaced by "Only irreversible plan-introduced decisions need the user." (Task 1.)
- Tests assert these exact phrases: in the stop rules, absent "returns `pass-with-decisions` or `fail`" and "approves the spec, not decisions a plan adds later"; present "irreversible" and "only irreversible plan-introduced decisions need the user". Step 12 contains `Plan decisions (auto-approved)`. (Task 1.)
- The kit-dev-gotchas Gates bullet is reworded, not removed (Task 3).
- When the user approves after an irreversible-decision stop, the record gets only `Decisions approved`, with no `Approved by` line: that part of the stop rule stays as it is. (Task 1.)
- The PR and report list the plan record's decisions whenever it has any (the spec: "omitted when there were none"): under `Plan decisions (auto-approved)` when the record has `- **Approved by:** /ship (auto)`, else under `Plan decisions`, so a user-approved list is never labelled auto-approved. (Task 1.)
- `test_version_is_0_24_0` is renamed `test_version_is_0_25_0` (Task 4).

## Review Focus

- A sub-step line in step 3 that starts at column 0 with `<digit>. ` would split step 3 in `_step()`: the sub-steps are indented and labelled `(3a)`–`(3e)` (Task 1 test `test_step_three_sub_steps_stay_inside_step_three`).
- A resumed record at `decisions not approved` whose list has an irreversible decision must still stop (Task 1 test `test_stop_rule_fires_on_irreversible_decisions`).
- Writing an ADR for an approved decision must not edit the plan, or the record goes stale (Task 1 test `test_step_three_does_not_edit_the_plan_for_adrs`).
- A record with `Approved by` added still verifies `ok:` (Task 2).
- A user-approved list (after a stop) must not be labelled auto-approved in the PR (Task 1 test `test_pr_lists_auto_approved_decisions`).

---

### Task 1: `/ship` auto-approves `pass-with-decisions`

**Files:**
- Modify: `plugin/commands/ship.md` (the plan-gate bullet under `## Stop rules`; steps 3, 7 and 12)
- Test: `tests/test_ship_command.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: the phrases in Global Constraints, which Task 3's prose refers to.

- [ ] **Step 1: Update and add the failing tests in `tests/test_ship_command.py`**

In `test_step_three_resumes_an_existing_plan_by_its_spec_line`, replace
`assert "never approval" in step` with `assert "never approval" not in step`.
Replace `test_plan_gate_is_a_stop_rule` with the tests below (they use the
file's existing `_step` and `_stops`):

```python
def test_plan_gate_is_a_stop_rule():
    stops = _stops().lower()
    assert "plan gate" in stops
    assert "`fail`" in stops
    assert "decisions approved" in stops


def test_stop_rule_fires_on_irreversible_decisions():
    stops = " ".join(_stops().lower().split())  # phrases may wrap across lines
    assert "irreversible" in stops
    assert "decisions not approved" in stops
    assert "only irreversible plan-introduced decisions need the user" in stops
    assert "returns `pass-with-decisions` or `fail`" not in stops
    assert "approves the spec, not decisions a plan adds later" not in stops


def test_step_three_auto_approves_decisions():
    step = _step(3)
    assert "- **Decisions approved:** <today>" in step
    assert "- **Approved by:** /ship (auto)" in step
    assert "Ruling:" in step
    assert "irreversible" in step


def test_step_three_does_not_edit_the_plan_for_adrs():
    step = _step(3)
    assert "MUST trigger" in step
    assert "Do not edit the plan" in step


def test_step_three_sub_steps_stay_inside_step_three():
    step = _step(3)
    for label in ("(3a)", "(3b)", "(3c)", "(3d)", "(3e)"):
        assert label in step
    assert "**Plan gate:**" in step and "**Implement.**" not in step


def test_pr_lists_auto_approved_decisions():
    step = _step(7)
    assert "Plan decisions (auto-approved)" in step
    assert "- **Approved by:** /ship (auto)" in step
    assert "`Plan decisions` otherwise" in step


def test_report_lists_auto_approved_decisions():
    assert "Plan decisions (auto-approved)" in _step(12)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `pytest tests/test_ship_command.py`
Expected: FAIL in the tests above (for example `test_stop_rule_fires_on_irreversible_decisions`, `test_step_three_auto_approves_decisions`).

- [ ] **Step 3: Rewrite the plan-gate stop rule in `plugin/commands/ship.md`**

Replace the whole bullet that starts "The plan gate in step 3 returns" with:

```
- The plan gate in step 3 returns `fail`; or it returns `pass-with-decisions`
  (or a resumed run finds the plan record at `decisions not approved`) and at
  least one plan-introduced decision is irreversible (step 3 defines it).
  Report the record's Plan-introduced decisions and Open items as questions
  (if the gate stopped at `P4-spec-gated` and wrote no record, report that
  reason and that the spec must pass `claude-kit:spec-gate`). Only
  irreversible plan-introduced decisions need the user. When the user
  answers: on approval, add `- **Decisions approved:** <today>` to the record
  and set the plan's Status to `approved`; otherwise update the plan (or the
  spec, which is gated again) and rerun the plan gate. Commit, and continue
  `/ship` from step 4.
```

- [ ] **Step 4: Rewrite step 3's two decision branches**

Replace "On `decisions not approved`, do not rerun the gate: the plan-gate stop
rule fires (rerunning `/ship` is never approval; only the user's answer is)."
with "On `decisions not approved`, do not rerun the gate: handle the record as
for `pass-with-decisions` below, from (3a)."

Replace "On `pass-with-decisions` or `fail`, commit the plan and its record
(the plan only, if the gate stopped at `P4-spec-gated`), then the plan-gate
stop rule fires." with the text below. Keep every line indented by three
spaces, like the rest of step 3, so no line starts at column 0:

```
   On `fail`, commit the plan and its record (the plan only, if the gate
   stopped at `P4-spec-gated`), then the plan-gate stop rule fires. On
   `pass-with-decisions`:
   (3a) Read the record's `## Plan-introduced decisions`. A decision is
   **irreversible** when carrying it out would delete, overwrite or migrate
   data not regenerable from the repo (user files, databases, remote state),
   rewrite published git history, or change something outside the
   repository that reverting the PR cannot undo (an external service, a
   published package, another repo); when unsure, treat it as irreversible.
   If any decision is irreversible, commit the plan and its record, then the
   plan-gate stop rule fires.
   (3b) Otherwise add, below the record's `Verdict` line,
   `- **Decisions approved:** <today>` and then
   `- **Approved by:** /ship (auto)`, and set the plan's Status to
   `approved` (neither changes a hash).
   (3c) For each approved decision that hits a MUST trigger of the
   decision-log playbook (the trigger list in the repo's decisions README,
   else `conventions/decision-log.md`, else `../conventions/decision-log.md`,
   as ADR 0027 reads them), write its
   ADR file and its decisions README row now. Do not edit the plan: any plan
   edit changes its hash and makes the record stale. A repo with no ADR
   folder and no trigger list skips this.
   (3d) Write a `Ruling:` ledger line naming the record and the number of
   decisions approved.
   (3e) Commit the plan, its record and any ADRs from (3c), and continue to
   step 4.
```

- [ ] **Step 5: Add the decisions to step 7's PR body and step 12's report**

In step 7, after "the plan gate record (`docs/superpowers/gates/plans/<plan file name>`),"
insert: "a section that lists verbatim each entry of the plan record's
`## Plan-introduced decisions` (omit it when that list is `none`), titled
`Plan decisions (auto-approved)` when the record has
`- **Approved by:** /ship (auto)` and `Plan decisions` otherwise,".

In step 12, after "the review findings you fixed," insert: "the
`Plan decisions (auto-approved)` (or `Plan decisions`) list from step 7, if
any,".

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `pytest tests/test_ship_command.py`
Expected: PASS (all tests in the file).

- [ ] **Step 7: Run the full suite and lint, then commit**

Run the three commands from Context; all must pass.

```bash
git add plugin/commands/ship.md tests/test_ship_command.py
git commit -m "/ship approves the plan gate's decisions itself" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: A record with `Approved by` still verifies

**Files:**
- Test: `tests/test_spec_lint.py`

**Depends on:** none

**Interfaces:**
- Consumes: the file's existing `plan_gated(root, verdict="pass", plan_digest=None, spec_digest=None, approved=False)` (returns the plan path; writes the record under `root/docs/superpowers/gates/plans/<plan name>`), `run_script`, `SCRIPT` and the `root` fixture.
- Produces: nothing.

- [ ] **Step 1: Add the test after `test_verify_plan_record_survives_ticks_and_approval`**

```python
def test_verify_plan_record_accepts_auto_approval(root):
    plan = plan_gated(root, "pass-with-decisions", approved=True)
    record = root / "docs" / "superpowers" / "gates" / "plans" / plan.name
    text = record.read_text(encoding="utf-8")
    record.write_text(text + "- **Approved by:** /ship (auto)\n", encoding="utf-8")
    result = run_script(SCRIPT, "--verify-record", str(plan), "--root", str(root))
    assert result.returncode == 0
    assert result.stdout.startswith("ok:")
```

- [ ] **Step 2: Run it**

Run: `pytest tests/test_spec_lint.py::test_verify_plan_record_accepts_auto_approval`
Expected: PASS (this pins existing behaviour; `spec-lint.py` is not changed).

- [ ] **Step 3: Run the full suite and lint, then commit**

```bash
git add tests/test_spec_lint.py
git commit -m "Pin that an auto-approved plan record verifies" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: ADR 0036 and prose

**Files:**
- Create: `knowledge/decisions/0036-ship-auto-approves-plan-decisions.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `knowledge/decisions/0016-plan-gate-signs-off-on-new-decisions-only.md`
- Modify: `knowledge/decisions/0027-adr-triggers.md`
- Modify: `CLAUDE.md`
- Modify: `conventions/spec-driven-development.md`
- Modify: `knowledge/kit-dev-gotchas.md`
- Modify: `docs/superpowers/README.md` (generated index; regenerated, never edited by hand)

**Depends on:** none

**Interfaces:**
- Consumes: the phrases in Global Constraints.
- Produces: nothing.

- [ ] **Step 1: Write ADR 0036**

Shape it like `knowledge/decisions/0031-capture-learnings-at-feature-finish.md`
(`# ADR 0036: /ship approves the plan gate's decisions itself`, a
`- **Status:** accepted` and `- **Date:** 2026-10-16` bullet, then
`## Context`, `## Decision`, `## Consequences`). Content:
- Context: ADR 0016 has the user sign off on decisions a plan adds; under `/ship` that stop interrupted autonomous runs while the user approved the lists as written. ADR 0027 relied on that sign-off to bring ADR-worthy plan decisions to the user.
- Decision: under `/ship`, a plan gate `pass-with-decisions` (and a resumed record at `decisions not approved`) is approved by `/ship`, recorded as `- **Decisions approved:** <date>` plus `- **Approved by:** /ship (auto)`; an irreversible decision (data not regenerable from the repo, rewritten published history, or an external change a PR revert cannot undo; when unsure, irreversible) still stops; a decision that hits a decision-log MUST trigger gets its ADR written by `/ship` on the feature branch without editing the plan; a gate `fail` still stops; the manual plan gate still asks the user.
- Consequences: the user sees these decisions first in the PR's `Plan decisions (auto-approved)` section and the final report, possibly after the merge; reverting the PR undoes them, which is why irreversible ones still stop. It amends rather than supersedes ADRs 0016 and 0027, because ADR 0016 still governs the manual plan gate.

- [ ] **Step 2: Update the ADR index and the amended ADRs**

In `knowledge/decisions/README.md`: append the row
`| [0036](0036-ship-auto-approves-plan-decisions.md) | `/ship` approves the plan gate's decisions itself | accepted | 2026-10-16 |`
after the 0035 row; set 0016's Status cell to `accepted; amended by 0036` and
0027's to `accepted; amended by 0032, 0036`.

In ADR 0016, set the Status bullet to
`- **Status:** accepted; amended by 0036 ([ADR 0036](0036-ship-auto-approves-plan-decisions.md): under `/ship`, plan-introduced decisions are approved automatically unless irreversible)`.

In ADR 0027, append to the Status bullet
`, 0036 ([ADR 0036](0036-ship-auto-approves-plan-decisions.md): under `/ship`, MUST-trigger plan decisions get their ADR written by `/ship`)`
so it reads "amended by 0032 (...), 0036 (...)", and add under Consequences,
after the bullet that ends "(ADR 0016).", the bullet
`- Under `/ship`, ADR 0036 amends that: `/ship` approves the plan's decisions itself and writes the ADR for any that hit a MUST trigger.`

- [ ] **Step 3: Update the prose**

- `CLAUDE.md`, under "Gate every plan": replace "`/ship` gates its own plan and stops on any plan-introduced decision." with "`/ship` gates its own plan and approves the decisions it lists itself, stopping only on a `fail` or an irreversible decision ([ADR 0036](knowledge/decisions/0036-ship-auto-approves-plan-decisions.md))."
- `conventions/spec-driven-development.md`: replace "Under `/ship`, anything but `pass` stops the run." (it wraps over two lines) with "Under `/ship`, `/ship` approves a `pass-with-decisions` itself unless a decision is irreversible, and a `fail` stops the run."
- `knowledge/kit-dev-gotchas.md`, the Gates bullet that starts "Answering a spec gate's `## Plan questions`": replace "and `/ship` stops for a one-line OK" with ", and `/ship` approves the decision itself and lists it in the PR's `Plan decisions (auto-approved)` section", and replace "Keep answers inside Scope In to avoid the stop." with "Keep answers inside Scope In to keep that list short."

- [ ] **Step 4: Verify no old wording is left**

Run: `git grep -n -i "stops on any plan-introduced\|anything but .pass. stops\|stops for a one-line OK" CLAUDE.md conventions knowledge/kit-dev-gotchas.md`
Expected: no output, exit 1.

- [ ] **Step 5: Regenerate the spec index**

Run: `python plugin/scripts/spec-index.py docs/superpowers`
Expected: `docs/superpowers/README.md` has a row for
`plans/2026-10-16-ship-auto-approves-plan-decisions.md` whose status matches
the plan's Status line (`approved` once `/ship` has approved the plan), and a
row for the spec.

- [ ] **Step 6: Run the full suite and lint, then commit**

```bash
git add knowledge CLAUDE.md conventions/spec-driven-development.md docs/superpowers/README.md
git commit -m "ADR 0036: /ship approves the plan gate's decisions itself" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: Version 0.25.0

**Files:**
- Modify: `plugin/.claude-plugin/plugin.json`
- Test: `tests/test_plugin_manifest.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

- [ ] **Step 1: Update the test**

Rename `test_version_is_0_24_0` to `test_version_is_0_25_0` and change its
assertion to `assert data["version"] == "0.25.0"`.

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/test_plugin_manifest.py::test_version_is_0_25_0`
Expected: FAIL (`'0.24.0' == '0.25.0'`).

- [ ] **Step 3: Set `"version": "0.25.0"` in `plugin/.claude-plugin/plugin.json`**

- [ ] **Step 4: Run it and confirm it passes**

Run: `pytest tests/test_plugin_manifest.py::test_version_is_0_25_0`
Expected: PASS.

- [ ] **Step 5: Run the full suite and lint, then commit**

```bash
git add plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py
git commit -m "Bump the plugin to 0.25.0" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Verification (the spec's success criteria)

1. `pytest` exits 0, including the tests from Tasks 1, 2 and 4.
2. `ruff check plugin tests` and `ruff format --check plugin tests` are clean.
3. `git grep -n -i "stops on any plan-introduced\|anything but .pass. stops\|stops for a one-line OK" CLAUDE.md conventions knowledge/kit-dev-gotchas.md` returns no match.
