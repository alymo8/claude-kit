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

   With the kit's opt-in grill on (`CLAUDE_KIT_GRILL=1`), the
   `claude-kit:grill` skill then interviews you on the agreed design and a
   coverage checklist (`plugin/skills/grill/coverage.md`) before the spec is
   written.
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
      gates/   # spec gate records (verdict + spec hash)
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
  title, status). The kit's spec-index hook regenerates it after every spec/plan
  edit and at every stop; do not edit it by hand.
- Significant decisions that emerge during spec or plan work are promoted to
  **ADRs** — the spec explains and the ADR locks in.

## Spec anatomy

A good spec answers, in roughly this order:

- **Purpose** — why this work exists.
- **Scope** — what is in, and (just as important) what is deliberately **out**.
- **Structure / design** — the shape of the solution.
- **Decisions** — the choices made and the alternatives rejected, with reasons.
- **Success criteria** — how we will know it is done and correct.
- **Coverage** (required when `CLAUDE_KIT_GRILL=1`, for specs dated
  2026-10-01 or later) — one `- **<Area>:**` bullet per area in
  `plugin/skills/grill/coverage.md`, saying where the spec addresses it or
  `N/A` with the reason. `spec-lint.py` rule `L9-coverage` checks it
  ([ADR 0019](../knowledge/decisions/0019-spec-grill-opt-in.md)).

## Spec gate

Every spec passes the kit's spec gate (`claude-kit:spec-gate`) before review.
The gate lints the spec with `plugin/scripts/spec-lint.py`, then runs up to
three discovery rounds of a fresh-context reviewer that tries to plan the
work from the spec alone. A finding is `[blocking]` only in one of six
classes (wrong-build, contradiction, false-claim, uncheckable, open-what,
too-large); a "how" question the plan can settle is a `[plan]` finding, which
is not fixed in the spec but listed under `## Plan questions` in the gate
record for the plan to answer. When the last discovery round's blocking
findings were fixed, up to two verification rounds check only those fixes
and the diff they made. The user then confirms a short verdict and the key
decisions rather than reading the whole spec
([ADR 0015](../knowledge/decisions/0015-spec-gate-replaces-full-read.md),
[ADR 0020](../knowledge/decisions/0020-gates-end-with-verification.md)).

The linter requires, outside code blocks:

- `- **Status:**` and `- **Date:** YYYY-MM-DD` bullets.
- `## Purpose`, `## Scope`, `## Design` (or `## Structure`), `## Decisions`
  and `## Success criteria` sections.
- An `**Out:**` list (or `**Out (later specs):**`) inside Scope, or an
  `## Out of scope` section.
- No TBD, TODO or FIXME (upper case) or "as discussed" placeholders, and no
  empty sections.
- A way to verify each success criterion (a command, test, output or manual
  check).
- Every backticked repo path in Scope's In list (the files the spec changes)
  exists, or is marked `(new)` where introduced.

The gate writes `docs/superpowers/gates/<spec file name>` with the verdict and
the spec's hash (Status line excluded). When the record is missing, failed or
stale, `/ship` runs the gate itself, and stops if the gate fails.

## Plan gate

Every plan passes the kit's plan gate (`claude-kit:plan-gate`) before it is
executed. The gate lints the plan with `plugin/scripts/spec-lint.py` (plan
rules apply to files in a `plans` folder), then runs up to three discovery
rounds of a fresh-context reviewer that maps every spec item to a task, tries
to execute each task cold, checks task order and code claims, and checks
that the plan answers the spec gate record's Plan questions
([ADR 0016](../knowledge/decisions/0016-plan-gate-signs-off-on-new-decisions-only.md)).
When the last discovery round's blocking findings were fixed, up to two
verification rounds check only those fixes
([ADR 0020](../knowledge/decisions/0020-gates-end-with-verification.md)).

The linter requires, outside code blocks:

- `- **Status:**` and `- **Date:** YYYY-MM-DD` bullets.
- `**Goal:**` and `**Spec:**` lines before the first task; `**Spec:**` holds
  one backticked path to a spec with a passing spec gate record.
- `### Task N:` headings numbered 1, 2, 3 in order.
- In each task: a `**Files:**` line; a step that runs a command (`Run:` with
  a backticked command, or a command fence) and states its output (a later
  `Expected:`, or `→ result` on the `Run:` line); and a commit (a step whose
  bullet line says "commit", or a `git commit` command). A task whose Files
  line says `none` needs no commit.
- No TBD, TODO or FIXME (upper case) or "as discussed" placeholders, and no
  empty sections.
- Every `- Modify:` path exists, or a `- Create:` or `- Test:` bullet of the
  same or an earlier task names it. Paths inside parentheses are notes and
  are not checked.

There are three verdicts. `pass`: the plan goes straight to execution and
the user sees one line. `pass-with-decisions`: the plan makes choices the
spec did not settle, and the user approves that list in one line. `fail`:
the open items go to the user as questions. The gate writes
`docs/superpowers/gates/plans/<plan file name>` with both the plan's hash
(Status line and checkbox ticks excluded) and its spec's hash, so editing
either makes the record stale. Under `/ship`, anything but `pass` stops the
run.

## Parallel plan tasks

A task may carry one `**Depends on:**` line under its `**Files:**` block:
`none`, or the earlier tasks whose results it uses (`Task 1, Task 3`). A task
without the line runs after every earlier task, so plans without these lines
run exactly as before. `plugin/scripts/parallel-plan.py waves` groups tasks
into waves: tasks in a wave share no file (from their Create, Modify and Test
bullets) and depend on no task in the same wave. Under `/ship`, a wave with
more than one task runs through `claude-kit:parallel-tasks`: one subagent and
git worktree per task, merged back in task order
([ADR 0017](../knowledge/decisions/0017-parallel-plan-tasks.md)). The plan
gate checks the line with rule `P10-depends`.

## Fast path for POCs

`/ship-fast <spec.md>` is the ungated path for a proof of concept of about
an hour: it skips the spec and plan gates, writes a short task list instead
of a full plan, and ends at an open pull request with green CI for the user
to review and merge
([ADR 0021](../knowledge/decisions/0021-ship-fast-skips-gates.md)).

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
