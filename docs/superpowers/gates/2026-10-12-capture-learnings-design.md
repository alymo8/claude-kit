# Gate: Capture learnings when a feature is finished

- **Spec:** docs/superpowers/specs/2026-10-12-capture-learnings-design.md
- **Spec SHA-256:** 63bcc8738d31a29b1a2f609488b369a182c853876bab86b5d4da2ac84e82f48d
- **Verdict:** pass
- **Date:** 2026-10-12
- **Rounds:** 2 discovery + 0 verification

## Key decisions

- Learnings are captured when a feature finishes, not at session end; no `SessionEnd`/`Stop` hook.
- Learnings are committed on the feature branch and land in the feature's PR, before merge.
- No approval pause: learnings are listed in the report's Learnings line and visible in the PR diff, keeping `/ship`'s no-check-in promise.
- One flow-invoked skill, `capture-learnings`, called from `/ship` step 7, `/ship-fast` step 7 and the workspace `CLAUDE.md` rule for manual finishes.
- Each learning is routed by kind to an existing home: `CLAUDE.md`, `knowledge/`, a new ADR, or auto-memory (never tracked); no new learnings file.
- No ADRs on `poc/` branches or in repos without `knowledge/decisions/`; such decisions are listed in the summary instead.
- `CLAUDE.md` entries move to `knowledge/` once `CLAUDE.md` would exceed 100 lines (so in the kit itself, whose `CLAUDE.md` is already longer, they always go to `knowledge/`).
- No secrets, personal data, other private repo names or account names in learnings, in any repo.
- `/handoff`, `/ship-many` and `superpowers:finishing-a-development-branch` are unchanged; no back-filling.
- Minor version bump and a new ADR (required: the change alters a workflow).

## Findings fixed

- round 1 [blocking] ADR route depends on a file other repos do not have: ADRs follow the repo's `0000-template.md` (else README, else newest ADR); fallbacks added for missing `knowledge/` and `knowledge/decisions/`.
- round 1 [blocking] Success criterion expects dropped candidates the skill never returns: the Return lists dropped candidates with their rule when nothing is written; test added.
- round 1 [minor] Section names do not match the CLAUDE.md template: lists the template's headings.
- round 1 [minor] Redundant push wording in `/ship-fast`: step 7 runs the skill, then its existing push.
- round 1 [minor] ADR route vs the decision-log's NOT REQUIRED list: no ADRs on `poc/` branches.
- round 1 [plan→fixed] How "public repo" is determined: the private-name rule applies to every repo.
- round 2 [minor] "about 100 lines" threshold: exact limit of more than 100 lines; an over-limit file always qualifies.

## Plan questions

- Add a `_step` helper to `tests/test_ship_fast_command.py` (copied from `test_ship_command.py`) or share it via `tests/helpers.py`? (Testing)
- Should step 1 also mine subagent/task reports and the CI fix-loop history for candidates? (Design: The skill, step 1)
- The learnings commit lands after the step-6 code review: is the PR diff enough, or should step 7 re-run lint and tests before the push? (Design: `/ship`)
- When an existing `CLAUDE.md` lacks the matching heading, add it or use the closest section? (Design: Route)
- Does the skill's ADR route, and this spec's own ADR, add a row to `knowledge/decisions/README.md`? (Scope In; Design: Route)
- Under `/ship-many`, should the skill re-read `MEMORY.md` right before writing to avoid concurrent-write collisions? (Design: Route)
- On a `/ship-fast` Resume at step 7, does the "already recorded" filter prevent a second `Capture learnings` commit, or should Resume skip the skill? (Design: `/ship-fast`)

## Open

- none
