# ADR 0022: `/ship-fast` interviews the user for the spec and asks product decisions

- **Status:** accepted; amended by 0024 ([ADR 0024](0024-ship-fast-user-approves-spec.md): the grill summary no longer approves the spec)
- **Date:** 2026-10-07

## Context
`/ship-fast` (ADR 0021) is run live in front of clients to show how a POC
is built. It started from an existing spec, assumed "how" choices and
listed them, and ended the run with a handoff on an unsettled product
decision. In a client session that hides who decides what the product
does, and breaks the flow.

## Decision
- Without a spec path, `/ship-fast` writes the spec with the user: a
  `superpowers:brainstorming` design (approaches and one full design, no
  clarifying questions), then a `claude-kit:grill` round limited to product
  areas. Step 0 asks at most 7 questions; product choices beyond that are
  written into the spec as "assumed (not asked)". The grill confirmation is
  the spec's approval; no gate runs.
- After the task list, a Decisions round asks at most 3 product and at
  most 3 engineering questions that the task split exposed, plus every
  risky engineering choice (deleting or migrating data, real credentials or
  paid services, interfaces outside the POC). Answers go in the task list's
  `## Decisions`, which parallel subagents follow.
- A product or risky choice that surfaces later is asked inline; the run
  waits and does not end. A non-interactive run takes recommended answers
  and stops only on a risky choice (or on step 0).
- One progress line starts each step. The command never deletes or
  suggests deleting a repository.

## Consequences
The user, not the model, decides what the POC does, visibly, at the cost
of a short interview and one pre-build round. An empty argument no longer
picks the newest spec; it starts the interview. ADR 0021's no-gates,
open-PR, user-merges shape is unchanged; its "stop and ask" rule for
unsettled decisions is replaced by inline questions.
