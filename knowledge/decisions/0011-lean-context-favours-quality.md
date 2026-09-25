# ADR 0011: Lean context favours quality over tokens when reading code

- **Status:** accepted
- **Date:** 2026-09-25
- **Refines:** the 2026-09-18 session-hygiene design
  (`docs/superpowers/specs/2026-09-18-session-hygiene-design.md`, lean-context
  rules 1 to 3)

## Context
The first `lean-context` skill told Claude to read ranges of any file over about
200 lines, to cap search output with `head`, and to send broad questions to an
Explore subagent. The measurement behind it showed same-file re-reads were rare
(7 in 67 sessions): whole-file reads were used, then carried for hundreds of
turns. The restart cap (`/handoff`, then `/clear`, from the nudge) already limits
how long that output is carried, and was simulated at 42 to 65% fewer input
tokens. Narrow reading on top of it saved tokens the cap mostly saves anyway, at
a quality cost nothing measured: edits made from partial reads, refactors missing
matches that `head` dropped without saying so, and reasoning from a subagent's
summary. It also contradicted the same design's own rule that hooks must not hide
output because "quality risk from hidden output was judged worse than the tokens
it would save".

## Decision
- Read a file in full before editing, debugging or reviewing it. For files only
  consulted, no size threshold: judgment, with ranges for large generated,
  vendored or data files.
- Count matches before capping search output; never cap when the task needs every
  occurrence, and say so when output is capped.
- Explore subagents only locate code (`file:line` pointers); code that will be
  reasoned about or changed is read in the main thread.
- Logs: find the first failure, not only the tail.
- The skill's trigger is narrowed to exploring unfamiliar code and long command
  output, not reading files in general.

## Consequences
Per-session context grows somewhat when files are read in full; the restart cap
remains the main cost control. The two-week outcome check in the session-hygiene
spec still measures cost only; judging the quality side needs a with/without
comparison on real tasks, which has not been run.
