# Plan gate: `pr-review-respond` Skill Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-10-pr-review-respond.md
- **Plan SHA-256:** 731060b85175e1dcb96398610ce29cd0be2bf1b3b50a750fb573062658fd7d41
- **Spec:** docs/superpowers/specs/2026-10-10-pr-review-respond-design.md
- **Spec SHA-256:** c274ce102811474f554535ef963e959e32781f16af98f07377d28333d1dbcf11
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-10-10
- **Date:** 2026-10-10
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- A branch ahead of its upstream (local commits from an earlier run that stopped before pushing) does not stop the skill: those commits are listed in the approval table and pushed in step 6 with the new ones.
- When the repo's `CLAUDE.md` is missing or lists no test/lint commands, the skill uses the commands its CI workflows (`.github/workflows/*.yml`) run; if there are none either, the table says so and CI in step 8 is the only verification.
- At the re-fetch before posting, a step-1 thread missing from the new output (resolved or answered meanwhile) gets no reply and is reported as "resolved or answered meanwhile (no reply posted)", separately from new unanswered items.
- A null GraphQL author (deleted account) is reported as `ghost` and, not being the viewer, its items are kept.
- Each **fix** paragraph in the combined PR comment names its commit's short SHA, like thread fix replies.
- In the live check, whoever executes the plan acts as the user at the approval gate and approves the table as drafted, so replies are posted under the user's account in the throwaway repo without the user seeing them first.

## Findings fixed

- round 1 [blocking] Live check expected test-command discovery the skill does not do: the throwaway repo's `CLAUDE.md` (uv: `uv run pytest`, `uv run ruff check .`) is the deterministic source; files go under `src/<pkg>/` and `tests/`; the bot workflow takes the file path as an input; repo CI result does not gate the check.
- round 1 [minor] Version hardcoded to 0.20.0: bump the minor of whatever `main` has if it moved.
- round 1 [minor] Resolved threads reported as "new and still unanswered": two report groups.
- round 1 [minor] PR-body name check fell after the last task: explicit Step 7 after the kit PR opens.
- round 2 [minor] README skill list not updated: `pr-review-respond` added to the skills list, anchor line clarified.
- round 2 [minor] Live-check approval wording assumed `/ship`: "whoever executes this plan".

## Open

- none
