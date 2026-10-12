# ADR 0031: Capture learnings when a feature finishes, in its PR

- **Status:** accepted
- **Date:** 2026-10-12

## Context
Sessions learn things later sessions rediscover or get wrong: gotchas,
commands that work, conventions, the user's corrections. `/handoff` moves
findings and decisions at a session's end, but no flow recorded operational
learnings when a feature finished. A `SessionEnd` hook cannot run the model,
and a headless `claude -p` over every transcript costs tokens each session
and writes files nobody reviews.

## Decision
- Learnings are captured when a feature or change finishes, by the
  `capture-learnings` skill: `/ship` and `/ship-fast` run it at the start of
  their PR step; the workspace rule runs it before a manual finish merges.
- It commits on the feature branch, so the learnings land in the feature's
  PR and are reviewable in its diff. No approval pause; the flow's report
  lists them.
- One flow-invoked skill instead of text copied into each command, because
  commands run in other repos and can reach only `plugin/`.
- Each learning goes to an existing home by kind: the repo's `CLAUDE.md`
  (or `knowledge/` once it would pass 100 lines), `knowledge/`, an ADR, or
  auto-memory for preferences. No separate learnings file.
- `/handoff` and `/ship-many` are unchanged; no back-filling of past work.

## Consequences
- In this repo, whose `CLAUDE.md` is already over 100 lines, repo learnings
  go to `knowledge/`.
- `/ship-fast` POC branches and repos without `knowledge/decisions/` get no
  ADRs; decisions are listed in the report instead.
- The learnings commit lands after the step-6 review; `/ship` runs the
  tests and lint on it before pushing, and the PR diff shows it.
