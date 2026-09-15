# ADR 0001: Workspace prefs repo tracks only whitelisted files

- **Status:** accepted
- **Date:** 2026-07-31

## Context
The workspace directory (`Desktop/Github`) holds both the workspace-level way of
working (`CLAUDE.md`, conventions, tooling) and ~30 independent project checkouts,
some private, some containing `.env` files. The preferences need to be versioned
and shareable; the projects must never be swept into that repo.

## Decision
The workspace root is itself a git repo whose `.gitignore` ignores every top-level
entry (`/*`) and un-ignores an explicit whitelist of preference files and folders.
A secrets guard (`.env*`, `*.local`) applies inside whitelisted folders too.

## Consequences
Nothing project-specific can be committed by accident. The cost: every new
top-level file or folder must be added to the whitelist or it is silently
untracked — tests and reviewers must watch for that.
