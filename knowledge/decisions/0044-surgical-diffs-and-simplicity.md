# ADR 0044: Surgical diffs and simplicity

- **Status:** accepted
- **Date:** 2026-11-10

## Context
Changes drift: an implementer tidies neighbouring code, removes dead code it
did not create, or builds for a future need. Reviewers saw a larger diff than
the spec asked for, and the kit's rules did not say what to do about it.

## Decision
Six rules (trace every line, mention unrelated dead code, remove only your own
leftovers, nothing speculative, deleting is a win, ask during design; see
`conventions/engineering-practices.md`) become a workspace convention and part of the Definition of done, and the
standards reviewer of `claude-kit:review` checks them. "Ask when unsure"
applies to design only, so it adds no check-in to `/ship` (ADR 0018, ADR 0036).
Rejected: installing the karpathy-guidelines plugin, which duplicates most kit
rules and loads in every session.

## Consequences
The Definition of done and the PR template ask for a surgical diff. Cleanups of
unrelated code become separate changes the user chooses.
