# ADR 0013: `/ship` never works in or depends on the local `main` checkout

- **Status:** accepted
- **Date:** 2026-09-29

## Context
`/ship` stopped at pre-flight unless local `main` was clean and level with
`origin/main`. It rarely is: the spec it ships is usually an untracked file in the
main checkout (brainstorming writes it there, and it reaches `main` only through
the PR), and other sessions work in that checkout too. After the merge, `/ship`
also ran `git pull --ff-only` and the test suite in the main checkout. That moved
another session's `main` under it and failed on a dirty tree.

## Decision
- The feature branch is always cut from a freshly fetched `origin/main`. Local
  `main` is never checked, and a dirty, ahead or behind `main` is no reason to
  stop.
- A spec that is not on `origin/main` is committed on the feature branch. The
  main checkout's copy is deleted only when it is untracked and identical to the
  committed one.
- Post-merge verification runs in a temporary detached worktree at the squash
  commit.
- Cleanup leaves the feature worktree first (a worktree-isolated session may not
  run git against the main checkout), then runs git with `-C <main-checkout>`,
  which never changes that checkout's files or branch. Last, local `main` is
  fast-forwarded only when it is on `main` with a clean tree and the fast-forward
  succeeds; otherwise it is left alone and the report says so.

## Consequences
Several sessions can ship in parallel while someone edits in the main checkout.
Unpushed commits on local `main` are never shipped by accident, but they are also
never picked up, so they need their own PR. Local `main` can lag behind
`origin/main` until it is clean; the report names that so it is not missed.
