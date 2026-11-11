# /ship: steps 8 to 12

Part of `commands/ship.md`, which reads this file when it reaches it. That command's Stop rules and Git lock retry apply here.

8. **Green CI.** `gh pr checks --watch --fail-fast`. On red, repeat the step-5 fix
   loop.
9. **Merge.** `gh pr view --json mergeStateStatus`. If `BEHIND` or `DIRTY`:
   `git fetch origin && git rebase origin/main`, resolve every conflict (a
   conflict in `docs/superpowers/README.md` is resolved by running
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py" docs/superpowers`, with
   the fallback `~/.claude/skills/claude-kit/scripts/spec-index.py`, then
   `git add docs/superpowers/README.md`, never by hand; a conflict in a
   file from the `Capture learnings` commit keeps one copy of each
   duplicate entry, and an ADR whose number `origin/main` already uses is
   renumbered to the next free one, with its file name and index row;
   other files as before), then `git rebase --continue`, re-run
   tests, `git push --force-with-lease`, return to step 8. Then
   `gh pr merge --squash --delete-branch`. Run from a worktree this exits
   non-zero *after* merging, because it cannot check out `main` here; confirm
   with `gh pr view --json state,mergeCommit` — `MERGED` means continue, and
   step 11 finishes the local cleanup. Anything else is a stop rule.
10. **Verify main.** Never test in the main checkout (the first entry of
    `git worktree list`). `git fetch origin`, then
    `git worktree add --detach <tmp> <squash-commit>` with `<tmp>` a new
    directory outside the repo. In `<tmp>`: run the full test suite and lint,
    then watch the `main` run for the squash commit:
    `gh run list --commit <squash-commit> --json databaseId` (retry every 15 s
    until it appears) → `gh run watch <id> --exit-status`. Then
    `git worktree remove --force <tmp>`.
11. **Cleanup.** Inline (do not show the
    `superpowers:finishing-a-development-branch` menu). First move the session
    out of the feature worktree (`ExitWorktree` with `keep` if the session
    entered it with `EnterWorktree`, otherwise change directory): Windows cannot
    remove a directory in use, and a worktree-isolated session may not run git
    against the main checkout. If the task used Docker, clean it up next, while
    the worktree (and any compose file in it) still exists: stop and remove the
    containers labelled `claude-kit.task=<slug>` (`docker compose -p <slug> down
    --volumes --rmi local` for a stack); remove the images, volumes and networks
    the task created or pulled that are not in the step-4 baseline; and
    `docker buildx rm <slug>`. Never run a prune without a
    `label=claude-kit.task=<slug>` filter, and never remove anything in the
    baseline. If the task used Docker, then run
    `python "${CLAUDE_PLUGIN_ROOT}/scripts/docker-disk.py"` (fallback
    `~/.claude/skills/claude-kit/scripts/docker-disk.py`) and keep its
    `docker disk:` line for the report; it changes nothing and never prompts,
    and its verdict is not a stop rule. Run every git command as
    `git -C <main-checkout> ...`; none of them changes that checkout's files or
    branch: `worktree remove <worktree-path>`, `worktree prune`,
    `branch -D feat/<slug>`, `push origin --delete feat/<slug>` (the merge's
    `--delete-branch` aborts before the remote step when run from a worktree),
    `fetch --prune`. Delete `.claude/handoffs/feat_<slug>.md` (`handoff.py` writes `/`
    as `_`) if present, and
    delete any scratch files you created outside the repo. Then bring local `main`
    up only when that is safe: if `git -C <main-checkout> branch --show-current`
    is `main` and `git -C <main-checkout> status --porcelain` is empty (a clean
    tree), run `git -C <main-checkout> merge --ff-only origin/main`. If either
    check fails, or the fast-forward refuses (local `main` has its own commits),
    leave local `main` as it is and say so in the report; this is not a stop
    rule. Check: `git worktree list` shows neither the feature worktree nor
    `<tmp>`, and `git ls-remote --heads origin` and `git branch -a` have no
    `feat/<slug>`; if the task used Docker,
    `docker ps -a --filter label=claude-kit.task=<slug> -q` is empty and
    `docker buildx ls` has no `<slug>`.
12. **Report.** One message: the PR link, the squash commit on `main`, the
    verification output from step 10, whether local `main` was fast-forwarded
    (and why not, if not), the review findings you fixed (from whichever
    review ran in step 4 or step 6), the
    `Plan decisions (auto-approved)` (or `Plan decisions`) list from step 7, if
    any, the Learnings summary from step 7, the `docker disk:` line from
    step 11 if the task used Docker, and anything left out and why
    (including SDD's rulings and any findings it parked or deferred).
