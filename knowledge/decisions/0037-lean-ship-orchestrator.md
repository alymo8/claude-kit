# ADR 0037: /ship's main session coordinates; subagents write the plan and the code

- **Status:** accepted
- **Date:** 2026-10-20

## Context
A `/ship` run's tokens go mostly to its main session, whose context grows
through brainstorming, plan writing and inline implementation and is re-read
on every turn. Over 66 runs, the median run cost 18.0M cost-weighted tokens
with a 391k peak context. These figures overstate the cost, because records
that Claude Code repeats for one API message were counted more than once.

## Decision
- The spec gate's approval message sends the user to a fresh session: `/clear`,
  then `/claude-kit:ship <path>`.
- In step 3, a fresh subagent writes the plan and runs the plan gate on it,
  while `/ship` keeps acting on the verdict and making the commits.
- Step 4 always implements through `superpowers:subagent-driven-development`
  (SDD) or `claude-kit:parallel-tasks`, whose inline paths under `/ship`
  (one-task waves and inline fallbacks) use SDD's task loop.
- Step 6 reuses step 4's final review instead of requesting a new one.

## Consequences
- The main session holds the spec, the plan path, verdicts and summaries; each
  task is built in a fresh context.
- Each task run through SDD gets a per-task review, while multi-task waves keep
  `parallel-tasks`' plain subagents and its final review.
- Subagent cost rises while main-session cost falls, so runs are judged on
  total cost, measured with `token-report.py --ship`.
- This amends [ADR 0017](0017-parallel-plan-tasks.md) for inline tasks under
  `/ship`.
- `/ship-fast` is not affected.
