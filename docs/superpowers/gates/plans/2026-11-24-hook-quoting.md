# Plan gate: Hook quoting and Vibe installer hardening Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-24-hook-quoting.md
- **Plan SHA-256:** 391729a833d04178668e5cdad554a1403ec97f05578f5fbe09731dbefe62aac1
- **Spec:** docs/superpowers/specs/2026-11-24-hook-quoting-design.md
- **Spec SHA-256:** 6e5dc5c84a5fde605ecb5bc7a08e7431de69642f93bd6d9d4bfecd7c280d3045
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-24
- **Approved by:** /ship (auto)
- **Date:** 2026-11-24
- **Rounds:** 1 discovery + 0 verification

## Plan-introduced decisions

- When rollback leaves a partial new copy at `<out>/<name>` next to its `.old` backup, a rerun moves the backup back only once the user has deleted the partial copy by hand; otherwise the rerun removes the `.old` with the stale staging folder and builds a fresh copy. The error message tells the user to delete the partial copy first (Task 2).
- `vibe_plugin.build` itself refuses unquotable python paths as its first step, so library callers are refused too, not only the two command lines (Task 1).

## Findings fixed

- round 1 [minor] Partial-copy advice can be wrong on rerun: the message and Decisions item 5 now say the partial copy must be deleted by hand (a rerun may refuse it as not built by agent-kit); "or rerun to build a fresh one" dropped.
- round 1 [minor] RestoreError tail wrong for partial-copy entries and used a literal placeholder: the message now names the actual `.old` file names and says the next build moves a copy back only when its plugin folder is missing.
- round 1 [minor] Task 1 Step 3 "Expected: FAIL" included tests that already pass: the step now lists the three tests that pass before the change.

## Open

- none
