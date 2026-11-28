# /ship-fast: resume

Part of `commands/ship-fast.md`, which reads this file when it reaches it. That command's Stop rules and Git lock retry apply here.

- If you are already in a worktree on `poc/<slug>`, skip step 2. If
  `git worktree list` shows a worktree on `poc/<slug>`, enter it
  (`EnterWorktree` with its path, or change directory) and skip step 2. If
  only the branch `poc/<slug>` exists, run
  `git worktree add <path> poc/<slug>` (no `-b`) and skip the rest of
  step 2.
- If `docs/superpowers/plans/*-<slug>.md` with `**Status:** fast (ungated)`
  exists on the branch, skip step 3, and in step 4 implement only the tasks
  whose commit message (`<slug>: task N`) is not yet in
  `git log origin/main..HEAD`.
- If that task list already has a `## Decisions` section, skip step 3b.
