# ADR 0004: ADRs live under `knowledge/decisions/`

- **Status:** accepted
- **Date:** 2026-09-14

## Context
Adopting repos had split two ways: `knowledge/decisions/` (as the convention
said) and `docs/decisions/`. Decisions are part of what a project *knows* — they
are made against the knowledge base and belong next to it.

## Decision
`knowledge/decisions/` is the fixed location, with a `README.md` index and a
`0000-template.md`. Two older repos that already use `docs/decisions/` keep it
as a grandfathered exception; they are not migrated.

## Consequences
One place to look in every new repo. The exceptions are named in the convention
so nobody "fixes" them later.
