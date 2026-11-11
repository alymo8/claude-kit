# ADR 0045: Merge Danger in PR bodies

- **Status:** accepted
- **Date:** 2026-11-10

## Context
A PR body described what changed but not how risky merging it is. A reviewer
had to infer the entry point, the blast radius and whether the change could be
undone.

## Decision
`/ship` and `/ship-fast` PR bodies, and the project PR template, state the
door (how the change is reached), the blast radius and the smallest visual that
shows the change. A change is one-way by step 3a's irreversible test, the
same test `/ship` already uses to stop on an irreversible decision.
`plugin/references/pr-body.md` holds the shared body text.
Rejected: keeping the PR body as it is.

## Consequences
Each PR carries a short Merge danger section, so a human merging a
`/ship-fast` PR sees the risk first. The bodies are slightly longer.
