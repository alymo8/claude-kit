# Plan gate: `/ship` approves the plan gate's decisions itself Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-16-ship-auto-approves-plan-decisions.md
- **Plan SHA-256:** 18e56216be43e1ddeb09af8a1cb3b554d1cab5e041d8138203aee87e165c1e8c
- **Spec:** docs/superpowers/specs/2026-10-16-ship-auto-approves-plan-decisions-design.md
- **Spec SHA-256:** 3f66a46faabb7dd25c6ae5715f6130af37c5aec8decc3cb2c0c4e2c2b399e6a2
- **Verdict:** pass-with-decisions
- **Date:** 2026-10-16
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- When the user approves after an irreversible-decision stop, the PR body and report still list the decisions, titled `Plan decisions` instead of `Plan decisions (auto-approved)`; the title is keyed on the record's `- **Approved by:** /ship (auto)` line. (Task 1)
- Approval by the user after an irreversible-decision stop writes only `Decisions approved`, with no `Approved by` line. (Task 1)

## Findings fixed

- round 1 [blocking] New stop-rule test fails on the prescribed line wrap: `test_stop_rule_fires_on_irreversible_decisions` now collapses whitespace in `_stops()`.
- round 1 [blocking] No task delivered the `docs/superpowers/README.md` index row for the plan: Task 3 regenerates it with `spec-index.py` and commits it.
- round 2 [minor] CRLF note missed `conventions/spec-driven-development.md`: added.
- round 2 [minor] (3c) trigger-list fallback was shorter than ADR 0027's: added `../conventions/decision-log.md`.
- round 2 [minor] Gotchas rewording read awkwardly: reworded.

## Open

- none
