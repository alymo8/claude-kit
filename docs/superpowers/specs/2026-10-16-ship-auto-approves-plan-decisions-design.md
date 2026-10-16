# `/ship` approves the plan gate's decisions itself

- **Status:** approved
- **Date:** 2026-10-16

## Purpose

`/ship` is meant to run autonomously once the user approves a spec. Today it
stops whenever the plan gate (step 3) returns `pass-with-decisions`: the plan
settled choices the spec left open, and `/ship` waits for a one-line OK. The
same stop fires on a resumed run whose plan record is still at
`decisions not approved`. In practice the user approves these lists as
written, so the stop costs a round trip and an interrupted run for no change
in outcome.

Each plan-introduced decision is already a concrete choice the plan made (the
gate lists what the plan decided, not open options), so "the recommended
decision" is the plan's own choice. This change makes `/ship` approve those
decisions itself and continue, recording that it did so, and listing them in
the PR and the final report. Two cases still stop: a gate `fail`, and any
plan-introduced decision about an irreversible action.

Running `claude-kit:plan-gate` by hand, outside `/ship`, is unchanged: its
step 7 still asks the user. `/ship-many` runs each spec as a headless `/ship`,
so it inherits the change with no edit of its own.

## Scope

**In:**
- `plugin/commands/ship.md`: step 3, the plan-gate stop rule, step 7 (PR
  body) and step 12 (report), as in Design.
- `tests/test_ship_command.py`: update the tests that assert the old stop;
  add the tests in Testing.
- `tests/test_spec_lint.py`: a test that a record carrying the new
  `Approved by` line still verifies.
- `CLAUDE.md`: the "Gate every plan" sentence about `/ship`.
- `conventions/spec-driven-development.md`: the "Under `/ship`, anything but
  `pass` stops the run" sentence.
- `knowledge/kit-dev-gotchas.md`: the Gates bullet that says `/ship` stops
  for a one-line OK on a plan-introduced decision.
- `knowledge/decisions/0036-ship-auto-approves-plan-decisions.md` (new) and
  `knowledge/decisions/README.md` (a row for 0036; 0016's status becomes
  `accepted; amended by 0036`, and 0027's becomes
  `accepted; amended by 0032, 0036`, in the index and in each ADR's Status
  line).
- `knowledge/decisions/0016-plan-gate-signs-off-on-new-decisions-only.md`:
  one line noting that ADR 0036 amends it for `/ship`.
- `knowledge/decisions/0027-adr-triggers.md`: one line under Consequences
  noting that ADR 0036 amends the "reach the user through the plan gate's
  sign-off" consequence for `/ship` (see ADR-trigger decisions below).
- `docs/superpowers/README.md`: index rows for this spec and its plan.
- `plugin/.claude-plugin/plugin.json`: minor version bump (0.24.0 → 0.25.0).
- `tests/test_plugin_manifest.py`: update the pinned version assertion to
  `0.25.0`.

**Out:**
- `plugin/skills/plan-gate/SKILL.md` and `rubric.md`: the gate's verdicts,
  record format and manual report are unchanged.
- `plugin/scripts/spec-lint.py`: `--verify-record` already accepts a record
  with a `Decisions approved` line; no code change.
- `/ship-fast` (it skips the gates) and `/ship-many` (inherits via `/ship`).
- The spec-gate stop in step 0 and the gate `fail` stop.

## Design

### Step 3, on `pass-with-decisions`

Replace "then the plan-gate stop rule fires" for `pass-with-decisions` with:

3a. Read the record's `## Plan-introduced decisions`. If any decision is
   **irreversible** (see below), the plan-gate stop rule fires, reporting
   that decision (and the rest of the list) as before.
3b. Otherwise approve them: add, below the record's `Verdict` line,

   ```
   - **Decisions approved:** <today>
   - **Approved by:** /ship (auto)
   ```

   and set the plan's Status to `approved` (neither changes a hash).
3c. For each approved decision that matches a MUST trigger in the decision-log
   playbook (`conventions/decision-log.md`, or the repo's decisions README
   trigger list, as ADR 0027 reads them), `/ship` writes the ADR file and
   its decisions README row now, and commits them in 3e below. It
   does not edit the plan: any plan edit changes the plan's hash and makes
   the gate record stale. A repo with no ADR folder and no trigger list
   skips this, as ADR 0027 does (see ADR-trigger decisions below).
3d. Write a `Ruling:` ledger line naming the record and the number of
   decisions approved.
3e. Commit the plan, its record and any ADRs from 3c, and continue to
   step 4.

`fail` is unchanged: commit, then the stop rule fires.

### Resumed runs

When step 3 finds an existing plan whose `--verify-record` prints
`decisions not approved`, apply the same rule to that record: approve and
continue unless a decision is irreversible. This replaces "rerunning `/ship`
is never approval". A record that the user previously declined does not exist
as a state (a decline leads to a plan edit and a re-gate), so this cannot
override a user's "no".

### Irreversible decisions

A plan-introduced decision is irreversible when carrying it out would delete,
overwrite or migrate data that is not regenerable from the repo (user files,
databases, remote state), rewrite published git history, or change something
outside the repository that cannot be undone by reverting the PR (an external
service, a published package, another repo). `/ship` judges each decision
against this definition; when unsure, it treats the decision as irreversible
and stops. This follows the workspace rule that decisions about
"data/irreversible actions" are confirmed explicitly.

### ADR-trigger decisions

A plan-introduced decision that hits a decision-log MUST trigger (it changes
a workflow, an interface, or another listed trigger) is approved like any
other, and `/ship` writes its ADR on the feature branch. The user reviews
that ADR in the PR diff, as with ADRs that `capture-learnings` writes
(ADR 0031). An ADR-trigger decision that is also irreversible still stops.

### Stop rule wording

The plan-gate stop rule becomes: the plan gate returns `fail`; or it returns
`pass-with-decisions` (or a resumed record is at `decisions not approved`) and
at least one plan-introduced decision is irreversible. Drop the sentence
"`/ship` approves the spec, not decisions a plan adds later" and replace it
with "only irreversible plan-introduced decisions need the user". The rest of
the rule (what to report, what to do when the user answers) stays.

### Visibility

- **PR body (step 7):** a `Plan decisions (auto-approved)` section listing
  each plan-introduced decision verbatim, or omitted when there were none.
- **Report (step 12):** the same list, after the review findings.

### ADR 0036

**`/ship` approves the plan gate's decisions itself.** Context: ADR 0016 has
the user sign off on decisions a plan adds; under `/ship` that stop
interrupted autonomous runs while the user approved the lists as written.
Decision: under `/ship`, plan-introduced decisions are approved automatically
and recorded with `Approved by: /ship (auto)`, except irreversible ones;
a decision that hits a decision-log MUST trigger gets its ADR written on the
feature branch; a gate `fail` still stops; the manual plan gate still asks. Consequences: the
user sees these decisions first in the PR and report, possibly after the
merge; reverting the PR undoes them, which is why irreversible ones still
stop. Amends ADR 0016 and the sign-off consequence of ADR 0027 for `/ship`
only; it amends rather than supersedes them because ADR 0016 still governs
the manual plan gate.

## Decisions

- **Only `pass-with-decisions` is auto-approved;** `fail` still stops, since
  its Open items have no settled answer.
- **Irreversible decisions still stop** `/ship`.
- **Audit trail:** the existing `Decisions approved` line plus a separate
  `- **Approved by:** /ship (auto)` line (the linter's regex needs the date
  line unchanged).
- **ADR-trigger decisions are approved,** and `/ship` writes their ADR on
  the feature branch for review in the PR.
- **Resumed records at `decisions not approved`** are approved the same way.
- **The manual plan gate is unchanged.**

## Testing

- `tests/test_ship_command.py`:
  - the stop-rules section names `fail` and "irreversible", and no longer
    says the rule fires on every `pass-with-decisions`;
  - step 3 contains `Decisions approved`, `Approved by:** /ship (auto)` and a
    `Ruling:` line for the approval;
  - step 3 no longer contains "never approval";
  - step 7 names the `Plan decisions (auto-approved)` section and step 12
    lists the decisions.
- `tests/test_spec_lint.py`: a `pass-with-decisions` record with both the
  `Decisions approved` and `Approved by` lines makes `--verify-record` print
  `ok:`.

## Success criteria

Agreed with the user before the work:

1. `pytest` passes, including the tests above.
2. `ruff check plugin tests` and `ruff format --check plugin tests` are clean.
3. `git grep -n -i "stops on any plan-introduced\|anything but .pass. stops\|stops for a one-line OK" CLAUDE.md conventions knowledge/kit-dev-gotchas.md`
   returns no match.
