# Spec-driven development

Work flows from an idea to shipped code through explicit, reviewable stages:
**brainstorm → spec → plan → build.** Thinking is done — and written down — *before*
code, so the hard choices are made deliberately rather than improvised at the
keyboard. The [knowledge layer](knowledge-layer.md) feeds this flow, and the
[decision log](decision-log.md) captures the choices it locks in.

## The stages

1. **Brainstorm.** Explore intent, requirements, and design options before
   committing to an approach. Surface the real problem and the alternatives; land on
   a direction. (Use the `superpowers:brainstorming` skill for creative/feature
   work.)
2. **Spec.** Write a design document that captures *what* is being built and *why*:
   purpose, scope (explicitly including **out of scope**), structure, the decisions
   made during brainstorming, and success criteria. The spec is the contract the
   build is reviewed against.
3. **Plan.** Break the spec into an ordered, checkable implementation plan — the
   concrete steps, in sequence, with review checkpoints. (Use
   `superpowers:writing-plans`.) The plan file must be **self-contained** — see
   [Self-contained plans](#self-contained-plans) below.
4. **Build.** Execute the plan test-first (see [engineering
   practices](engineering-practices.md)), checking off steps and updating the spec
   or adding an ADR if reality diverges from the plan.

For small work these stages compress — a couple of paragraphs of brainstorm notes
and a short spec may be enough — but the *order* holds: decide before you build.

## Where documents live

```
<repo>/
  docs/
    superpowers/
      specs/   # design specs (the "what & why")
      plans/   # implementation plans (the "how & in what order")
```

The `docs/superpowers/` prefix is where the `superpowers:brainstorming` and
`superpowers:writing-plans` skills write by default, and where the shared spec
renderer looks; keeping the convention identical to the tooling means nothing has
to be moved or configured.

- **Specs and plans are dated:** `YYYY-MM-DD-<slug>.md`.
- A spec (and a plan) carries a **Status** and a **Date**, and a spec names its
  scope and success criteria explicitly. Status is one of:
  `draft` → `approved` → `implemented`, or `superseded`. When the work a plan
  describes merges, set the spec and plan to `implemented` in the same PR. When a
  later spec replaces one, mark the old spec `superseded` and link its successor.
- `docs/superpowers/README.md` is a **generated index** of specs and plans (date,
  title, status). The kit's render hook regenerates it on every spec/plan write; do
  not edit it by hand.
- Significant decisions that emerge during spec or plan work are promoted to
  **ADRs** — the spec explains and the ADR locks in.

## Spec anatomy

A good spec answers, in roughly this order:

- **Purpose** — why this work exists.
- **Scope** — what is in, and (just as important) what is deliberately **out**.
- **Structure / design** — the shape of the solution.
- **Decisions** — the choices made and the alternatives rejected, with reasons.
- **Success criteria** — how we will know it is done and correct.

## Self-contained plans

A plan is a **handoff document**: execution may happen in a fresh session, in a
subagent, or on another machine, with none of the conversation that produced it. The
plan file is the only context the executor gets, so it carries everything needed:

- Goal and rationale, plus what "done and correct" means.
- The decisions already made (and alternatives rejected), so they aren't relitigated.
- Concrete paths, file names, commands, and expected output — never "as discussed"
  or other references to a conversation the executor cannot see.
- Prerequisites and setup (installs, env vars, services), since a fresh session
  starts cold.
- The verification criteria to check the work against.
- Ordered, independently checkable steps with review checkpoints.

Links to the spec, ADRs, and knowledge docs give depth, but the plan must be
executable without them. Test: *could a competent stranger execute this with only
the repo and this file?*

## Rendered views

The `.md` is the only source of truth and the only thing produced by default. A
co-located, self-contained HTML rendering (same basename) is available **on demand
only** — `/spec-html [path]` renders and opens it — never generated automatically
when a spec is written. The HTML is a local reading view, not a deliverable: it is
gitignored (`docs/superpowers/**/*.html`) and only the `.md` is tracked. (See the
workspace `CLAUDE.md` for the shared renderer.)

## Definition of done

- The work traces back to a spec; the spec states its scope and success criteria.
- A plan existed, was self-contained enough to execute cold, and its steps were
  followed (or the divergence is recorded).
- Emergent decisions landed as ADRs, not just as code.
