# Plan gate: Scaffold Secret Scan Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-07-scaffold-secret-scan.md
- **Plan SHA-256:** 3c7a02dbca3bbb4304f3cc05d914cba09f5f62a10e0cfcf7bf75bc8713b2d186
- **Spec:** docs/superpowers/specs/2026-10-07-scaffold-secret-scan-design.md
- **Spec SHA-256:** cf9d30feaaa761bd9c62f8ea280cae00a0c61f892c6ad4920cff99e1d419454b
- **Verdict:** pass-with-decisions
- **Date:** 2026-10-07
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- Bump the plugin to 0.13.1 and change the version literal in `tests/test_plugin_manifest.py::test_description_mentions_ship_fast`; both files are outside the spec's Scope In (Task 1).
- The permissions test requires `contents: read` to be the only entry in the top-level `permissions:` block (Task 1).
- No local gitleaks pre-scan of the kit history: the branch's push CI is the first full-history scan, and a finding there stops the work and is reported, with no `.gitleaksignore` entry or history edit (Task 3).
- The live check uses the python stack in a fresh `mktemp -d` directory, deleted afterwards, with a state file in `$HOME` also deleted; a failing scaffolded `ci.yml` run is ignored (Task 2).
- If the throwaway repo's `default_workflow_permissions` is `write`, the live check notes that the 403 condition was not reproduced and continues (Task 2).
- The harmless PR on the throwaway repo is left open along with the repo (Task 2).

## Findings fixed

- round 1 [blocking] No task verifies success criterion 2: added Task 3 (branch push run, PR run, `main` run after the squash-merge; a kit history finding stops and is reported).
- round 1 [blocking] Task 2 assumes shell state persists: step 1 writes `OWNER`/`NAME`/`PARENT` to `$HOME/.secret-scan-check.env`; every later step reloads it with guards; cleanup guards `rm -rf`.
- round 1 [minor] LF wording vs CRLF working tree: explained that only working-tree equality matters and `cp` guarantees it.
- round 2 [minor] Task 3 PR check could not show the commit: uses `--commit "$(git rev-parse HEAD)"` and `headSha`.

## Open

- none
