# ADR 0016: A plan gate, with sign-off only on decisions the plan adds

- **Status:** accepted
- **Date:** 2026-09-30

## Context
The user does not read implementation plans, and a plan is the only context
its executor gets. A gap in a plan (a spec item no task covers, a task that
cannot be done from the plan alone, a choice the spec never made) reached the
build unchecked: it was guessed silently or fired a `/ship` stop rule partway
through. The spec gate (ADR 0015) checks specs only.

## Decision
Every plan passes `claude-kit:plan-gate`: plan rules P1–P9 in `spec-lint.py`
(chosen when the file's folder is `plans`) plus up to three rounds of a new,
context-free reviewer that maps spec items to tasks, executes each task cold,
and lists the plan's own decisions. The user signs off only on those
plan-introduced decisions; a plan with none goes straight to execution. A
plan can pass only on a gated spec, and its record under
`docs/superpowers/gates/plans/` pins both the plan's and the spec's hash. The
plan hash ignores the Status line and ticked checkboxes. Under `/ship`, any
plan-introduced decision stops the run, because invoking `/ship` approves the
spec, not choices made after it. Alongside, spec design no longer pauses for
approval between design sections; the gates do that review.

## Consequences
Plans get a rigorous read without the user's time, and routine plans do not
interrupt the user at all. Each gate costs one to three reviewer subagents. A
`/ship` run stops more often when its plan makes real decisions; the plan
writer is told to prefer choices the spec, ADRs or code already imply. The
reviewer's quality is measured by a manual seeded-defect eval
(`tests/fixtures/plan-gate/`), not in CI.
