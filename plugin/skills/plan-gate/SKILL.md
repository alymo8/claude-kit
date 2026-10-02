---
name: plan-gate
description: Use when an implementation plan has just been written or revised, before offering an execution choice, or when /ship has written a plan. Lints the plan, runs up to 3 discovery rounds of a fresh-context reviewer subagent that checks it against its spec, then up to 2 verification rounds of its fixes, fixes what it finds, and writes a gate record under docs/superpowers/gates/plans/. The user signs off only on decisions the plan adds that the spec did not settle.
argument-hint: [path-to-plan.md]
---

# Plan gate

A plan is the only context its executor gets, and the user does not read
plans. This gate does that reading. It passes only when the linter is clean,
a reviewer that never saw the conversation finds every spec item covered and
every task executable from the plan alone, and the last fixes have been
verified. The user signs off only on decisions the plan makes that its spec
did not settle.

## Setup

- **Plan:** `$ARGUMENTS` if given, else the `*.md` under
  `docs/superpowers/plans/` whose file name sorts last. Name it in one line.
- **Spec:** the path on the plan's `**Spec:**` line.
- **Spec gate record:** `docs/superpowers/gates/<spec file name>`.
- **Linter:** `python <this skill's directory>/../../scripts/spec-lint.py`
  (fallback: `~/.claude/skills/claude-kit/scripts/spec-lint.py`).
- **Rubric:** `rubric.md` in this skill's directory (discovery rounds).
- **Verify rubric:** `../spec-gate/verify.md` from this skill's directory
  (verification rounds).
- **Scratchpad:** the session's scratchpad directory, or a temporary
  directory outside the repository. Snapshots, fixes files and diff files go
  there; `<name>` below is the plan's file name.

## Steps

1. **Lint.** If the plan has no `- **Status:**` bullet, add
   `- **Status:** draft`. Run the linter on the plan and fix every other
   violation in the plan, re-running until it exits 0. If `P4-spec-gated` is
   then the only violation left, stop with verdict `fail`: write no record,
   and report that the spec must pass `claude-kit:spec-gate` first. Never
   edit the spec from this gate.
2. **Review round.** This is a **discovery round**. Dispatch a **new**
   general-purpose subagent every round (never reuse one; a reviewer anchors
   on its own earlier findings). Give it only this prompt, with absolute
   paths:

   > Review the implementation plan at `<plan>` against its spec at `<spec>`
   > in the repository at `<repo root>`. The spec's gate record is at
   > `<spec gate record>`; its `## Plan questions` section lists questions
   > the plan must answer. Read `<rubric.md>` first and follow it exactly.
   > Return only the output format it defines.

   Do not pass it any conversation or summary.
3. **Fix.** Before applying this round's fixes, copy the plan to the
   scratchpad as `<name>.before-round-<N>.md`. For each `[blocking]` finding,
   edit the plan to fix it, unless the fix would change what the spec asks
   for: that is a **spec finding**. Do not fix it in the plan; collect it for
   the Open list. Fix `[minor]` findings too when the fix is clear. Re-run
   the linter after editing.
4. **Repeat, then verify.** Repeat steps 2 and 3 until a discovery round
   returns no `[blocking]` findings, for at most 3 discovery rounds.

   If there are spec findings, skip verification: the verdict is `fail`.

   Otherwise, if the last discovery round had `[blocking]` findings (all now
   fixed), run up to 2 **verification rounds**. For each:

   1. Write the fixes file `<name>.fixes-<R>.md` to the scratchpad: each
      fixed `[blocking]` finding's title and what changed. `<R>` names the
      round whose fixes are verified: `round-<N>` for the last discovery
      round, `verify-<N>` for a verification round.
   2. Write the diff file: `git diff --no-index <snapshot> <plan>` into
      `<name>.diff-<R>.txt` in the scratchpad, where the snapshot is the copy
      taken before those fixes (exit status 1 means the files differ and is
      expected).
   3. Dispatch a **new** general-purpose subagent with only this prompt,
      with absolute paths:

      > Verify fixes to the implementation plan at `<plan>` in the repository
      > at `<repo root>`. Read `<verify.md>` first and follow it exactly. The
      > document is a plan; its spec is at `<spec>`. The fixed findings are
      > listed in `<fixes file>`; the diff of the fixes is in `<diff file>`.
      > Return only the output format it defines.

   4. No `[blocking]` findings: stop verifying. A finding whose fix would
      change what the spec asks for is a spec finding: stop verifying; the
      verdict is `fail`. Otherwise copy the plan to
      `<name>.before-verify-<N>.md`, fix the findings, re-run the linter, and
      run the next verification round on those fixes only.

   At most 5 review rounds in total (3 discovery + 2 verification).
   If verification round 2 returns `[blocking]` findings, fix those that are
   clear, then list each one under Open as "fixed after verification round
   2, not verified" (or "unresolved" if not fixed); the verdict is `fail`.

   The **plan-introduced decisions** are the last discovery round's list plus
   every verification round's `## Decisions changed` entries (a changed
   decision replaces the old wording).
5. **Verdict.**
   - `pass`: the linter is clean, the last round (discovery or verification)
     returned no `[blocking]` findings, there are no spec findings, and the
     plan-introduced decisions are empty.
   - `pass-with-decisions`: the same, but the plan-introduced decisions are
     not empty.
   - `fail`: anything else.
6. **Record.** Run the linter with `--hash` on the plan and on the spec after
   the last plan edit. Write `docs/superpowers/gates/plans/<plan file name>`
   (create the folder if needed; overwrite an older record):

   ```
   # Plan gate: <plan title>

   - **Plan:** docs/superpowers/plans/<plan file name>
   - **Plan SHA-256:** <--hash of the plan>
   - **Spec:** <spec path from the plan>
   - **Spec SHA-256:** <--hash of the spec>
   - **Verdict:** pass | pass-with-decisions | fail
   - **Date:** YYYY-MM-DD
   - **Rounds:** <D> discovery + <V> verification

   ## Plan-introduced decisions

   - <the plan-introduced decisions, or "none">

   ## Findings fixed

   - <round N | verify N> [blocking|minor] <title>: <what changed in the plan>

   ## Open

   - <each spec finding and each unresolved blocking finding, or "none">
   ```

   The decisions section holds the plan-introduced decisions as defined in
   step 4; that exact list is what the user approves. Then run the linter
   with `--verify-record` on the plan: on `pass` it must print `ok:`; on
   `pass-with-decisions` it prints `decisions not approved` until the user
   approves.
7. **Report to the user.** One short message. Name the plan by path only;
   never open or render it.
   - **pass:** "Plan gate passed in D discovery + V verification rounds; no
     new decisions." Set the plan's Status to `approved` (the hash ignores
     it) and continue straight to the execution choice, with no further
     sign-off.
   - **pass-with-decisions:** "Plan gate passed in D discovery + V
     verification rounds. The plan makes these decisions the spec doesn't:",
     then the list, then "OK?". On yes, add
     `- **Decisions approved:** <today>` to the record and set the plan's
     Status to `approved` (neither changes a hash). On a change request, edit
     the plan and run the gate again from step 1.
   - **fail:** "Plan gate failed." Then each Open item as a direct question
     with the options and your recommendation; a spec finding names the spec
     section to change. After the user answers, update the plan (or the spec,
     which is then gated again with `claude-kit:spec-gate`) and run this gate
     again from step 1.

When `/ship` runs this skill, it runs steps 1–6 only; `/ship` decides what
happens after the verdict.
