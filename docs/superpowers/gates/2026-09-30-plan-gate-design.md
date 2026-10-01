# Gate: Plan gate: linter rules and independent plan reviewer

- **Spec:** docs/superpowers/specs/2026-09-30-plan-gate-design.md
- **Spec SHA-256:** 7d68085ef1735e115c089af39c9ac03b2e5970430af623959d19fba68d8d7576
- **Verdict:** pass
- **Date:** 2026-09-30
- **Rounds:** 4 (3 in the first run, which failed on the round limit; 1 in the rerun)

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
- rerun round 1: no blocking findings
- rerun round 1 [minor] plan Status lifecycle (draft when written, approved on pass or approved decisions); P4 stop reported without a record under /ship; `spec not found` message; P4 alongside other violations; record holds the last round's decisions; eval renaming and defect-6 hit rule; reason order in prose

## Open

- none
