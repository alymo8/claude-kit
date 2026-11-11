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
- The plan gate in step 3 returns `fail`; or it returns `pass-with-decisions`
  (or a resumed run finds the plan record at `decisions not approved`) and at
  least one plan-introduced decision is irreversible (step 3 defines it).
  Report the record's Plan-introduced decisions and Open items as questions
  (if the gate stopped at `P4-spec-gated` and wrote no record, report that
  reason and that the spec must pass `claude-kit:spec-gate`). Besides a
  `fail`'s Open items, only irreversible plan-introduced decisions need the
  user. A record with a `Stopped on irreversible` line stops again on every
  resumed run until the user answers: rerunning `/ship` is not an answer.
  When the user answers: on approval, do (3c) and (3d), add
  `- **Decisions approved:** <today>` to the record and set the plan's Status
  to `approved`; otherwise update the plan (or the spec, which is gated again)
  and rerun the plan gate through step 3's subagent dispatch. Commit, and
  continue `/ship` from step 4.
- The PR title does not match the spec's title after one fix in step 7.
- `frozen-check.py` exits 1 (see Frozen check). Report each changed path. The
  user answers by approving the change or by revising the spec. On approval,
  and only then, the main session runs `git commit --allow-empty` after the
  change commit, with one `Frozen-change-approved: <path>` trailer line per
  approved path, and continues from the push it stopped before. Implementers
  and subagents never write that trailer.

## Git lock retry

Any git command in this repository, in the main checkout or any worktree,
that fails with `Unable to create '...lock': File exists` or
`cannot lock ref` is retried after 5 seconds, up to 5 times. All worktrees
share one `.git` directory, so concurrent worktrees can collide on its locks.
A command still failing after that is handled like any other failed command.

## Frozen check

Before every `git push` in steps 5 to 9 (step 7's push, step 8's fix loop and
step 9's rebase included), run
`python "${CLAUDE_PLUGIN_ROOT}/scripts/frozen-check.py" <spec> <plan>`
(fallback if the variable is not expanded:
`~/.claude/skills/claude-kit/scripts/frozen-check.py`) in the feature
worktree. Exit 0: push. Exit 1: the frozen stop rule. Exit 2 (bad usage,
unreadable file, git failure): debug it with
`superpowers:systematic-debugging` and rerun before pushing; it is not a stop
rule.

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
   if the record has a `Stopped on irreversible` line, the plan-gate stop
   rule fires; otherwise handle the record as for `pass-with-decisions`
   below, from (3a). On any other reason, run the plan gate (below) on the
   existing plan.
   Whenever step 3 would write a plan or run the plan gate (no plan exists,
   or `--verify-record` on the existing plan prints neither `ok:` nor
   `decisions not approved`), `/ship` does neither itself: it dispatches one
   **new** general-purpose subagent on the session's own model (no `model`
   override), with no conversation, summary or other context, and only this
   prompt (absolute paths):

   > In the git worktree at `<feature worktree root>`, the approved spec is
   > `<spec>` and its gate record is `<spec gate record>`. Existing plan:
   > `<plan>` (or `none`).
   >
   > If the existing plan is `none`, write the implementation plan for the
   > spec using the `superpowers:writing-plans` skill, saved as
   > `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md`. Where the spec leaves a
   > choice open, prefer one the spec, its ADRs or the existing code already
   > imply. Answer every question under `## Plan questions` in the spec gate
   > record in the task it affects (none if the section is missing). Copy the
   > spec's `**Frozen:**` bullet into the plan header, adding any test or eval
   > file whose full content the plan writes and that a success criterion
   > depends on. Add a
   > `**Depends on:**` line under each task's `**Files:**` block: `none`, or
   > the earlier tasks whose results it uses (`Task 1, Task 3`); a task whose
   > only link to earlier tasks is shared files gets `none`. Do not write a
   > new plan over an existing one; the plan gate's own fixes to it are
   > expected.
   >
   > Then run the `claude-kit:plan-gate` skill on the plan, steps 1–6 only (do
   > not run step 7 and do not ask anything). Do not commit and do not offer
   > an execution choice. Return exactly three lines: `Plan: <repo-relative
   > path>`, `Verdict: pass | pass-with-decisions | fail`, and `Record:
   > <repo-relative path of the plan gate record>` (`Record: none` when the
   > gate stopped at `P4-spec-gated` and wrote no record).

   In that prompt, `<feature worktree root>` is the absolute path of the
   feature worktree from step 2 (never the main checkout); `<spec>`,
   `<spec gate record>` (`docs/superpowers/gates/<spec file name>`) and
   `<plan>` are absolute paths inside it.
   Check the result: in that worktree, the plan file exists, its `**Spec:**`
   line names the spec, and the reported verdict matches the record's
   `Verdict` line (for `Record: none`: the plan exists and no record was
   written). Before the first dispatch with an existing plan, copy that plan
   and its record (if any) to the scratchpad. On a failed check, delete any
   plan file and record the subagent created, restore an existing plan it was
   given and that plan's existing record from those copies, and dispatch it
   once more with the same prompt; a second failure is debugged with
   `superpowers:systematic-debugging`, not a stop rule.
   **Plan gate:** from here `/ship` acts on the reported verdict, reading the
   Plan-introduced decisions and Open items from the record file, and makes
   every commit itself. On `pass`, set the
   plan's Status to `approved`, commit the plan and its record
   (`docs/superpowers/gates/plans/<plan file name>`), and continue.
   On `fail`, commit the plan and its record (the plan only, if the gate
   stopped at `P4-spec-gated`), then the plan-gate stop rule fires. On
   `pass-with-decisions`:
   (3a) Read the record's `## Plan-introduced decisions`. A decision is
   **irreversible** when carrying it out would delete, overwrite or migrate
   data not regenerable from the repo (user files, databases, remote state),
   rewrite published git history, or change something outside the
   repository that reverting the PR cannot undo (an external service, a
   published package, another repo); when unsure, treat it as irreversible.
   If any decision is irreversible, add
   `- **Stopped on irreversible:** <today>` below the record's `Verdict`
   line (it changes no hash), commit the plan and its record if they
   changed, then the plan-gate stop rule fires.
   (3b) Otherwise add, below the record's `Verdict` line,
   `- **Decisions approved:** <today>` and then
   `- **Approved by:** /ship (auto)`, and set the plan's Status to
   `approved` (neither changes a hash).
   (3c) For each approved decision that hits a MUST trigger of the
   decision-log playbook (the trigger list in the repo's decisions README,
   else the decision-log playbook path from the kit map, ADRs 0027 and
   0032), write its ADR file and its decisions README row now. Do not edit the plan: any plan
   edit changes its hash and makes the record stale. A repo with no ADR
   folder and no trigger list skips this.
   (3d) Write a `Ruling:` ledger line naming the record and the number of
   decisions approved.
   (3e) Commit the plan, its record and any ADRs from (3c), and continue to
   step 4.
4. **Implement.** Before implementing, `spec-lint.py --verify-record <plan>`
   on the plan from step 3 must print `ok:`; otherwise return to step 3. Then
   run `python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" waves <plan>`
   (fallback if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/parallel-plan.py`). If the script
   exits non-zero, write a `Ruling:` ledger line with its messages, then
   implement with `superpowers:subagent-driven-development` on the plan;
   this is not a stop rule, because the plan is still executable one task at
   a time. Else, if every wave has one task, use
   `superpowers:subagent-driven-development`. Otherwise use
   `claude-kit:parallel-tasks` with `<plan>` as its argument (under `/ship`
   its inline paths use SDD's task loop). `/ship`'s override applies to SDD
   as to every skill: no question, menu or checkpoint inside it pauses the
   run; an SDD stop reason that is not a `/ship` stop rule is settled with a
   `Ruling:` ledger line; a ruling on an irreversible, destructive or
   security-sensitive action never carries the action out unless the spec
   requires it: it declines the action and records why. A task-review or
   final-review finding that needs a scope, product or behaviour decision
   the spec does not settle is never settled by a ruling: it is a stop rule,
   as in step 6. SDD's closing
   `superpowers:finishing-a-development-branch` is not run: step 11 does the
   clean-up. After each task SDD marks complete, the main session runs the
   full test suite and lint from `CLAUDE.md` with quiet output and confirms
   the task's commit is on the branch; a red suite is debugged and fixed in
   the main session with `superpowers:systematic-debugging` (not by resuming
   the implementer) before the next task. Pass each implementer and task
   reviewer this global constraint, with <list> the plan's `**Frozen:**`
   paths (skip it when the plan has none): "Files under Frozen (`<list>`)
   that exist are read-only. One that does not exist yet is created once,
   exactly as the plan gives it, and never changed after that commit. Report
   any other needed change as a blocker." The plan's review
   checkpoints are progress notes, not pauses. A failing test or an unclear
   instruction is debugged with `superpowers:systematic-debugging`, not
   escalated. Before every commit run the full test suite and lint from
   `CLAUDE.md`; commit per task. Before the first Docker command, record the
   baseline (`docker ps -aq`, `docker images -q`, `docker volume ls -q`,
   `docker network ls -q`) in a scratch file outside the repo; then label every
   object the task creates `claude-kit.task=<slug>` (compose: `-p <slug>`) and
   build with `docker buildx create --name <slug>`.
5. **CI.** Run the frozen check, then `git push -u origin feat/<slug>`. Find
   the run for the pushed commit:
   `gh run list --commit $(git rev-parse HEAD) --json databaseId,status,conclusion`
   (retry every 15 s until it appears), then `gh run watch <id> --exit-status`.
   On red: `gh run view <id> --log-failed`, use `superpowers:systematic-debugging`,
   fix, commit, run the frozen check, push, count one attempt.
6. **Review.** If this session did not receive, during step 4 of this run,
   the report of the final whole-branch review that step 4's skill runs
   (SDD's final review or `parallel-tasks`' final review), for example on a
   run resumed in another session, first use
   `superpowers:requesting-code-review` on `origin/main..HEAD`, then
   `superpowers:receiving-code-review`, and fix every finding you can verify.
   Then, on every run, run the `claude-kit:review` skill with base
   `origin/main`, the spec and the plan. Fix every `hard` standards finding
   and every spec finding of kind (a) or (c) you can verify; remove scope
   creep (b) unless removing it breaks a requirement. Fix a `judgement`
   finding when the fix is small and clearly better; keep the rest for the PR
   body and the report. Commit, re-run the full test suite and lint, run the
   frozen check, push. A finding from any of these reviews that needs a
   scope, product or behaviour decision the spec does not settle is a stop
   rule.
7. **PR.** First run the `claude-kit:capture-learnings` skill with the
   argument `--auto`. If it made a commit, run the full test suite and lint
   from `CLAUDE.md`, then run the frozen check and `git push`. The PR title
   is the spec's **title**: the first line outside code fences that starts
   with `# `, with the `# ` prefix and trailing whitespace
   removed (backticks and punctuation kept). Run, with the Bash tool (not
   PowerShell, whose native-argument quoting drops `"` and mangles non-ASCII),
   `gh pr create --title '<title>' --body-file <file>`, with the title written
   out literally inside single quotes and each `'` in it written as `'\''`.
   Single quotes keep backticks and `$` literal, and a literal command passes
   worktree-isolation guards, which refuse command substitution. Write the
   body by `${CLAUDE_PLUGIN_ROOT}/references/pr-body.md` (fallback if the
   variable is not expanded: `~/.claude/skills/claude-kit/references/pr-body.md`):
   its shared parts and its `/ship` list.
   Then compare `gh pr view --json title` with the title; on a mismatch run
   `gh pr edit --title '<title>'` (same quoting) once and compare again. A
   title that still differs is a stop rule.
**Steps 8 to 12** (Green CI, Merge, Verify main, Cleanup, Report): once step 7
is done, read `${CLAUDE_PLUGIN_ROOT}/references/ship-finish.md` (fallback if the variable is not expanded: `~/.claude/skills/claude-kit/references/ship-finish.md`) and follow it.
