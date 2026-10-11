# ADR 0029: Pre-push lint hook in scaffolded repos

- **Status:** accepted
- **Date:** 2026-10-10

## Context
A lint error in a scaffolded repo was found only by CI after the push. It
cost a CI run and a `/ship` fix attempt for a problem the lint command
would have caught locally in seconds.

## Decision
- Scaffolded repos ship `.githooks/pre-push`, which runs the stack's CI
  lint and nothing else. It is one POSIX script that Git for Windows runs
  in its `sh`.
- New mode records the hook `100755` in the index and sets
  `core.hooksPath .githooks`.
- Adopt mode stages the hook executable and never sets git config, because
  that would silently replace husky, pre-commit or `.git/hooks`.
- A template `.gitattributes` keeps the hook LF on Windows clones.
- No pre-commit hook: auto-fixing and re-staging changes a commit an agent
  made without it seeing the change.
- No tests or typecheck in the hook, to keep pushes fast.

## Consequences
- Other clones enable the hook with one command
  (`git config core.hooksPath .githooks`).
- The hook lints the working tree, not the pushed commits.
- `git push --no-verify` skips it.
- Already-scaffolded repos are not patched.
