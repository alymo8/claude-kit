# ADR 0035: Process rules move from personal memory into CLAUDE.md

- **Status:** accepted
- **Date:** 2026-10-13

## Context
Three rules lived only, or only partly, in the kit owner's auto-memory,
which a teammate never sees: clean-up never deletes or suggests deleting a
repo; the kit repo is public, so tracked files name no private repo or
machine username; recurring behaviour goes into an existing flow step first.

## Decision
The three rules become workspace rules in `CLAUDE.md`. The repo-deletion
rule joins the feature clean-up paragraph; the other two go under
"Developing the kit", so they are not injected into project repos.

## Alternatives
Leave them personal: every new contributor would have to learn them by
correction.

## Consequences
Every contributor follows them. The owner's memory copies are removed after
the change merges.
