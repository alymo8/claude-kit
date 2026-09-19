# ADR 0008: Session handoff files are gitignored, per branch, per work tree

- **Status:** accepted
- **Date:** 2026-09-18

## Context
Sessions restart cheaply only if in-flight state carries over. That state is
fast-moving and branch-specific: exactly what the project memory convention keeps
out of `CLAUDE.md`. It could be committed on the feature branch or kept local.

## Decision
The handoff lives at `<work-tree>/.claude/handoffs/<branch>.md` and is
gitignored. `/handoff` writes it; the SessionEnd hook refreshes its State; the
SessionStart hook injects it for seven days. Durable content goes to
`knowledge/`, ADRs or the plan, never only to the handoff.

## Consequences
No PR diff noise and no cleanup step at merge; a removed worktree takes its
handoffs with it. A machine switch mid-feature loses the handoff (the plan and
git history remain). Rejected: committing it on the feature branch. The folder
carries its own `.gitignore` (`*`), written on first use, so the guarantee
holds in repos whose root `.gitignore` predates the template.
