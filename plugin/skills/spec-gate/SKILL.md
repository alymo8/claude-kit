---
name: spec-gate
description: Use when a design spec has just been written or revised, before asking the user to review it, or when /ship finds no valid gate record. Lints the spec, runs up to 3 rounds of a fresh-context reviewer subagent, fixes what it finds, and writes a gate record under docs/superpowers/gates/. The user then confirms a short verdict instead of reading the spec.
argument-hint: [path-to-spec.md]
---

# Spec gate

A spec is the contract `/ship` builds against without check-ins, and the user
does not read specs in full. This gate does that reading. It passes only when
the linter is clean and a reviewer that never saw the conversation can plan
the work without questions.

## Setup

- **Spec:** `$ARGUMENTS` if given, else the `*.md` under `docs/superpowers/specs/`
  whose file name sorts last (the newest date prefix). Name it in one line.
- **Linter:** `python <this skill's directory>/../../scripts/spec-lint.py`
  (fallback: `~/.claude/skills/claude-kit/scripts/spec-lint.py`).
- **Rubric:** `rubric.md` in this skill's directory.

## Steps

1. **Lint.** Run the linter on the spec. Fix every violation in the spec and
   re-run until it exits 0. A violation the spec cannot fix without a product
   choice is a decision finding (step 3).
2. **Review round.** Dispatch a **new** general-purpose subagent every round
   (never reuse one; a reviewer anchors on its own earlier findings). Give it
   only this prompt, with absolute paths:

   > Review the design spec at `<spec>` in the repository at `<repo root>`.
   > Read `<rubric.md>` first and follow it exactly. Return only the output
   > format it defines.

   Do not pass it any conversation, summary or plan.
3. **Fix.** For each `[blocking]` finding:
   - If fixing it needs a scope, product or behaviour choice that the spec
     and the conversation do not settle, it is a **decision finding**. Do not
     guess. Collect it for the user.
   - Otherwise, edit the spec to fix it. Fix `[minor]` findings too when the
     fix is clear. Re-run the linter after editing.
4. **Repeat** steps 2 and 3 until a round returns no `[blocking]` findings,
   for at most 3 rounds in total.
5. **Verdict.** `pass` when the linter is clean, the last round returned no
   `[blocking]` findings, and there are no decision findings. Otherwise `fail`.
6. **Record.** Run the linter with `--hash` on the spec after its last edit.
   Write `docs/superpowers/gates/<spec file name>` (create the folder if
   needed; overwrite an older record):

   ```
   # Gate: <spec title>

   - **Spec:** docs/superpowers/specs/<spec file name>
   - **Spec SHA-256:** <the --hash output>
   - **Verdict:** pass | fail
   - **Date:** YYYY-MM-DD
   - **Rounds:** <number of review rounds run>

   ## Key decisions

   - <from the last round's Key decisions, merged with earlier rounds>

   ## Findings fixed

   - <round N> [blocking|minor] <title>: <what changed in the spec>

   ## Open

   - <each decision finding and each unresolved blocking finding, or "none">
   ```

   Then run the linter with `--verify-record` on the spec. On a pass verdict
   it must print `ok:`.
7. **Report to the user.** One short message. Name the spec by path only;
   never open or render it.
   - **pass:** "Gate passed in N rounds; M findings fixed." Then the key
     decisions as a list, then "OK to mark it approved?". On yes, set the
     spec's Status bullet to `approved` (the hash ignores that line, so the
     record stays valid).
   - **fail:** "Gate failed." Then each Open item as a direct question with
     the options and your recommendation. After the user answers, update the
     spec and run the gate again from step 1.

When `/ship` runs this skill, it skips step 7's question: invoking `/ship` is
the approval.
