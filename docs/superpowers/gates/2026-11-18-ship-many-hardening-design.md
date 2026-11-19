# Gate: `/ship-many` hardening: time limit, one resume, keep-awake

- **Spec:** docs/superpowers/specs/2026-11-18-ship-many-hardening-design.md
- **Spec SHA-256:** d48d05e67ac9c762abe9397bbb14f8d1506ce8d55989092972e397f50a2c0ca8
- **Verdict:** pass
- **Date:** 2026-11-18
- **Rounds:** 3 discovery + 0 verification

## Key decisions

- Children run with `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` rather than a rule keeping their suites in the foreground (D1).
- A new standard-library runner, `plugin/scripts/ship-child.py`, enforces 2 hours per attempt and kills the whole process tree; at most 2 attempts, worst case 4 hours per child (D2).
- Resume exactly once on any ending without a merged PR, a stop-rule handoff (a `Written` line not by `session-end snapshot`) or a timeout; no error-pattern matching. A failing `gh` lookup (`gh failed`) or a `feat/<slug>` worktree that existed before the run blocks the resume. Stop rules that fire before the worktree exists (fetch failure, spec gate) are retried on purpose (D3).
- The runner requests keep-awake per OS; a closed laptop lid stays out of scope (D4).
- No ADR-number reservation and no holding of later waves; rely on `/ship` step 9 renumbering, keeping ADR 0018's independence of children (D5).
- The branch slug rule (spec file name minus date prefix and `-design`) becomes a contract between `/ship` and the runner (D6).
- `/ship-many` excludes specs with duplicate slugs and drops the `-2`/`-3` log-name suffix rule.
- Rerunning over an existing `feat/<slug>` branch, `/ship-fast` and a plain `/ship` stay unchanged.
- Nothing is frozen (D7); new ADR recording D1 to D6; minor version bump.

## Findings fixed

- round 1 [blocking] Handoff mtime cannot tell a stop rule from the SessionEnd snapshot: stop rule now read from the handoff's `Written` line (`<by>` not `session-end snapshot`); tests for snapshot-written files added.
- round 1 [blocking] Failing `gh` after a merge triggered a rerun in the main checkout: a failing `gh` now gives `resume: "gh failed"` and no resume; test added.
- round 1 [blocking] D6 had no ADR: the ADR records D6 as a `/ship`–runner contract.
- round 1 [minor] Scope said fake `git`: now fake `claude`/`gh` and a real git repository.
- round 1 [minor] "PRs 57 to 64" overstated: now "PRs 57, 63 and 64".
- round 1 [minor] Dead log-name suffix rule: step 4 drops it.
- round 1 (plan questions folded in) Executables resolved with `shutil.which` (exit 2 when not found); `gh` runs from `--main` with UTC-aware comparison; a pre-existing `feat/<slug>` worktree gives `no worktree`.
- round 2 [blocking] Stop-rule detection relied on a model-typed timestamp: time comparison dropped; the pre-existing-worktree rule makes any handoff come from this run.
- round 2 [blocking] D3 claimed stop rules are never retried while early ones are: D3 now says the two pre-worktree stop rules are retried on purpose, and why.
- round 2 [minor] README sentence now mentions the closed-lid limit; ADR now records D1 to D6.
- round 2 (plan questions folded in) `SetThreadExecutionState` called and reset on the main thread; a missing status file gives unknown cost and attempts.
- round 3 [minor] "moved the spec" reworded; D3 summary names the `gh failed` and no-worktree cases.

## Plan questions

- Should a `/ship` note or test make sure a stop-rule handoff is written from the feature worktree, or is one extra (harmless) attempt acceptable when it lands in the main checkout? (Design, Child runner, point 3)
- How do the resume and stop-rule test fixtures create the `feat/<slug>` worktree after the runner's pre-attempt snapshot (for example, the fake `claude` creates it)? (Testing)
- Does the runner create a missing `--log` directory or exit 2? (Design, Child runner)
- How is the prompt passed intact through a `claude.cmd` shim on Windows (list argv, checked by the fake `.cmd` launcher test)? (Design, Child runner, point 2)

## Open

- none
