# Decision log (ADRs)

Significant, locked-in decisions are recorded as **Architecture Decision Records
(ADRs)** — short, numbered markdown files under `knowledge/decisions/`. The decision
log is where the project's choices leave a durable, reviewable trace, so that six
months later anyone can answer *what we decided, and why* without archaeology.

## When to write one

**MUST** write an ADR when a decision:

- adopts, replaces or drops a framework, language, datastore, hosting
  platform, or external service or API the code depends on;
- changes an interface, data schema, or data retention that code or people
  outside the change rely on;
- chooses an authentication, authorization, security or privacy approach;
- changes how work is done in the repo: a workflow, a gate, a required CI
  check, or a convention;
- reverses or narrows an accepted ADR (write a new ADR and mark the old one
  `superseded`).

**SHOULD** write an ADR when a decision:

- picks one of several viable options and the rejected one was seriously
  considered, so someone could reasonably propose it again;
- is a deliberate workaround that looks wrong without its reason;
- departs from a workspace convention for this repo only.

**NOT REQUIRED:**

- choices that follow an existing ADR, convention or approved spec
  without changing it;
- internal details that are easy to reverse (names, file layout inside a
  module, private helpers);
- bug fixes and dependency version bumps;
- throwaway or `/ship-fast` POC repos, unless the POC is kept.

A decision that matches a NOT REQUIRED item needs no ADR, even if it also
matches a MUST or SHOULD trigger.

## How it works

- **One decision per file:** `NNNN-short-slug.md`, numbered sequentially from `0001`.
  `0000-template.md` holds the template.
- **New decisions take the next available number.** Numbers are never reused.
- **Decisions are never deleted.** If a decision changes, add a *new* ADR and mark
  the old one `superseded`, noting which ADR replaces it. The history stays intact.
- **An index table** in `knowledge/decisions/README.md` lists every ADR: number, title,
  status.
- **The location is fixed at `knowledge/decisions/`** — not `docs/decisions/` or
  `docs/adr/`. Decisions are part of what the project *knows*, so they live in the
  knowledge layer next to the docs they were made against. Repos that adopted
  ADRs before this was fixed (two older repos use `docs/decisions/`) stay where
  they are as a grandfathered exception.

## Template

Each ADR is deliberately short — the operational detail belongs in a knowledge or
practice doc; the ADR captures the decision itself.

```markdown
# ADR NNNN: <Title>

- **Status:** proposed | accepted | superseded
- **Date:** YYYY-MM-DD

## Context
<the forces at play, the situation forcing a decision>

## Decision
<the choice made>

## Consequences
<tradeoffs — what this enables and what it costs>
```

- **Status** is one of `proposed` | `accepted` | `superseded`.
- **Cross-reference** related ADRs and knowledge docs rather than duplicating their
  content.

## Definition of done

- The decision is one numbered file following the template, with a real Context /
  Decision / Consequences — not a bare title.
- `knowledge/decisions/README.md`'s index has a row for it.
- If it replaces an earlier decision, the earlier ADR is marked `superseded` and
  points here.
