# Plan gate: agent-kit-lite Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-28-directory-lite.md
- **Plan SHA-256:** 023186b7e28b75b410a1c417a113b52b5b9c38bdeeb203973089a75388ce139e
- **Spec:** docs/superpowers/specs/2026-11-27-directory-lite-design.md
- **Spec SHA-256:** e9f8a61fc6ecc31d68fa9b28b1885a694c399ad62c2244e4a3eb87bfa5720295
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-28
- **Approved by:** /ship (auto)
- **Date:** 2026-11-28
- **Rounds:** 3 discovery + 1 verification

## Plan-introduced decisions

- Markers may also be inline (open and close on one line); a line that inline removal empties is dropped; the build does not skip code fences (Task 2)
- The lite document id removes every `- **Status:**` line outside fences, not only the first, and unticks boxes in specs as well as plans: one pipeline for both (Task 3)
- The variable check allows positional parameters (`$1`, `$@`, `$?`) and `$(`; only `$` or `%` followed by a name counts (Task 2)
- Lite `/ship-fast` ignores `**Repo:** new`, works in the spec's own repository, and stops when the spec is in no git repository; the Docker baseline goes to `<git common dir>/ship-fast/<slug>.docker-baseline.txt` (Task 4)
- The lite Frozen check follows `frozen-check.py`: patterns from the spec's and the plan's Frozen bullets, a merge-base snapshot (or the commit that added the file), and the newest `Frozen-change-approved:` trailer commit as the new snapshot (Task 3)
- Lite `/ship` settles a rebase conflict in `docs/superpowers/README.md` by keeping every row from both sides, and its report says "Spec index: not updated" (Task 4)
- Lite `present` renders no screenshots and asks the user to page through the deck once in a browser (Task 5)
- Wording that changes in both plugins, with the meaning kept: `review/SKILL.md` and `spec-gate/rubric.md` write `./conventions/...`; `audit/rules.md` and `lean-context/SKILL.md` drop their `$TMPDIR`, `%TEMP%` and `$SCRATCH` spellings (Tasks 3, 5)
- A missing `references/<name>.md` named by a kept file fails the build; a backticked file name the build leaves out (such as `user-mode.md`) is handled by the marker edits, not by a check (Tasks 2, 5)
- Icon design: a teal square with three white bars and a white check mark, drawn by a throwaway script (Task 1)

## Findings fixed

- round 1 [blocking] lean-context edit broke `test_kit_map_inject.py` and `test_fallbacks_name_the_kit_map_root`: the whole pinned phrase is wrapped in one F block, the L text uses a relative path; Context facts and Step 9 tests added
- round 1 [blocking] Task 5's final check needed Tasks 1, 3, 4: Step 8 narrowed to Task 5's own files
- round 1 [blocking] Task 7's docs link needed `lite/`: Task 7 depends on Task 6
- round 1 [blocking] column-0 numbered-item rule contradicted session-hygiene edits: the rule now applies only to `ship.md`, `ship-fast.md` and `references/ship-*.md`
- round 1 [blocking] isolated config had no sign-in: Task 8 asks the user to log in once in `<cfg>`
- round 1 [minor] Task 2 Step 6 expected output: names the missing icon and checklist too
- round 1 [minor] record templates' hash placeholders: lite text says the `lite-git:` lines replace them
- round 2 [blocking] SC5 check ran the main checkout's agent-kit: Task 8 Step 2 installs the worktree's `agent-kit` into a second isolated config
- round 2 [minor] ship-finish lite text said "never by hand": the F block now ends after it
- round 2 [minor] lite `/ship-fast` stop rule missing from the list: lite-only stop bullet added; step 2's new-repo sentence made full-only
- round 2 [minor] `pr-body.md` needing no edit: stated in Task 4 Step 7
- round 3 [blocking] Task 1 could not commit under the gitignored `scripts/`: the whitelist moved into Task 1; Task 2 checks it
- round 3 [blocking] new files broke `test_no_live_file_names_old_conventions_root`: `CONV_RE` and the unit-test fixtures build the string as `"conventions" + "/"`; Context fact added
- round 3 [blocking] lite `present` check looser than `check-deck.py`: covers `@import`, outside HTML comments, no clickable-link exception
- round 3 [minor] lite `/ship` report asked for the `docker disk:` line: made full-only
- round 3 [minor] ambiguous review filter in lite `pr-review-respond`: both filters apply to reviews and comments
- round 3 [minor] Task 4 Step 4 bullet order and a `present` line number: reordered; the sentence is named instead

## Open

- none
