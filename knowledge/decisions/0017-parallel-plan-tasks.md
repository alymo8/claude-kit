# ADR 0017: Independent plan tasks run as concurrent subagents

- **Status:** accepted
- **Date:** 2026-10-01

## Context
`/ship` implemented a plan's tasks one after another, even when tasks touched
different files and did not use each other's results. Plans already list each
task's files (the plan gate requires it).

## Decision
A task may declare `**Depends on:** none` or `Task N, ...`; without the line
it depends on every earlier task. `parallel-plan.py waves` adds a dependency
on every earlier task that shares a file, and groups tasks into waves of at
most 3. `/ship` runs a wave with several tasks through the `parallel-tasks`
skill: one subagent per task, each in its own worktree branched from the
feature branch, merged back with `--no-ff` in task order, the full suite run
after each wave. A failed task, or a failing `waves` run, falls back to
one-at-a-time work instead of stopping `/ship`. Every git command in the repo
retries on lock errors, because worktrees share one `.git` directory.

## Consequences
Plans with independent tasks finish sooner, at the cost of one subagent per
parallel task. History shows one merge commit per parallel task. A `Files:`
list that misses a file shows up as a merge conflict, resolved by the agent
and recorded as a ruling.
