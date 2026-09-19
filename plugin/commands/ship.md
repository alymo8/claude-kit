---
description: Use after a spec is approved to land it on main without further check-ins — plan, implement, CI, review, PR, green CI, squash-merge, verify main, clean up
argument-hint: [path-to-spec.md]
---

Ship the approved spec at `$ARGUMENTS` (if empty: the newest file under
`docs/superpowers/specs/`; name it in one line and continue).

Invoking `/ship` is the user's approval for everything below, including the merge:
the human-approval gate in `conventions/engineering-practices.md` is waived for this
change. Do not ask for confirmation at any step. Report once, at the end.

## Stop rules

These are the only reasons to stop. When one fires: run `/handoff`, state the
blocker and what you tried, and end your turn.

- CI is red after 3 fix attempts on this branch (attempts are counted across
  steps 5 and 8 together).
- A review finding needs a scope, product, or behaviour decision the spec does not
  settle. (Bugs, missing tests, style, naming: fix them yourself.)
- `gh pr merge` is refused by branch protection, or the rebase in step 9 conflicts
  in a file the plan did not touch.
- The pre-flight in step 1 fails.

## Steps

1. **Pre-flight.** `git branch --show-current` is `main`; `git fetch`;
   `git status -sb` shows `main...origin/main` with no ahead/behind and a clean
   tree. If you are already in a worktree on a feature branch created for this
   spec, skip to step 3.
2. **Worktree.** Use `superpowers:using-git-worktrees`. Branch `feat/<slug>` from
   up-to-date `main`. Run the full test suite from the repo's `CLAUDE.md` and
   confirm it is green before changing anything.
3. **Plan.** Use `superpowers:writing-plans` to write
   `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md` from the spec. Commit it.
4. **Implement.** Use `superpowers:executing-plans` with
   `superpowers:test-driven-development`. The plan's review checkpoints are
   progress notes, not pauses. Before every commit run the full test suite and
   lint from `CLAUDE.md`; commit per task.
5. **CI.** `git push -u origin feat/<slug>`. Watch the run:
   `gh run list --branch feat/<slug> --limit 1 --json databaseId,status,conclusion`
   then `gh run watch <id> --exit-status`. On red: `gh run view <id> --log-failed`,
   use `superpowers:systematic-debugging`, fix, commit, push, count one attempt.
6. **Review.** Use `superpowers:requesting-code-review` on `main..HEAD`, then
   `superpowers:receiving-code-review`. Fix every finding you can verify; commit,
   re-run tests, push. A finding that needs a decision is a stop rule.
7. **PR.** `gh pr create --title "<spec title>" --body-file <file>` where the body
   has: Summary, links to the spec and plan, Verification (the exact commands and
   their results), and the attribution line the session requires.
8. **Green CI.** `gh pr checks --watch --fail-fast`. On red, repeat the step-5 fix
   loop.
9. **Merge.** `gh pr view --json mergeStateStatus`. If `BEHIND` or `DIRTY`:
   `git fetch origin && git rebase origin/main`, resolve, re-run tests, `git push
   --force-with-lease`, return to step 8. Then
   `gh pr merge --squash --delete-branch`.
10. **Verify main.** From the main checkout: `git pull --ff-only`, run the full
    test suite and lint, and watch the `main` run:
    `gh run list --branch main --limit 1` → `gh run watch <id> --exit-status`.
11. **Cleanup.** Use `superpowers:finishing-a-development-branch`. The worktree is
    removed and pruned (`git worktree list` shows only the main checkout), the
    branch is gone locally and on the remote (`git branch -a` has no
    `feat/<slug>`), `.claude/handoffs/feat-<slug>.md` is deleted, and any scratch
    files you created outside the repo are deleted.
12. **Report.** One message: the PR link, the squash commit on `main`, the
    verification output from step 10, the review findings you fixed, and anything
    left out and why.
