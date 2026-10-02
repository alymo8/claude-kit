---
name: spec-gate
description: Use when a design spec has just been written or revised, before asking the user to review it, or when /ship finds no valid gate record. Lints the spec, runs up to 3 discovery rounds of a fresh-context reviewer subagent, then up to 2 verification rounds of its fixes, fixes what it finds, and writes a gate record under docs/superpowers/gates/. The user then confirms a short verdict instead of reading the spec.
argument-hint: [path-to-spec.md]
---

# Spec gate

A spec is the contract `/ship` builds against without check-ins, and the user
does not read specs in full. This gate does that reading. It passes only when
the linter is clean, a reviewer that never saw the conversation finds nothing
blocking, and the last fixes have been verified. "How" questions that the plan
can settle do not block: they are handed to the plan.

## Setup

- **Spec:** `$ARGUMENTS` if given, else the `*.md` under `docs/superpowers/specs/`
  whose file name sorts last (the newest date prefix). Name it in one line.
- **Linter:** `python <this skill's directory>/../../scripts/spec-lint.py`
  (fallback: `~/.claude/skills/claude-kit/scripts/spec-lint.py`).
- **Rubric:** `rubric.md` in this skill's directory (discovery rounds).
- **Verify rubric:** `verify.md` in this skill's directory (verification
  rounds).
- **Scratchpad:** the session's scratchpad directory, or a temporary
  directory outside the repository. Snapshots, fixes files and diff files go
  there; `<name>` below is the spec's file name.

## Steps

1. **Lint.** Run the linter on the spec. Fix every violation in the spec and
   re-run until it exits 0. A violation the spec cannot fix without a product
   choice is a decision finding (step 3).
2. **Review round.** This is a **discovery round**. Dispatch a **new**
   general-purpose subagent every round (never reuse one; a reviewer anchors
   on its own earlier findings). Give it only this prompt, with absolute
   paths:

   > Review the design spec at `<spec>` in the repository at `<repo root>`.
   > Read `<rubric.md>` first and follow it exactly. Return only the output
   > format it defines.

   Do not pass it any conversation, summary or plan.
3. **Fix.** Before applying this round's fixes, copy the spec to the
   scratchpad as `<name>.before-round-<N>.md`. For each `[blocking]` finding:
   - If fixing it needs a scope, product or behaviour choice that the spec
     and the conversation do not settle, it is a **decision finding**. Do not
     guess. Collect it for the user.
   - Otherwise, edit the spec to fix it. Fix `[minor]` findings too when the
     fix is clear.

   Do **not** fix `[plan]` findings in the spec. Collect each one's question
   and spec section for the record, dropping duplicates by question. Re-run
   the linter after editing.
4. **Repeat, then verify.** Repeat steps 2 and 3 until a discovery round
   returns no `[blocking]` findings, for at most 3 discovery rounds.

   If there are decision findings, skip verification: the verdict is `fail`,
   and the rerun after the user answers starts from step 1.

   Otherwise, if the last discovery round had `[blocking]` findings (all now
   fixed), run up to 2 **verification rounds**. For each:

   1. Write the fixes file `<name>.fixes-<R>.md` to the scratchpad: each
      fixed `[blocking]` finding's title and what changed. `<R>` names the
      round whose fixes are verified: `round-<N>` for the last discovery
      round, `verify-<N>` for a verification round.
   2. Write the diff file: `git diff --no-index <snapshot> <spec>` into
      `<name>.diff-<R>.txt` in the scratchpad, where the snapshot is the copy
      taken before those fixes (exit status 1 means the files differ and is
      expected).
   3. Dispatch a **new** general-purpose subagent with only this prompt,
      with absolute paths:

      > Verify fixes to the design spec at `<spec>` in the repository at
      > `<repo root>`. Read `<verify.md>` first and follow it exactly. The
      > document is a spec. The fixed findings are listed in `<fixes file>`;
      > the diff of the fixes is in `<diff file>`. Return only the output
      > format it defines.

   4. No `[blocking]` findings: stop verifying. A finding that needs a choice
      the spec and conversation do not settle is a decision finding: stop
      verifying; the verdict is `fail`. Otherwise copy the spec to
      `<name>.before-verify-<N>.md`, fix the findings, re-run the linter, and
      run the next verification round on those fixes only.

   At most 5 review rounds in total (3 discovery + 2 verification).
   If verification round 2 returns `[blocking]` findings, fix those that are
   clear, then list each one under Open as "fixed after verification round
   2, not verified" (or "unresolved" if not fixed); the verdict is `fail`.
5. **Verdict.** `pass` when the linter is clean, the last round (discovery or
   verification) returned no `[blocking]` findings, and there are no decision
   findings. Otherwise `fail`. `[plan]` findings never affect the verdict.
6. **Record.** Run the linter with `--hash` on the spec after its last edit.
   Write `docs/superpowers/gates/<spec file name>` (create the folder if
   needed; overwrite an older record):

   ```
   # Gate: <spec title>

   - **Spec:** docs/superpowers/specs/<spec file name>
   - **Spec SHA-256:** <the --hash output>
   - **Verdict:** pass | fail
   - **Date:** YYYY-MM-DD
   - **Rounds:** <D> discovery + <V> verification

   ## Key decisions

   - <the discovery rounds' Key decisions merged, plus each verification
     round's Decisions changed (a changed decision replaces the old wording)>

   ## Findings fixed

   - <round N | verify N> [blocking|minor] <title>: <what changed in the spec>

   ## Plan questions

   - <question> (<spec section>), or "none"

   ## Open

   - <each decision finding and each unresolved blocking finding, or "none">
   ```

   Then run the linter with `--verify-record` on the spec. On a pass verdict
   it must print `ok:`.
7. **Report to the user.** One short message. Name the spec by path only;
   never open or render it.
   - **pass:** "Gate passed in D discovery + V verification rounds; M
     findings fixed.", plus "K plan questions handed to the plan." when K is
     more than 0. Then the key decisions as a list, then "OK to mark it
     approved?". On yes, set the spec's Status bullet to `approved` (the hash
     ignores that line, so the record stays valid).
   - **fail:** "Gate failed." Then each Open item as a direct question with
     the options and your recommendation. After the user answers, update the
     spec and run the gate again from step 1.

When `/ship` runs this skill, it skips step 7's question: invoking `/ship` is
the approval.
