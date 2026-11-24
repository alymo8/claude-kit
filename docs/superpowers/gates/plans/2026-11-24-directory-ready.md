# Plan gate: Directory-ready plugin Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-24-directory-ready.md
- **Plan SHA-256:** ad3d98973b56c6c445e662a46504fccb4a61bd8df3fe1408a9bbb10beebe2c5f
- **Spec:** docs/superpowers/specs/2026-11-24-directory-ready-design.md
- **Spec SHA-256:** 2f6126dd4fd1bd3e4c3f1b1ffa876d9e443306732d516c67da9cc71892f4f9c8
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-24
- **Approved by:** /ship (auto)
- **Date:** 2026-11-24
- **Rounds:** 1 discovery + 0 verification

## Plan-introduced decisions

- The README and the data-handling answers disclose the SessionEnd hook's `gh pr view` call (`handoff_snapshot.py` via `handoff.pr_url`, when the branch has an upstream and `gh` is installed) as the one hook network exception, instead of the spec's "hooks open no network connection"; the hook itself is not changed (Task 4; ADR 0055 notes the correction)
- P11 matches only bare `git mv`/`git add` commands (after splitting on `&&`/`;`, tokens starting `git mv`/`git add`); `git -C x add` is not matched; spans in any non-fence line count, prose included, and fence lines in any language count; `git add <src>/file` is not flagged (equality after stripping one trailing `/`) (Task 2)
- `default_parent` prints the error to stderr and raises `SystemExit(2)` itself, with no sentinel (Task 3)
- Rule 3 passes the resolved `--show-toplevel` path to `main_checkout` and accepts its fallback; submodules (whose sibling lands inside the superproject) and a repo at the home folder get no guard (Task 3)
- `test_stop_hook_regenerates_spec_index` asserts the Stop hooks hold exactly `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py"` and no Stop command contains `CLAUDE_PROJECT_DIR` (Task 1)

## Findings fixed

- round 1 [minor] README Network line departs from the spec's settled wording: ADR 0055's Consequences (Task 5 Step 1) now records that the spec's sentence was corrected in `plugin/README.md`.
- round 1 [minor] Task 1's run_hooks test copies into a folder `make_kit` does not create: the step now creates `<plugin>/scripts/` first.

## Open

- none
