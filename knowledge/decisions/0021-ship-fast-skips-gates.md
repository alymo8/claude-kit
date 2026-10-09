# ADR 0021: `/ship-fast` takes a POC spec to a PR with no gates

- **Status:** accepted; amended by 0022 ([ADR 0022](0022-ship-fast-user-driven-spec.md): spec interview, decisions round, inline questions) and 0024 ([ADR 0024](0024-ship-fast-user-approves-spec.md): the user reads and approves the spec)
- **Date:** 2026-10-06

## Context
`/ship` lands a change on `main` unattended, so it gates the spec and the
plan (ADR 0015, ADR 0016), runs a formal review round, watches CI on the
branch, the PR and `main`, and merges. For a proof of concept of about an
hour, that ceremony takes longer than the POC.

## Decision
- A user-only command `/ship-fast <spec.md>` takes a spec to an open pull
  request with green CI. No gate runs on the spec or its task list; the
  user reviews and merges the PR.
- It writes a short task list (1 to 5 tasks, no step-by-step code) in the
  format `parallel-plan.py` reads, so independent tasks run in parallel
  through `claude-kit:parallel-tasks` (ADR 0017).
- Quality comes from TDD on the core path, a smoke run of the app against
  the spec's acceptance criteria, one `code-review low --fix` pass kept to
  correctness fixes, and green PR CI.
- A spec header `- **Repo:** new <name> <node|python>` scaffolds a new repo
  and creates a private GitHub repo for it.
- A choice the spec does not settle that changes scope, behaviour,
  interface or data stops the run and is asked; smaller "how" choices are
  assumed and listed in the PR.

## Consequences
POCs reach a reviewable PR in far less time, at the cost of unreviewed
specs and plans; the user's PR review and merge is the only gate. Branches
are `poc/<slug>` so POC work is easy to tell from `/ship`'s `feat/`.
`/ship` is unchanged and remains the path for changes that must land
unattended.
