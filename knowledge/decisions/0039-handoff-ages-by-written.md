# ADR 0039: A handoff ages by its Written date, not by the session-end refresh

- **Status:** accepted
- **Date:** 2026-10-30

## Context
The SessionEnd snapshot refreshed a handoff's State section and also rewrote
its `**Written:**` line. The inject hook ages a handoff by that line (seven
days), so every session that ended on a branch made its hand-written Task look
new. On `main`, a month-old task for a feature that had since moved repos would
have been injected as the previous session's handoff.

## Decision
The snapshot leaves `**Written:**` alone and keeps its own
`- **State refreshed:** <time> by session-end snapshot` line, right after
Written. The inject hook still ages by Written, so a handoff expires seven
days after its body was written by `/handoff` (or created by the snapshot).
Rejected: skipping the snapshot on the default branch, which leaves feature
branches with the same revival.

## Consequences
An old handoff no longer comes back after any session on its branch. A
handoff that is still current but older than seven days stops being injected
until `/handoff` rewrites it; that is the intended prompt to refresh it.
