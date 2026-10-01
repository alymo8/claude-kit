---
name: parallel-tasks
description: Use when /ship (or you) implements a plan whose waves, from parallel-plan.py, hold more than one task. Runs each wave's tasks as concurrent subagents, one git worktree per task, then merges them back in task order with --no-ff and runs the full suite after each wave.
argument-hint: [path-to-plan.md]
---

# Parallel tasks

Runs one plan's tasks by waves from inside a `/ship` feature worktree. Tasks
in a wave share no files and do not depend on each other, so they can be
built at the same time.

## Setup

- **Plan:** `$ARGUMENTS`, the plan `/ship` is implementing.
- **Script:** `python <this skill's directory>/../../scripts/parallel-plan.py`.
- `<branch-slug>` is the feature branch name with `/` replaced by `_`;
  `<tmp>` is the OS temp directory; `<plan>` is the plan's repo-relative
  path (the plan is committed in `/ship` step 3, so every task worktree has
  the same copy).
- Every git command here follows `/ship`'s git lock retry rule: a command
  that fails with `Unable to create '...lock': File exists` or
  `cannot lock ref` is retried after 5 seconds, up to 5 times.

## Steps

1. **Setup.** Do `superpowers:executing-plans`' setup once: its ledger
   workspace, reading the plan and spec, and its pre-flight scan.
2. **Waves.** Run the script: `parallel-plan.py waves <plan>`. If it exits
   non-zero, write a `Ruling:` ledger line with its messages and implement
   the remaining tasks one at a time with `superpowers:executing-plans`.
3. **Each wave, in order**, skipping every task that already has a
   `Task N: complete` ledger line (a resumed run picks up where it stopped):
   - **One task:** implement it in the feature worktree exactly as
     `executing-plans` does (TDD, its commit, its `complete` ledger line).
   - **Several tasks:** for each task N:
     - **Leftovers first.** If a `<feature-branch>-task-N` branch exists from
       an interrupted run, it counts as merged only when its tip appears as
       the second parent of a merge commit on the feature branch: look for
       `git rev-parse <feature-branch>-task-N` in the second column of
       `git log --merges --format=%P <feature-branch>`. A branch that never
       got a commit sits at an ancestor of HEAD and does not count. If it
       counts, write its missing `complete` ledger line and skip the task.
       Otherwise delete the branch (`git branch -D`). Either way, if the task
       is not skipped, run `git worktree prune` and remove any worktree or
       leftover directory at the task's path (`git worktree remove --force`),
       whether or not its branch still exists.
     - Create its worktree:
       `git worktree add <tmp>/claude-tasks/<branch-slug>/task-N -b <feature-branch>-task-N HEAD`.

     Then dispatch one new general-purpose subagent per task, all in the
     background, each given only this prompt:

     > Implement Task N of the plan at `<plan>` in the git worktree at
     > `<task worktree>`, exactly as written, test-first. Read the plan's
     > header and Global Constraints first. Run the full test suite and lint
     > that the plan names (else the repo's `CLAUDE.md`) in that worktree,
     > and commit there with the task's commit message. Any git command that
     > fails with `Unable to create '...lock': File exists` or
     > `cannot lock ref` is retried after 5 seconds, up to 5 times. Do not
     > push, merge, or touch any other worktree. Report the commit SHAs and
     > the test result.

     When every subagent has reported, merge, in task-number order with
     `git merge --no-ff --no-edit <feature-branch>-task-N`, only the task
     branches whose subagent reported a passing suite and for which
     `git rev-list --count HEAD..<feature-branch>-task-N` is at least 1.
     Right after each merge, append
     `Task N: complete (merged <task branch> at <merge sha7>, tests: <reported result>)`
     to the ledger. A merge conflict means a `**Files:**` list was
     incomplete: resolve it keeping both changes and write a `Ruling:` ledger
     line. A failed task's branch is not merged; after the merges, implement
     that task inline in the feature worktree from the merged HEAD, and write
     its `complete` line after its commit.
   - **After the wave:** run the full test suite and lint. Red is debugged
     with `superpowers:systematic-debugging`, fixed and committed. Then
     remove the wave's task worktrees (`git worktree remove --force`) and
     branches (`git branch -D`).
4. **Final review.** Remove `<tmp>/claude-tasks/<branch-slug>/` if it is
   empty, then do `executing-plans`' final whole-branch review and fix pass.
