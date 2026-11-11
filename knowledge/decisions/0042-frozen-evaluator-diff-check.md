# ADR 0042: Frozen evaluator as a diff check and a stop rule

- **Status:** accepted
- **Date:** 2026-11-10

## Context
Acceptance tests, eval harnesses and fixtures decide whether a change is done.
An implementer that edits them to make them pass defeats the spec. Nothing
stopped that: the approved spec could not name files as off limits.

## Decision
A spec or plan may carry a `- **Frozen:**` bullet of backticked paths or globs.
`plugin/scripts/frozen-check.py` compares them with the snapshot taken when the
spec and plan were approved and reports any changed file before every push in
`/ship` and `/ship-fast`; a changed frozen file stops the run. A frozen file
that does not exist yet is created once, exactly as the plan gives it. A
needed change goes back to the user as a spec decision. Only the main session
writes the `Frozen-change-approved: <path>` trailer, after the user approves;
implementers and subagents never do.
Rejected: a PreToolUse hook (ADR 0007 makes hooks exit 0, so a hook cannot
block an edit); letting an implementer edit the Frozen bullet to unfreeze a
file (that changes the spec and re-gates the spec and the plan).

## Consequences
Enforcement happens at push time, not at edit time, so a violating edit is
caught late but never reaches the remote. Specs that freeze nothing pay
nothing: the script prints `frozen: none declared`.
