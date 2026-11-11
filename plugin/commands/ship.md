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

Where `${CLAUDE_PLUGIN_ROOT}` is not expanded, use `~/.claude/skills/claude-kit` in its place.

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
- The plan gate in step 3 returns `fail`, or a record at `pass-with-decisions`
  or `decisions not approved` holds an irreversible plan-introduced decision
  (step 3a). Report the record's Plan-introduced decisions and Open items as
  questions (if the gate stopped at `P4-spec-gated` with no record: that
  reason, and that the spec must pass `claude-kit:spec-gate`). Besides a
  `fail`'s Open items, only irreversible plan-introduced decisions need the
  user. A record with a `Stopped on irreversible` line stops again on every
  resumed run: rerunning `/ship` is not an answer. When the user answers:
  on approval, do (3c) and (3d), add `- **Decisions approved:** <today>` to
  the record and set the plan's Status to `approved`; otherwise update the
  plan (or the spec, which is gated again) and rerun the plan gate through
  step 3's subagent dispatch. Commit, and continue from step 4.
- The PR title does not match the spec's title after one fix in step 7.

## Git lock retry

A git command (any checkout or worktree of this repository) that fails with
`Unable to create '...lock': File exists` or `cannot lock ref` is retried
after 5 seconds, up to 5 times; then it is handled like any failed command.

## Steps

0. **Gate.** Run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-lint.py" --verify-record <spec>`.
   If it prints `ok:`, set the spec's Status to `approved` if it is not
   already, and continue. Otherwise run the `claude-kit:spec-gate` skill on
   the spec, steps 1–6 (skip step 7's question: invoking `/ship` is the
   approval), then set the Status to `approved`; a fail verdict is a stop
   rule.
1. **Pre-flight.** If you are already in a worktree on a feature branch created
   for this spec, do only step 2's spec hand-off, then go to step 3.
   Otherwise: `git fetch origin`.
   Do not check local `main` or stop for its state: no step builds, tests or
   commits in it.
2. **Worktree.** Use `superpowers:using-git-worktrees`. Branch `feat/<slug>` from
   `origin/main`, not local `main` (the git fallback is
   `git worktree add <path> -b feat/<slug> origin/main`). If the spec or its
   gate record (`docs/superpowers/gates/<spec file name>`) is missing from
   `origin/main` or differs from it, copy each to the same path in the
   worktree and commit them there. Then delete each from the main checkout
   only if its copy there is untracked and identical to the committed one
   (`git diff --no-index --quiet`), so the merge can later reach local
   `main`; otherwise leave it and mention it in the report. Run the full test
   suite from the repo's `CLAUDE.md` and confirm it is green before changing
   anything.
3. **Plan.** First look for an existing plan: a `*.md` under
   `docs/superpowers/plans/` on this branch whose `**Spec:**` line names this
   spec (the newest by file name if several match). If there is one, run
   `spec-lint.py --verify-record <plan>`. On `ok:`, go to step 4. On
   `decisions not approved`, do not rerun the gate: if the record has a
   `Stopped on irreversible` line, the plan-gate stop rule fires; otherwise
   continue from (3a) below. On any other reason, or with no plan, `/ship`
   neither writes the plan nor runs the gate itself: it dispatches one
   **new** general-purpose subagent on the session's own model (no `model`
   override), with no conversation, summary or other context, and only this
   prompt:

   > In the git worktree at `<feature worktree root>`, the approved spec is
   > `<spec>` and its gate record is `<spec gate record>`. Existing plan:
   > `<plan>` (or `none`).
   >
   > If the existing plan is `none`, write the implementation plan for the
   > spec using the `superpowers:writing-plans` skill, saved as
   > `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md`. Where the spec leaves a
   > choice open, prefer one the spec, its ADRs or the existing code already
   > imply. Answer every question under `## Plan questions` in the spec gate
   > record in the task it affects (none if the section is missing). Add a
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

   All placeholders are absolute paths inside the feature worktree from
   step 2 (never the main checkout); `<spec gate record>` is
   `docs/superpowers/gates/<spec file name>`.
   Check the result: the plan file exists in that worktree, its `**Spec:**`
   line names the spec, and the reported verdict matches the record's
   `Verdict` line (for `Record: none`: no record was written). Before the
   first dispatch with an existing plan, copy it and its record (if any) to
   the scratchpad. On a failed check, delete what the subagent created,
   restore those copies, and dispatch once more with the same prompt; a
   second failure is debugged with `superpowers:systematic-debugging`, not a
   stop rule.
   **Plan gate:** `/ship` acts on the reported verdict, reading the
   Plan-introduced decisions and Open items from the record file, and makes
   every commit itself. On `pass`, set the plan's Status to `approved`,
   commit the plan and its record
   (`docs/superpowers/gates/plans/<plan file name>`), and continue. On
   `fail`, commit the plan and its record (the plan only, if the gate
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
   else the decision-log playbook path from the kit map), write its ADR file and its decisions README row now. Do not edit
   the plan: any plan edit changes its hash and makes the record stale. A
   repo with no ADR folder and no trigger list skips this.
   (3d) Write a `Ruling:` ledger line naming the record and the number of
   decisions approved.
   (3e) Commit the plan, its record and any ADRs from (3c), and continue to
   step 4.
4. **Implement.** `spec-lint.py --verify-record <plan>` on the plan from
   step 3 must print `ok:`; otherwise return to step 3. Then run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" waves <plan>`.
   If it exits non-zero, write a `Ruling:` ledger line with its messages and
   implement with `superpowers:subagent-driven-development` (SDD); this is
   not a stop rule, because the plan still runs one task at a time. If every
   wave has one task, use SDD too. Otherwise use `claude-kit:parallel-tasks`
   with `<plan>` as its argument (under `/ship` its inline paths use SDD's
   task loop). An SDD stop reason that is not a `/ship` stop rule is settled
   with a `Ruling:` ledger line; a ruling on an irreversible, destructive or
   security-sensitive action declines the action and records why, unless
   the spec requires it. A task-review or final-review finding that needs a
   scope, product or behaviour decision the spec does not settle is never
   settled by a ruling: it is a stop rule, as in step 6. SDD's closing
   `superpowers:finishing-a-development-branch` is not run: step 11 does the
   clean-up. The plan's review checkpoints are progress notes, not pauses.
   After each task SDD marks complete, the main session runs the full test
   suite and lint from `CLAUDE.md` with quiet output and confirms the task's
   commit is on the branch; a red suite is debugged and fixed in the main
   session with `superpowers:systematic-debugging` (not by resuming the
   implementer) before the next task. A failing test or an unclear
   instruction is debugged with `superpowers:systematic-debugging`, not
   escalated. Before every commit run the full test suite and lint; commit
   per task. Before the first
   Docker command, follow "Docker hygiene" in the engineering-practices
   playbook (kit map), with `<slug>` as the task name.
5. **CI.** `git push -u origin feat/<slug>`. Find the run for the pushed commit:
   `gh run list --commit $(git rev-parse HEAD) --json databaseId,status,conclusion`
   (retry every 15 s until it appears), then `gh run watch <id> --exit-status`.
   On red: `gh run view <id> --log-failed`, use `superpowers:systematic-debugging`,
   fix, commit, push, count one attempt.
6. **Review.** If this session received, during step 4 of this run, the
   report of that step's final whole-branch review (SDD's or
   `parallel-tasks`'), the findings it fixed are the PR's review findings:
   do not run another review. Otherwise (for example a run resumed in
   another session that never reached that review), use
   `superpowers:requesting-code-review` on `origin/main..HEAD`, then
   `superpowers:receiving-code-review`. Fix every finding you can verify;
   commit, re-run tests, push. A finding that needs a scope, product or
   behaviour decision the spec does not settle is a stop rule, whichever
   review raised it.
7. **PR.** First run the `claude-kit:capture-learnings` skill. If it made a
   commit, run the full test suite and lint from `CLAUDE.md`, then
   `git push`. The PR title is the spec's **title**: the first line outside code
   fences that starts with `# `, with the `# ` prefix and trailing whitespace
   removed (backticks and punctuation kept). Run, with the Bash tool (not
   PowerShell), `gh pr create --title '<title>' --body-file <file>`, with the
   title written out literally inside single quotes and each `'` in it
   written as `'\''` (no command substitution). The body has:
   Summary, links to the spec, the plan and the plan gate record
   (`docs/superpowers/gates/plans/<plan file name>`), a section that lists
   verbatim each entry of the plan record's `## Plan-introduced decisions`
   (omit it when that list is `none`), titled
   `Plan decisions (auto-approved)` when the record has
   `- **Approved by:** /ship (auto)` and `Plan decisions` otherwise,
   Verification (the exact commands and their results), and the attribution
   line the session requires. Then compare `gh pr view --json title` with
   the title; on a mismatch run `gh pr edit --title '<title>'` (same
   quoting) once and compare again. A title that still differs is a stop
   rule.
**Steps 8 to 12** (Green CI, Merge, Verify main, Cleanup, Report): once step 7
is done, read `${CLAUDE_PLUGIN_ROOT}/references/ship-finish.md` and follow it.
