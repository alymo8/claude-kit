# Plan gate: Template CI Hardening Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-10-template-ci-hardening.md
- **Plan SHA-256:** 7056de87167ffbf0d3ba203d056b4867f3cdabac6eb8e5b5ceebf9c6b9bc8f54
- **Spec:** docs/superpowers/specs/2026-10-10-template-ci-hardening-design.md
- **Spec SHA-256:** 5fe1c031891fb6b98f523679fbd8901ebcd75bb83076868e7b0c5aea2225d9d1
- **Verdict:** pass
- **Date:** 2026-10-10
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- none

## Findings fixed

- round 1 [blocking] Task 2 uses Task 1's `STACK_CIS` but declared no dependency: Task 2 now depends on Task 1; Task 1's Interfaces names `KIT_WORKFLOWS`, `STACK_CIS`, `PIN_RE`, `_workflow_files()`; Task 2 consumes `STACK_CIS`.
- round 1 [blocking] Success criterion 2 (green kit CI on the PR) unmapped: Task 4 Step 7 pushes, opens the PR and watches `ci` (both OS) and `secret-scan`.
- round 1 [minor] Live-check owner and run timing implicit: owner from `gh api user --jq .login`; `gh run list` re-run every 15 s until both runs appear.
- round 2 [minor] README anchor sentence wraps in the file: Step 3 points at line ~100 and inserts before "`/handoff` writes…".
- round 2 [minor] Live-check name hard-coded despite suffix rule: `NAME` variable used throughout.

## Open

- none
