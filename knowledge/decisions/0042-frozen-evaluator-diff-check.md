# ADR 0042: Frozen evaluator as a diff check and a stop rule

- **Status:** accepted
- **Date:** 2026-11-10

## Context
Acceptance tests, eval harnesses and fixtures decide whether a change is done.
An implementer that edits them to make them pass defeats the spec. Nothing
stopped that: the approved spec could not name files as off limits.

## Decision
A spec or plan may carry a `- **Frozen:**` bullet of backticked paths or globs.
`plugin/scripts/frozen-check.py` compares each with its snapshot (the
merge-base, else the branch commit that created it, moved by a later approval
commit) and reports any changed file before every push in
`/ship` and `/ship-fast`; a changed frozen file stops the run. A frozen file
that does not exist yet is created once, exactly as the plan gives it. A
needed change goes back to the user as a spec decision. Only the main session
writes the `Frozen-change-approved: <path>` trailer, after the user approves;
implementers and subagents never do. The approval is a separate
`git commit --allow-empty` the main session makes after the change commit,
with one trailer line per approved path.
The check also runs before step 7's push and in step 8's fix loop of `/ship`,
not only before the pushes in steps 5, 6 and 9.
Globs use a custom matcher, not the spec's `fnmatch`: a single `*` and `?`
never cross `/`, `**/` matches zero or more whole directories, and a trailing
`**` matches anything. Of several approval trailers for one path, the last
wins.
An exit 2 (bad usage, unreadable file, git failure) under `/ship` and
`/ship-fast` is debugged with `superpowers:systematic-debugging` and rerun
before pushing; it is not a stop rule. `claude-kit:review` passes the stderr
to the standards reviewer and does not report it as a finding; with no spec
and no plan found it skips the check and reports
`Frozen: skipped (no spec or plan)`.
Rejected: a PreToolUse hook (ADR 0007 makes hooks exit 0, so a hook cannot
block an edit); letting an implementer edit the Frozen bullet to unfreeze a
file (that changes the spec and re-gates the spec and the plan).

## Consequences
Enforcement happens at push time, not at edit time, so a violating edit is
caught late but never reaches the remote. Specs that freeze nothing pay
nothing: the script prints `frozen: none declared`. Any commit may carry a
`Frozen-change-approved:` trailer, so a subagent that ignores its prompt
could unfreeze a file; the rule is an instruction, not a mechanism.
