# Plan gate: Pre-push Lint Hook Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-10-pre-push-hook.md
- **Plan SHA-256:** 472470893429435e093014c4e7c548876e2a3c8030a2a2ee673d1d69496c8b83
- **Spec:** docs/superpowers/specs/2026-10-10-pre-push-hook-design.md
- **Spec SHA-256:** 0e75a11fa817ace0dc3af9246b9b387193d5c08cf6fe73ba69484a7bac99cdd9
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-10-10
- **Date:** 2026-10-10
- **Rounds:** 3 discovery + 0 verification

## Plan-introduced decisions

- A failing `git add --chmod=+x .githooks/pre-push` in adopt mode is fatal: `error: git add failed: <stderr>`, exit 1, the same way `commit_all` treats every failed git command. It runs after the created/skipped report is printed, leaves the written files in place (adopt mode never rolls back) and prints no `hooks:` line. (Task 2; the spec gate left this as a plan question.)

## Findings fixed

- round 1 [blocking] No task checked success criterion 1 on CI or the PR-body half of criterion 4: added Task 5 (both CI legs, PR body without the throwaway name; the name is kept in a scratch file outside the repo).
- round 1 [minor] Task 2 expected-failure list was inaccurate: it now excludes `test_adopt_with_existing_hook_says_nothing_about_hooks`, which already passes.
- round 1 [minor] Over-long line in `plugin/` and formatting covered tests only: lines pre-wrapped and `ruff format plugin tests` added to Task 2.
- round 1 (decision rework) Adopt staging failure changed from a warning with a variant `hooks:` line to fatal, so the spec's `hooks:` line stays verbatim; the adopt output order now only appends the new lines before `review with ...`.
- round 2 [blocking] Task 5 claimed the suite has no skipped tests, but ubuntu skips 6 Windows-only install tests: expected counts are now stated per leg.
- round 2 [minor] Commit steps used `git add -A`: they now stage named paths.
- round 2 [minor] Task 5 assumed an open PR: it now says how to push, open the PR and get the run id outside `/ship`. Adopt staging moved after the created/skipped report.
- round 3 [minor] Unset `core.hooksPath` check read global config: now `git config --local`.
- round 3 [minor] Expected-failure note ignored the no-`sh` skip: noted.

## Open

- none
