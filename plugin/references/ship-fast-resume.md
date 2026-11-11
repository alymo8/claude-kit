# /ship-fast: resume

Part of `commands/ship-fast.md`, which reads this file when it reaches it. That command's Stop rules and Git lock retry apply here.

A repository folder counts as this run's only if it holds
`docs/superpowers/specs/<spec file name>` (step 1 commits it there). Any
other existing folder at that path is a name collision: `scaffold.py`
refuses it, and that is a stop rule.

- With `**Repo:** new`, if this run's repository folder already exists as a
  git repository with an `origin` remote, step 1 only runs `git fetch origin`
  there.
- With `**Repo:** new`, if this run's repository folder exists as a git
  repository without an `origin` remote (a stop in step 1): skip
  `scaffold.py`, run the stack's init commands only if their output
  (`pyproject.toml` or `package.json`) is missing, commit anything
  uncommitted, then run `gh repo create` as in step 1.
- In both cases above, "the spec" is the copy at
  `docs/superpowers/specs/<spec file name>` in the repository, as after
  step 1.
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
