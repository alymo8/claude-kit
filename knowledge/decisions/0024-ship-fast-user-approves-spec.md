# ADR 0024: `/ship-fast`: the user reads and approves the spec

- **Status:** accepted
- **Date:** 2026-10-08

## Context
`/ship-fast` (ADR 0021) runs no gate on its spec, and since ADR 0022 the
user's confirmation of the grill summary approves the spec it writes. The
user never sees the written spec before the build starts, so a wrong
paraphrase of the interview reaches the code unnoticed.

## Decision
- Step 0 writes the spec with Status `draft`, opens the `.md` for the user,
  and waits. The user replies "approve" or with changes; changes are applied
  and the spec is opened again. These rounds do not count against the
  interview's 7-question budget. On "approve" the Status becomes `approved`
  and the run continues.
- Confirming the grill summary ends the interview; it no longer approves
  the spec.
- A spec passed by path whose Status is not `approved` gets the same
  approval step; an approved one runs straight on.
- In a non-interactive session, an unapproved spec is a stop rule.
- The user's read is the spec's only review: no `spec-gate` runs.

## Consequences
A POC is built only from a spec the user has read, at the cost of one more
pause before the build. The light path stays gate-free; the user's spec
approval and PR merge are its human checks.
