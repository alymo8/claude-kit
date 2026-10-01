---
name: plan-gate
description: Use when an implementation plan has just been written or revised, before offering an execution choice, or when /ship has written a plan. Lints the plan, runs up to 3 rounds of a fresh-context reviewer subagent that checks it against its spec, fixes what it finds, and writes a gate record under docs/superpowers/gates/plans/. The user signs off only on decisions the plan adds that the spec did not settle.
argument-hint: [path-to-plan.md]
---

# Plan gate

A plan is the only context its executor gets, and the user does not read
plans. This gate does that reading. It passes only when the linter is clean
and a reviewer that never saw the conversation finds every spec item covered
and every task executable from the plan alone. The user signs off only on
decisions the plan makes that its spec did not settle.

## Setup

- **Plan:** `$ARGUMENTS` if given, else the `*.md` under
  `docs/superpowers/plans/` whose file name sorts last. Name it in one line.
- **Spec:** the path on the plan's `**Spec:**` line.
- **Linter:** `python <this skill's directory>/../../scripts/spec-lint.py`
  (fallback: `~/.claude/skills/claude-kit/scripts/spec-lint.py`).
- **Rubric:** `rubric.md` in this skill's directory.

## Steps

1. **Lint.** If the plan has no `- **Status:**` bullet, add
   `- **Status:** draft`. Run the linter on the plan and fix every other
   violation in the plan, re-running until it exits 0. If `P4-spec-gated` is
   then the only violation left, stop with verdict `fail`: write no record,
   and report that the spec must pass `claude-kit:spec-gate` first. Never
   edit the spec from this gate.
2. **Review round.** Dispatch a **new** general-purpose subagent every round
   (never reuse one; a reviewer anchors on its own earlier findings). Give it
   only this prompt, with absolute paths:

   > Review the implementation plan at `<plan>` against its spec at `<spec>`
   > in the repository at `<repo root>`. Read `<rubric.md>` first and follow
   > it exactly. Return only the output format it defines.

   Do not pass it any conversation or summary.
3. **Fix.** For each `[blocking]` finding, edit the plan to fix it, unless
   the fix would change what the spec asks for: that is a **spec finding**.
   Do not fix it in the plan; collect it for the Open list. Fix `[minor]`
   findings too when the fix is clear. Re-run the linter after editing.
4. **Repeat** steps 2 and 3 until a round returns no `[blocking]` findings,
   for at most 3 rounds in total.
5. **Verdict.**
   - `pass`: the linter is clean, the last round returned no `[blocking]`
     findings, there are no spec findings, and the last round listed no
     plan-introduced decisions.
   - `pass-with-decisions`: the same, but the last round listed
     plan-introduced decisions.
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
   - **Rounds:** <number of review rounds run>

   ## Plan-introduced decisions

   - <the last round's list, or "none">

   ## Findings fixed

   - <round N> [blocking|minor] <title>: <what changed in the plan>

   ## Open

   - <each spec finding and each unresolved blocking finding, or "none">
   ```

   The decisions section holds the last round's list; that exact list is
   what the user approves. Then run the linter with `--verify-record` on the
   plan: on `pass` it must print `ok:`; on `pass-with-decisions` it prints
   `decisions not approved` until the user approves.
7. **Report to the user.** One short message. Name the plan by path only;
   never open or render it.
   - **pass:** "Plan gate passed in N rounds; no new decisions." Set the
     plan's Status to `approved` (the hash ignores it) and continue straight
     to the execution choice, with no further sign-off.
   - **pass-with-decisions:** "Plan gate passed in N rounds. The plan makes
     these decisions the spec doesn't:", then the list, then "OK?". On yes,
     add `- **Decisions approved:** <today>` to the record and set the plan's
     Status to `approved` (neither changes a hash). On a change request, edit
     the plan and run the gate again from step 1.
   - **fail:** "Plan gate failed." Then each Open item as a direct question
     with the options and your recommendation; a spec finding names the spec
     section to change. After the user answers, update the plan (or the spec,
     which is then gated again with `claude-kit:spec-gate`) and run this gate
     again from step 1.

When `/ship` runs this skill, it runs steps 1–6 only; `/ship` decides what
happens after the verdict.
