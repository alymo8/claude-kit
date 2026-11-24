# ADR 0053: Prune learnings at ship

- **Status:** accepted
- **Date:** 2026-11-23

## Context

`agent-kit:capture-learnings` only adds. Entries in `CLAUDE.md`, `knowledge/`
and auto-memory go stale: paths move, commands change, gotchas get fixed and
"pending" items get done. Later sessions still trust them. The idea of letting
learnings decay came from an external setup's confidence-scored instincts; only
its ideas were taken.

## Decision

- **D1, prune at ship.** capture-learnings gains a Prune step that fixes or
  removes the entries the feature's own diff made wrong, limited to what that
  diff changed. Per-entry confidence or "last confirmed" stamps were rejected:
  they cost tokens every session and decay useful notes. A sweep-only approach
  was rejected because it runs only when someone audits. For the time between
  ships, the audits add a staleness check for `knowledge/` docs.
- **D2, auto-memory is in scope.** A ship step may edit the user's auto-memory,
  because project memories collect the most stale pending items.
- **D3, narrow memory deletion.** A memory is deleted only when nothing in it
  stays true. Feedback and user memories are never edited or deleted. Every
  memory edit is reported in the run's summary.
- **D4, ADRs are never edited.** A contradiction with an ADR is reported as
  `not written: ADR <NNNN> may be superseded` instead.
- **D5, audits never read auto-memory.** Their reports are repo files, and
  memory contents must not land in a repo.

## Consequences

- Prune edits are learnings, not hardening, so ADR 0043's rule that automated
  runs never change code or process files on their own still holds.
- There is no approval pause: the PR diff reviews the repo edits and the
  summary reviews the memory edits.
- Memory edits are uncommitted and cannot be undone, which is why deletion is
  narrow.
- After merge, the `pruned:` and `memory:` lines of the next three `/ship` runs
  are checked by hand; one wrong removal means revisiting D3 or narrowing
  Prune.
