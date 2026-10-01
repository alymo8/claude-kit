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
- The spec gate fails in step 0. Report the gate record's Open items.
- The plan gate in step 3 returns `pass-with-decisions` or `fail`, or a
  resumed run finds the plan record at `decisions not approved`. Report the
  record's Plan-introduced decisions and Open items as questions (if the gate
  stopped at `P4-spec-gated` and wrote no record, report that reason and that
  the spec must pass `claude-kit:spec-gate`). `/ship` approves the spec, not
  decisions a plan adds later. When the user answers: on approval, add
  `- **Decisions approved:** <today>` to the record and set the plan's Status
  to `approved`; otherwise update the plan (or the spec, which is gated again)
  and rerun the plan gate. Commit, and continue `/ship` from step 4.
- The PR title does not match the spec's title after one fix in step 7.

## Git lock retry

Any git command in this repository, in the main checkout or any worktree,
that fails with `Unable to create '...lock': File exists` or
`cannot lock ref` is retried after 5 seconds, up to 5 times. All worktrees
share one `.git` directory, so concurrent worktrees can collide on its locks.
A command still failing after that is handled like any other failed command.

## Steps

0. **Gate.** Run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-lint.py" --verify-record <spec>`
   (fallback if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/spec-lint.py`). If it prints `ok:`,
   set the spec's Status to `approved` if it is not already, and continue.
   Otherwise run the `claude-kit:spec-gate` skill on the spec, steps
   1–6 (skip step 7's question: invoking `/ship` is the approval), then set the
   spec's Status to `approved`. On a pass verdict, continue; on a fail, that
   is a stop rule.
1. **Pre-flight.** If you are already in a worktree on a feature branch created
   for this spec, do only step 2's spec hand-off, then go to step 3 (the
   worktree and baseline test run are skipped). Otherwise: `git fetch origin`.
   Do not check local `main` or stop for its state: it may be dirty, ahead,
   behind or in use by another session, and no step builds, tests or commits in
   it.
2. **Worktree.** Use `superpowers:using-git-worktrees`. Branch `feat/<slug>` from
   `origin/main`, not local `main` (the git fallback is
   `git worktree add <path> -b feat/<slug> origin/main`). If the spec or its
   gate record (`docs/superpowers/gates/<spec file name>`) is missing from
   `origin/main` or differs from it (they are usually untracked files in the
   main checkout), copy each to the same path in the worktree and commit them
   there. Then, for each of the two files, only if the main checkout's copy is
   untracked and identical to the committed one
   (`git diff --no-index --quiet`), delete it from the main checkout, so the
   merge can later reach local `main` without an "untracked file would be
   overwritten" error; otherwise leave it and mention it in the report. Run the
   full test suite from the repo's `CLAUDE.md` and confirm it is green before
   changing anything.
3. **Plan.** First look for an existing plan: a `*.md` under
   `docs/superpowers/plans/` on this branch whose `**Spec:**` line names this
   spec (the newest by file name if several match). If there is one, run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-lint.py" --verify-record <plan>`.
   On `ok:`, go to step 4. On `decisions not approved`, do not rerun the gate:
   the plan-gate stop rule fires (rerunning `/ship` is never approval; only
   the user's answer is). On any other reason, run the plan gate (below) on
   the existing plan. If there is no plan, use `superpowers:writing-plans` to
   write `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md` from the spec. Where
   the spec leaves a choice open, prefer one the spec, its ADRs or the
   existing code already imply, so a routine plan passes without stopping. Do
   not offer an execution choice. Then add a `**Depends on:**` line under each
   task's `**Files:**` block: `none`, or the earlier tasks whose results it
   uses (`Task 1, Task 3`). Shared files need not be listed
   (`parallel-plan.py` orders them anyway), so a task whose only link to
   earlier tasks is shared files gets `**Depends on:** none`. **Plan gate:** run the `claude-kit:plan-gate`
   skill on the plan, steps 1–6 (step 7 is not shown). On `pass`, set the
   plan's Status to `approved`, commit the plan and its record
   (`docs/superpowers/gates/plans/<plan file name>`), and continue. On
   `pass-with-decisions` or `fail`, commit the plan and its record (the plan
   only, if the gate stopped at `P4-spec-gated`), then the plan-gate stop rule
   fires.
4. **Implement.** Before implementing, `spec-lint.py --verify-record <plan>`
   on the plan from step 3 must print `ok:`; otherwise return to step 3. Then
   run `python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" waves <plan>`
   (fallback if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/parallel-plan.py`). If the script
   exits non-zero, write a `Ruling:` ledger line with its messages and use
   `superpowers:executing-plans` with `superpowers:test-driven-development`,
   in this session: this is not a stop rule, because the plan is still
   executable one task at a time. Else, if every wave has one task, use
   `executing-plans` the same way. Otherwise use `claude-kit:parallel-tasks`
   with `<plan>` as its argument. The plan's review
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
7. **PR.** The PR title is the spec's **title**: the first line outside code
   fences that starts with `# `, with the `# ` prefix and trailing whitespace
   removed (backticks and punctuation kept). Write it to a file outside the
   repo and run `gh pr create --title "$(cat <title file>)" --body-file <file>`
   (a command substitution's output is not expanded again, so backticks and
   `$` arrive unchanged), where the body has: Summary, links to the spec, the
   plan and the plan gate record
   (`docs/superpowers/gates/plans/<plan file name>`), Verification (the exact
   commands and their results), and the attribution line the session requires.
   Then compare `gh pr view --json title` with the title; on a mismatch run
   `gh pr edit --title "$(cat <title file>)"` once and compare again. A title
   that still differs is a stop rule.
8. **Green CI.** `gh pr checks --watch --fail-fast`. On red, repeat the step-5 fix
   loop.
9. **Merge.** `gh pr view --json mergeStateStatus`. If `BEHIND` or `DIRTY`:
   `git fetch origin && git rebase origin/main`, resolve every conflict (a
   conflict in `docs/superpowers/README.md` is resolved by running
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py" docs/superpowers`, with
   the fallback `~/.claude/skills/claude-kit/scripts/spec-index.py`, then
   `git add docs/superpowers/README.md`, never by hand; other files as
   before), then `git rebase --continue`, re-run
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
