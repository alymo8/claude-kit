# Plan gate: Capture learnings at feature finish Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-12-capture-learnings.md
- **Plan SHA-256:** d5b9e6b25a61be595aca59c4f023fc8dad7142a185df651f1a4249f84d458bf8
- **Spec:** docs/superpowers/specs/2026-10-12-capture-learnings-design.md
- **Spec SHA-256:** 63bcc8738d31a29b1a2f609488b369a182c853876bab86b5d4da2ac84e82f48d
- **Verdict:** pass-with-decisions
- **Date:** 2026-10-12
- **Rounds:** 3 discovery + 0 verification
- **Decisions approved:** 2026-10-12

## Plan-introduced decisions

- The skill also mines subagent/task reports and the CI fix-loop history for candidates, not only the main context (Task 1).
- `/ship` step 7 runs the full test suite and lint after a learnings commit and before `git push`; `/ship-fast` relies on CI from its existing push (Tasks 2, 3).
- When an existing `CLAUDE.md` lacks the matching heading, the skill appends that heading at the end of the file (Task 1).
- The skill adds an index row to `knowledge/decisions/README.md` for every ADR it writes when that index has a table; this change's ADR 0031 gets its row (Tasks 1, 5).
- For auto-memory, the skill re-reads `MEMORY.md` right before writing and adds one pointer line instead of rewriting the file, so concurrent `/ship-many` children do not overwrite each other (Task 1).
- A rerun or `/ship-fast` resume relies on the "already recorded at its destination" filter (nothing new → no commit) rather than skipping the skill (Task 1).

## Findings fixed

- round 1 [blocking] Existing `test_version_is_0_21_0` breaks on the version bump: Task 5 replaces it with `test_version_is_0_22_0`.
- round 1 [blocking] `test_never_writes_secrets` fails on wrapped text: skill tests match against whitespace-collapsed text (`flat()`).
- round 1 [blocking] Success criterion 3 (live check) unassigned: new Task 6 runs the skill from the worktree before the PR.
- round 1 [minor] Private-name check only in Task 5: moved into Global Constraints as a before-every-commit check.
- round 1 [minor] `test_none_is_a_valid_result` lacked "rule that dropped it": assertion added.
- round 1 [minor] `/ship-fast` learnings commit would restart the app: step 7 text says it needs no restart.
- round 2 [blocking] plugin.json description edit outside spec scope: dropped; manifest change is the version bump only.
- round 2 [minor] Task 6 did not carry the summary into the report: Step 4 added.
- round 2 [minor] README addition more than one line: descriptive paragraph dropped.
- round 2 [minor] Private-name check missing from Tasks 1–4 commit steps: added to each.
- round 3 [minor] Task 6 checked private names after the commit: check now runs on the staged diff before the skill commits.
- round 3 [minor] Task 6 expected subject assumed linear history: expectation allows any non-`Capture learnings` subject, including a merge commit.

## Open

- none
