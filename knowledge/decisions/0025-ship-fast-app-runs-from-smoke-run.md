# ADR 0025: `/ship-fast`: the app runs for the user from the smoke run

- **Status:** accepted
- **Date:** 2026-10-08

## Context
Since ADR 0023, `/ship-fast` launches the POC for the user only in step 8,
after the smoke run, the quick review and the PR's CI. The user's time is
short, and they wait through all three before they can try the app.

## Decision
- Step 5 launches the app once, from the worktree, as a background process
  (or its containers), and posts a **Try it now** line with its URL or entry
  command and how to stop it, before any smoke check.
- The smoke checks run against that same copy: there is one copy, not a
  second one for the checks. The checks use their own clearly labelled
  sample data and never edit or delete data the user created.
- Every fix commit from step 5 to step 7 (a smoke fix, the review fixes, a
  CI fix) restarts that copy on the new code, with one progress line.
- Step 8 no longer launches the app: it confirms the running copy serves
  the branch's final commit, restarting or relaunching it if needed.
- A stop after step 5 leaves the app running and gives its stop command.

## Consequences
The user tries the POC while the smoke run, review and CI proceed. In
return, a restart briefly interrupts them, in-memory data is lost on each
restart, and their data and the checks' sample data share one app. Two
copies were rejected to keep a single running app and port.
