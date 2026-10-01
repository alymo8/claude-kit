# Gate: Plan gate: linter rules and independent plan reviewer

- **Spec:** docs/superpowers/specs/2026-09-30-plan-gate-design.md
- **Spec SHA-256:** b2561ddc9b87ab5a172176eddd095a237c6c40dd7514c32c8b93c02521dd226e
- **Verdict:** fail
- **Date:** 2026-09-30
- **Rounds:** 3

## Key decisions

- Separate follow-up spec; the merged spec-gate spec is not edited (Decisions, Scope Out)
- The user signs off only on plan-introduced decisions; a `pass` plan goes straight to execution (Purpose, Decisions)
- One linter, plan rules chosen by parent folder name `plans` (Decisions)
- A plan can pass only on a gated spec (P4); the plan record pins the spec hash (Decisions, Plan hashing)
- The plan hash ignores the Status bullet and ticked checkboxes (Plan hashing)
- Plan records under `docs/superpowers/gates/plans/`; verdicts pass, pass-with-decisions (needs `Decisions approved`), fail (Plan hashing and records)
- The plan gate never edits the spec (SKILL.md, Decisions)
- Under `/ship`, pass-with-decisions or fail stops the run; rerunning `/ship` is never approval (`/ship` changes)
- No per-section design approval during spec creation, shipped with the plan gate on purpose (Decisions, CLAUDE.md changes)
- Existing plans are not retrofitted; back-test only (Scope Out, criterion 6)
- Reviewer eval is manual: at least 5/6 on both runs, at most 1 blocking on the control (criterion 7)
- Plugin 0.6.0 → 0.7.0; ADR 0016 (Scope)

## Findings fixed

- pre-round lint: L8-path on `plans/` and the ADR path; scope aligned with the merged spec gate (L8 is Scope-only, `tests/test_plan_gate_skill.py`, `ok:` output); dropped the edit to the merged spec-gate spec (would invalidate its record)
- round 1 [blocking] four vs five existing plans; P4 passes for the spec-gate plan
- round 1 [blocking] P6 "step" and "fenced command block" defined; Run/Expected only outside fences
- round 1 [blocking] /ship stop: commit plan and record first; approval adds `Decisions approved`; resume does not rewrite the plan
- round 1 [blocking] criterion 8 path for pass-with-decisions
- round 1 [minor] checkbox hash scope; which spec path is hashed; ADR index row; manifest description
- round 2 [blocking] P9 no longer checks `- Test:` paths (writing-plans lists new tests there)
- round 2 [blocking] eval uses hypothetical-feature plans, blind detached checkout, shuffled names
- round 2 [blocking] resume with `decisions not approved` shows decisions and stops; rerun is never approval
- round 2 [minor] prerequisite wording; shape origin; reason order; P4 stop writes no record; exact `## Designing a spec` heading and phrase
- round 3 [blocking] end-to-end check reworded: runs after implementation with the worktree's skill, reviewers on a detached checkout of the plan commit
- round 3 [blocking] resume finds the plan by its `**Spec:**` line, not by today's date
- round 3 [minor] P5 counting rule; P3 owns a malformed `**Spec:**` line; docs/ADR/manifest criterion; decision note for the no-pause rule

## Open

- Round limit reached: round 3's two blocking findings are fixed in the spec but no fresh reviewer has confirmed the fixes. No decision findings are open.
