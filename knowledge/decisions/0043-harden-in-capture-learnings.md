# ADR 0043: Harden step in capture-learnings

- **Status:** accepted
- **Date:** 2026-11-10

## Context
Learnings captured at the end of a feature were notes. Mechanical mistakes
(a missed lint rule, a repeated manual check) kept recurring because a note is
not a guardrail, while judgement calls had no home the reviewers could read.

## Decision
`capture-learnings` gains a Harden step. Mechanical mistakes are proposed as a
hook, test or script change, never built by the step. Under `/ship`,
`/ship-fast` and the `/ship-many` children, which pass `--auto`, the step only
lists the proposals; a hand run asks the user. Judgement calls go to
`knowledge/review-standards.md`, a file only the standards reviewer reads. A
scan for steering that was needed during the session is report-only.
A hand run is told from an automated one by the `--auto` argument that `/ship`
and `/ship-fast` pass in step 7. Files changed by the branch's `Capture
learnings` commit (`CLAUDE.md`, `knowledge/` entries, an ADR) are process
files and never scope creep in `claude-kit:review`.
Rejected: a separate `/retro` skill (one more thing to remember to run);
putting the step in `/ship`'s clean-up (it would not cover `/ship-fast` or a
hand-finished change).

## Consequences
Guardrails accumulate as proposals the user can accept in a later change.
Automated runs never change code or process files on their own.
