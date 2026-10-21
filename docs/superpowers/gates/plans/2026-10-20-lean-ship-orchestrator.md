# Plan gate: `/ship` keeps its main session lean Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-20-lean-ship-orchestrator.md
- **Plan SHA-256:** f2e11fc69e71acfeed3ecb268a0338531fc1b9d1b4e6b07b49bf107e6bc1d3af
- **Spec:** docs/superpowers/specs/2026-10-20-lean-ship-orchestrator-design.md
- **Spec SHA-256:** 1b14366989b1f12338fe89ac3a72094c38d68ac1a75094d3a7603d63c239e8d9
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-10-20
- **Approved by:** /ship (auto)
- **Date:** 2026-10-20
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- Before the first plan-subagent dispatch with an existing plan, `/ship` copies that plan and its record to the scratchpad; on a failed check it restores both from those copies, deletes the files the subagent created, then retries. (Task 4)
- A red suite after an SDD task is fixed in the main session with `superpowers:systematic-debugging`, not by resuming the implementer; step 4's "Before every commit run the full test suite and lint" sentence stays. (Task 4)
- SDD's rulings and parked or deferred findings go only in the step-12 report under "anything left out and why"; the PR body is unchanged. (Task 4)
- Step 6 treats step 4's final review as having run only if this session received that review's report during step 4 of this run; a run resumed in another session runs step 6 as today. (Task 4)
- `parallel-tasks` decides its caller is `/ship` from the session's command context (the run was started by `/ship` or `/claude-kit:ship`), not from an argument. (Task 3)
- `--ship`: each session file is one row, so a run resumed across sessions gives several rows; a headless `/ship-many` child matches only if its transcript carries the command-name tag. (Task 2)
- `--ship` details: peak context is the largest input + cache_creation + cache_read of any main-session assistant record; the date is the first record's `timestamp`; it uses the same file set as `--project` and `--all`; it prints only the ship table, replacing the normal report; the median line shows `median` and `-` in the id and date columns. (Task 2)

## Findings fixed

- round 1 [blocking] Success criterion 3 is checked by no task: Task 5 gains a step running `--verify-record` on the spec and the plan; criterion added to Global Constraints.
- round 1 [minor] "SDD's task loop" could omit the skill name the tests need: each of the three passages must name `superpowers:subagent-driven-development` in full; the Caller bullet defines SDD.
- round 1 [minor] Restoring an untracked plan from git fails: the existing plan and record are copied to the scratchpad before the first dispatch and restored from there.
- round 1 [minor] Step-3 items could become a column-0 list: items are prose indented 3 spaces; no column-0 numbered lines.
- round 2 [minor] Failed-task passage must keep the phrase the test splits on: kept explicitly.
- round 2 [minor] `--ship` session id length: `sid = path.stem[:8]`.

## Open

- none
