# Gate: Template CI hardening: SHA-pinned actions, Dependabot, and a workflows README

- **Spec:** docs/superpowers/specs/2026-10-10-template-ci-hardening-design.md
- **Spec SHA-256:** 5fe1c031891fb6b98f523679fbd8901ebcd75bb83076868e7b0c5aea2225d9d1
- **Verdict:** pass
- **Date:** 2026-10-10
- **Rounds:** 3 discovery + 0 verification

## Key decisions

- Every action is pinned to the commit SHA of the newest release tag in its current major, with a full-tag comment; a major with only a moving `vN` tag pins what `vN` points to now, comment `# vN`.
- Dependabot: monthly, one group (`patterns: ["*"]`), GitHub Actions only, in the template and the kit (byte-identical); major-version bumps are not excluded.
- No scheduled (cron) runs and no SAST/dependency scanning until a scanner justifies them (user's choice).
- Branch protection is documented (a bash `gh api` command in the workflows README), never applied; `build-test` and `gitleaks` required, `review` advisory.
- The kit pins its own workflows; its `secret-scan.yml` stays byte-identical to the template, no-paths comment included.
- Adopt mode adds `dependabot.yml` and the workflows README to existing repos when missing, and warns when an existing `ci.yml` may not match the README's check names.
- `claude-review.yml` stays manual; already-scaffolded repos are not patched.
- Live check on a throwaway private python-stack repo, left for the user to delete; its name stays out of tracked files and the PR body.
- ADR at the next free number (0028 expected); minor version bump.

## Findings fixed

- round 1 [blocking] No-paths test contradicted the comment it checks: the test now checks the block of consecutive comment lines above `pull_request:`.
- round 1 [minor] Kit `secret-scan.yml` gets the comment: stated in Scope In.
- round 2 [blocking] Adopt mode's handling of the two new files unspecified: adopt adds both and prints a check-names warning when `ci.yml` was skipped; test added.
- round 2 [minor] Branch-protection heredoc only worked rendered: now a fenced bash block, labelled bash / Git Bash.
- round 3 [minor] Testing omitted the adopt-mode test: added; Scope says "output lines (new and adopt mode)".
- round 3 [minor] Live check stack unnamed: `--stack python`.

## Plan questions

- Does the SHA-pin test use `re.search` per line on `read_text` output (lines start with `      - uses:`)? (Testing)
- Are job IDs extracted by indentation under `jobs:`, or hard-coded (`build-test`, `gitleaks`, `review`) and checked in their files; how is the placeholder template `ci.yml` (`jobs: {}`) handled? (Testing)
- How does `test_plugin_manifest.py`'s `== "0.17.0"` assertion change (relax to `>=` plus a new pin at the new version)? (Scope)
- Where does the adopt-mode check line print relative to the `.gitignore` hint and "review with git status"? (Scaffold output)
- Which README section gets the one-line mention? (Scope)
- If 0027 is still free at ship time, does the ADR take it or stay 0028? (Scope)
- Live check order: `--stack python`, `uv init`, `uv add --dev pytest ruff`, one test, one extra commit, then push? (Success criteria)

## Open

- none
