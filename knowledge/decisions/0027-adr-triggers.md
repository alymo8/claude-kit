# ADR 0027: ADR triggers: MUST, SHOULD, NOT REQUIRED

- **Status:** accepted
- **Date:** 2026-10-10

## Context
`conventions/decision-log.md` said to record a decision "whenever a choice
is significant and meant to stick". The call was left to judgment, and on
projects other than the kit ADRs stopped being written.

## Decision
- The convention and the scaffold template's `knowledge/decisions/README.md`
  carry the same `## When to write one` section: MUST, SHOULD and NOT
  REQUIRED lists. A NOT REQUIRED match overrides the other two. A test keeps
  the two copies identical.
- The spec gate's rubric gains check 8: a key decision that matches a MUST
  trigger with no ADR in the spec's Scope In is a blocking `open-what`
  finding, which the gate fixes by adding the ADR to the spec. A SHOULD
  match is reported as minor and never added without the user.
- The trigger lists are read from the repo's decisions README, else
  `conventions/decision-log.md`, else `../conventions/decision-log.md`;
  without any of them the check is skipped.

## Consequences
- Specs that hit a MUST trigger carry their ADR, visible in the gate
  record's Findings fixed.
- `/ship-fast` POCs are exempt: they skip the gates (ADR 0024).
- The plan gate does not check ADRs; decisions a plan adds still reach the
  user through the plan gate's sign-off (ADR 0016).
