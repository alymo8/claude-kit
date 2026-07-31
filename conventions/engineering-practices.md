# Engineering practices

How code is written, tested, and reviewed. Three practices — test-first
development, coding standards, and code review — set a consistent quality floor for
every project. They are decided up front so quality is designed in, not retrofitted,
and each is durable enough to record as an [ADR](decision-log.md) when a project
adopts it.

## PR lifecycle end-to-end

Every change to `main` travels the same path:

```
branch → test-first → CI (lint / type-check / test) → AI review → human review → merge
```

`main` is protected: changes land through a pull request that clears the gates
below.

## 1. Test-first development

Test-first is the **default and expected** practice: write the test, watch it fail,
then implement. Regression safety is a core need, not a nicety — it is what makes it
safe to ship optimizations and refactors with confidence.

Named carve-outs where test-first is relaxed:

- **Exploratory spikes** — thrown away, or redone test-first before merge.
- **Pure configuration / declarative data.**
- **Generated code.**

Regardless of the order code was written in, **behavior must be covered by tests at
merge.** (Use the `superpowers:test-driven-development` skill.)

## 2. Coding standards

Language-agnostic principles that hold whatever the stack:

- Small, single-purpose units with clear interfaces.
- Readable over clever.
- Consistent formatting enforced by an **automated formatter** — no hand-formatting
  debates.
- No dead or commented-out code.
- Meaningful, intention-revealing names.

Concrete tool choices (formatter, linter, type-checker, and their configs) are
pinned per project once its stack is known — and that choice is itself worth an ADR.

## 3. Code review

Every change to `main` clears three gates before merge:

1. **CI gates (blocking):** lint, type-check, and the full test suite pass.
2. **AI review:** an automated review runs on the PR (e.g. Claude Code
   `/code-review`), surfacing correctness and quality findings.
3. **Human approval:** at least one human approves.

Projects with quality-sensitive or performance-sensitive code add their own gate —
e.g. an eval or benchmark gate — on top of these three.

This raises merge friction deliberately, in exchange for a consistent quality floor
and a second (AI) set of eyes on every change. It requires branch protection and CI
wiring, set up when the code phase begins.

## Definition of done

- Behavior is covered by tests at merge (test-first, or the divergence is a named
  carve-out).
- Formatting is tool-enforced; no dead code; names reveal intent.
- The PR passed CI, an AI review, and a human approval before landing on `main`.
