# Plan gate: ADR Triggers Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-10-adr-triggers.md
- **Plan SHA-256:** 528519bd6b990db6109f29c38bc3a42f4a88f4786275ff08ad3c7cb8232170ae
- **Spec:** docs/superpowers/specs/2026-10-10-adr-triggers-design.md
- **Spec SHA-256:** 6c95f8253a6ad49a5c802914a826298b4946378a345f585707b81a0b0d09b852
- **Verdict:** pass-with-decisions
- **Date:** 2026-10-10
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- The hand-run spec-gate reviewer eval (`tests/fixtures/spec-gate/README.md`) is not re-run and its Results table is not updated; the PR body says so (Task 3).
- The README line next to the spec gate goes into the mermaid node label: `Spec gate<br/>independent review<br/>+ ADR triggers` (Task 3).

## Findings fixed

- round 1 [blocking] New manifest test name matched `-k adr_triggers` and nothing ran criterion 2: renamed to `test_version_is_0_18_0`; Task 3 runs `pytest -k "adr_triggers" -v` expecting exactly 2 passed.
- round 1 [blocking] Task 2 Step 5 had no expected output: "Expected: all pass." added.
- round 1 [minor] Version fallback not carried into hard-coded values: constraint now covers test, `plugin.json` and commit message.
- round 1 [minor] Criterion 5 had no check step: `grep -c` on the ADR index added.
- round 1 [minor] test_docs parenthetical imprecise: reworded.
- round 2 [minor] Task 3 Files list named the wrong README spot: now the `sgate` mermaid node.

## Open

- none
