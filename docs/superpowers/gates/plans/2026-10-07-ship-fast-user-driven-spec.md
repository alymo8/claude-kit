# Plan gate: Ship Fast User-Driven Spec Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-07-ship-fast-user-driven-spec.md
- **Plan SHA-256:** b9bd1e24ad3afada0e744559683c9c34871105e9e0bec90fc6eaf54c0285b9bc
- **Spec:** docs/superpowers/specs/2026-10-07-ship-fast-user-driven-spec-design.md
- **Spec SHA-256:** 0d52568de752a68357ec853a68ea7d570820fce22df94d279e8c6dbd5989eb85
- **Verdict:** pass-with-decisions
- **Date:** 2026-10-07
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- The live run (success criterion 5) is not part of executing the plan: the user runs it after the merge reaches local `main`, because it needs a person answering the interview and the junction-loaded plugin would shadow a worktree copy. The PR body and report list it as "not run, handed to the user". (Verification item 5)
- A session is non-interactive when the `AskUserQuestion` tool is not available (listed directly or as a deferred tool both count as available), checked before the first question. (Task 1)
- If the user picks a non-recommended approach, the design is not presented again; the grill summary states the chosen approach and what it changes, and no extra question is asked. (Task 1)
- Each inline answer is appended to the task list's `## Decisions` and the task list is committed each time. (Task 1)

## Findings fixed

- round 1 [blocking] Success criterion 5 had no task and misstated the spec: Verification item 5 now explains why the live run is handed to the user after merge and lists it as a plan-introduced decision.
- round 1 [minor] Task 2 test code failed `ruff format --check`: statements rewritten on one line; Step 11 gains a `ruff format tests` fallback.
- round 1 [minor] Manifest test asserted more than the spec: `interview` assertion dropped; checked by hand in Step 11.
- round 1 [minor] Deferred `AskUserQuestion` ambiguity: "listed directly or as a deferred tool both count as available".
- round 1 [minor] README replacement spliced mid-line: full replaced lines 106-110 shown with their target.
- round 2 [minor] Verification item 4 said the manifest test checks `interview`: now says it is checked by hand.
- round 2 [minor] ADR 0021 lacked the literal "amended by 0022": Status line and test use that phrase.

## Open

- none
