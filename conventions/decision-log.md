# Decision log (ADRs)

Significant, locked-in decisions are recorded as **Architecture Decision Records
(ADRs)** — short, numbered markdown files under `knowledge/decisions/`. The decision
log is where the project's choices leave a durable, reviewable trace, so that six
months later anyone can answer *what we decided, and why* without archaeology.

Record a decision as an ADR whenever a choice is **significant and meant to stick** —
it shapes the architecture, the product boundary, or how the team works. Routine,
easily-reversed choices do not need one.

## How it works

- **One decision per file:** `NNNN-short-slug.md`, numbered sequentially from `0001`.
  `0000-template.md` holds the template.
- **New decisions take the next available number.** Numbers are never reused.
- **Decisions are never deleted.** If a decision changes, add a *new* ADR and mark
  the old one `superseded`, noting which ADR replaces it. The history stays intact.
- **An index table** in `decisions/README.md` lists every ADR: number, title, status.

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
- `decisions/README.md`'s index has a row for it.
- If it replaces an earlier decision, the earlier ADR is marked `superseded` and
  points here.
