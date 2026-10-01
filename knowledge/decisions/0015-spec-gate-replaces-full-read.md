# ADR 0015: A spec gate replaces the user's full read of a spec

- **Status:** accepted
- **Date:** 2026-09-30

## Context
Specs are the contract `/ship` builds against without check-ins. The only
quality check was the brainstorming skill's self-review, by the session that
wrote the spec, plus the user's review. The user mostly does not read specs in
full, so gaps reached `/ship` and were either a stop rule or a silent guess.

## Decision
Every spec passes `claude-kit:spec-gate`: a deterministic linter
(`spec-lint.py`) plus up to three rounds of a new, context-free reviewer
subagent whose core probe is a dry-run plan. A pass does not approve the spec;
the user confirms a short verdict and the key decisions in one line. The gate
writes a record with the spec's hash (Status line excluded) under
`docs/superpowers/gates/`, and `/ship` requires a passing, current record.
Open product choices found by the gate always go to the user. It is enforced
through the workspace `CLAUDE.md` and `/ship`, not by editing the superpowers
plugin.

## Consequences
Specs get a rigorous read without the user's time; `/ship` should hit fewer
stop rules. Each gate costs one to three reviewer subagents. The reviewer's
quality is measured by a manual seeded-defect eval
(`tests/fixtures/spec-gate/`), not in CI, so it can drift unnoticed between
eval runs.
