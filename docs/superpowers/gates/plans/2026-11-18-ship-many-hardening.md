# Plan gate: `/ship-many` hardening Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-18-ship-many-hardening.md
- **Plan SHA-256:** 8e48e9670a5fc22b22275a8133ab8eb8edd4a1bc3ada0c60e4e1217b343aa531
- **Spec:** docs/superpowers/specs/2026-11-18-ship-many-hardening-design.md
- **Spec SHA-256:** d48d05e67ac9c762abe9397bbb14f8d1506ce8d55989092972e397f50a2c0ca8
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-18
- **Approved by:** /ship (auto)
- **Date:** 2026-11-18
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- No `/ship` note or test is added; a stop-rule handoff written outside the feature worktree costs one extra attempt, which is accepted (Task 2).
- The runner creates a missing `--log` directory instead of exiting 2 (Task 2).
- `gh` exiting 0 but printing something other than a JSON list of objects counts as `gh failed`; a PR entry whose `createdAt` cannot be parsed is skipped, not counted as merged (Task 2).
- `/ship-many` step 5 reads a child's `result` text from its last attempt's JSON file (`<log-name>.resume.json` when there were two attempts) (Task 3).

## Findings fixed

- round 1 [blocking] Full-suite check ran in Task 4, which depends on nothing: the full `pytest`, ruff and username grep moved to Task 5 Step 0 (depends on Tasks 3 and 4); Task 4 Step 8 runs only its touched tests.
- round 1 [blocking] Keep-awake fake's `wait` conflicted with `release()`'s `wait(5)`: the fake raises only for `wait(timeout=1)`; `release()` falls back to `kill()` on `TimeoutExpired`.
- round 1 [minor] Task 3 Step 2 expected output now names which tests fail and which pass.
- round 1 [minor] First attempt's `cwd` stated as `main`, the resume's as the chosen directory.
- round 1 [minor] `systemd-inhibit` starts in its own session and is released with `os.killpg`, so `sleep infinity` does not orphan.
- round 2 [minor] Linux keep-awake test patches `os.killpg` with `raising=False` (absent on Windows); the fake exposes `pid`.
- round 2 [minor] `/ship` step 2 insertion point now names the `Branch ...` sentence correctly.

## Open

- none
