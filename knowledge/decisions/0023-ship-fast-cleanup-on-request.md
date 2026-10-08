# ADR 0023: `/ship-fast` hands over a running POC; cleanup waits for the user

- **Status:** accepted
- **Date:** 2026-10-07

## Context
`/ship-fast` (ADR 0021, 0022) removed its worktree, local branch and Docker
objects as its last automatic step. The POC is then shown to a client and
tested by the user, which needs the workspace and a running app; the
automatic cleanup left nothing to present from.

## Decision
- The run's step 8 is a hand-over: the worktree, local `poc/<slug>` branch
  and Docker objects stay, and the app is launched from the worktree and
  left running. The report adds a **Try it** block (URL or entry command,
  how to stop and restart, worktree path) and does not suggest cleanup.
- Cleanup is a separate section that runs only when the user asks. Claude
  suggests it in one line once the user says they have tested or presented
  the POC. It works in a later session: the worktree is found by its
  branch, and the Docker baseline lives at
  `~/.claude/ship-fast-specs/<slug>.docker-baseline.txt`, not in the
  session scratchpad. Uncommitted or unpushed work in the worktree is
  listed and confirmed before anything is removed.

## Consequences
A finished run leaves a worktree and a local branch behind until the user
asks; the session-start hook's leftover report reminds them. A background
app process ends with the session, so the report gives its restart command.
ADR 0021's no-merge, open-PR shape is unchanged.
