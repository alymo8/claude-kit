# Gate: Pre-push lint hook in scaffolded repos

- **Spec:** docs/superpowers/specs/2026-10-10-pre-push-hook-design.md
- **Spec SHA-256:** 0e75a11fa817ace0dc3af9246b9b387193d5c08cf6fe73ba69484a7bac99cdd9
- **Verdict:** pass
- **Date:** 2026-10-10
- **Rounds:** 3 discovery + 0 verification

## Key decisions

- Pre-push hook, lint only (`ruff check` + `ruff format --check` / `pnpm lint`); no pre-commit auto-fix, no tests or typecheck (user's choice).
- One POSIX `sh` script for all OSes (Git for Windows runs hooks in its `sh`); no PowerShell variant or setup scripts.
- Missing manifest skips lint (exit 0); missing `uv`/`pnpm` fails the push.
- New mode sets `core.hooksPath=.githooks`; adopt mode never sets git config, stages the hook (`git add --chmod=+x`) and prints how to enable it.
- Executable bit set on the working file and recorded in the index (`100755`); template `.gitattributes` forces LF for `.githooks/*`.
- The hook lints the working tree, not the pushed commits; its comment says so.
- No hook in the kit repo itself; built after the CI-hardening spec (adds a paragraph to its workflows README); ADR 0029 expected; minor version bump.
- Live check on this Windows machine with a throwaway repo left for the user to delete.

## Findings fixed

- round 1 [blocking] Hook not executable in the working tree on Linux/macOS (hook ignored, `git status` dirty): both modes chmod the working file; non-Windows test asserts `X_OK` and a clean status.
- round 1 [minor] Module docstring outdated: added to Scope.
- round 1 [minor] Criterion 4 loosely worded: `git grep <name>` and `gh pr view --json body` checks.
- round 2 [blocking] CRLF checkout on Windows clones (`core.autocrlf=true`) breaks `sh`: template ships `.gitattributes` with `.githooks/* text eol=lf`; clone test added; adopt prints a check when `.gitattributes` exists.
- round 2 [minor] Adopt hint inaccurate with an existing `core.hooksPath`: wording covers both.
- round 2 [minor] `<name>` undefined: defined.
- round 3 [minor] Line-endings test lost its `\r`: explicit `b"\r" not in path.read_bytes()`.
- round 3 [minor] Adopt test did not check the staged mode: asserts `100755`.
- round 3 [minor] Working-tree vs pushed-commit lint: stated in the hook comment and Decisions.
- round 3 [minor] README line unspecified: text and section given.

## Plan questions

- Which `EXPECTED` entries are added (`.gitattributes` in test_templates; `.gitattributes` and `.githooks/pre-push` in test_scaffold, merged with the CI-hardening additions)? (Testing)
- Is a failing `git add --chmod=+x` in adopt mode fatal or a warning? (Design > Adopt mode)
- Order of the `.gitignore` check, `hooks:` and `.gitattributes` check lines in adopt output? (Design > Adopt mode)
- How do hook tests build fake `uv`/`pnpm` and `PATH` so they behave the same under MSYS `sh` on `windows-latest` and Linux `sh`? (Testing)
- Does a failing post-commit `git config core.hooksPath` remove the new directory like the other steps? (Design > New mode)
- Does the chmod go in `scaffold_new` or `commit_all`? (Design > Scaffolder)

## Open

- none
