---
description: Use after a spec is approved to land it on main without further check-ins — plan, implement, CI, review, PR, green CI, squash-merge, verify main, clean up
argument-hint: [path-to-spec.md]
disable-model-invocation: true
---

Ship the approved spec at `$ARGUMENTS` (if empty: the newest `*.md` under
`docs/superpowers/specs/`; name it in one line and continue).

Invoking `/ship` is the user's approval for everything below, including the merge:
the human-approval gate in `conventions/engineering-practices.md` is waived for this
change. Do not ask for confirmation at any step. The Stop rules below override
every ask, menu, option list, or checkpoint inside the skills this command
invokes: where a skill says "ask" or "wait for the answer", take the path this
command names and continue. Report once, at the end.

## Stop rules

These are the only reasons to stop. When one fires: write the handoff with the
`claude-kit:handoff` skill, state the blocker and what you tried, and end your turn.

- CI is red after 3 fix attempts on this branch (attempts are counted across
  steps 5 and 8 together).
- A review finding needs a scope, product, or behaviour decision the spec does not
  settle. (Bugs, missing tests, style, naming: fix them yourself.)
- `gh pr merge` refuses to merge (branch protection, required reviews, failed
  required checks). An error printed *after* the PR is merged is not a refusal;
  step 9 says how to tell them apart.
- `git fetch origin` fails in step 1.

## Steps

1. **Pre-flight.** If you are already in a worktree on a feature branch created
   for this spec, do only step 2's spec hand-off, then go to step 3 (the
   worktree and baseline test run are skipped). Otherwise: `git fetch origin`.
   Do not check local `main` or stop for its state: it may be dirty, ahead,
   behind or in use by another session, and no step builds, tests or commits in
   it.
2. **Worktree.** Use `superpowers:using-git-worktrees`. Branch `feat/<slug>` from
   `origin/main`, not local `main` (the git fallback is
   `git worktree add <path> -b feat/<slug> origin/main`). If the spec is not on
   `origin/main` (it is usually an untracked file in the main checkout), copy it
   to the same path in the worktree and commit it there. Then, only if the main
   checkout's copy is untracked and identical to the committed one
   (`git diff --no-index --quiet`), delete it from the main checkout, so the
   merge can later reach local `main` without an "untracked file would be
   overwritten" error; otherwise leave it and mention it in the report. Run the
   full test suite from the repo's `CLAUDE.md` and confirm it is green before
   changing anything.
3. **Plan.** Use `superpowers:writing-plans` to write
   `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md` from the spec. Commit it. Do
   not offer an execution choice; continue.
4. **Implement.** Use `superpowers:executing-plans` with
   `superpowers:test-driven-development`, in this session. The plan's review
   checkpoints are progress notes, not pauses. A failing test or an unclear
   instruction is debugged with `superpowers:systematic-debugging`, not
   escalated. Before every commit run the full test suite and lint from
   `CLAUDE.md`; commit per task.
5. **CI.** `git push -u origin feat/<slug>`. Find the run for the pushed commit:
   `gh run list --commit $(git rev-parse HEAD) --json databaseId,status,conclusion`
   (retry every 15 s until it appears), then `gh run watch <id> --exit-status`.
   On red: `gh run view <id> --log-failed`, use `superpowers:systematic-debugging`,
   fix, commit, push, count one attempt.
6. **Review.** Use `superpowers:requesting-code-review` on `origin/main..HEAD`,
   then `superpowers:receiving-code-review`. Fix every finding you can verify;
   commit, re-run tests, push. A finding that needs a decision is a stop rule.
7. **PR.** `gh pr create --title "<spec title>" --body-file <file>` where the body
   has: Summary, links to the spec and plan, Verification (the exact commands and
   their results), and the attribution line the session requires.
8. **Green CI.** `gh pr checks --watch --fail-fast`. On red, repeat the step-5 fix
   loop.
9. **Merge.** `gh pr view --json mergeStateStatus`. If `BEHIND` or `DIRTY`:
   `git fetch origin && git rebase origin/main`, resolve every conflict, re-run
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
    against the main checkout. Run every git command as
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
    `feat/<slug>`.
12. **Report.** One message: the PR link, the squash commit on `main`, the
    verification output from step 10, whether local `main` was fast-forwarded
    (and why not, if not), the review findings you fixed, and anything left out
    and why.
