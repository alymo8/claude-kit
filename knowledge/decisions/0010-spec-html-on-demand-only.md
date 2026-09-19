# ADR 0010: Spec/plan HTML is rendered on demand only

- **Status:** accepted
- **Date:** 2026-09-19
- **Supersedes:** ADR 0002 (the "regenerated automatically by the PostToolUse
  hook" part; the "never committed" part stands)

## Context
Auto-rendering after every Write/Edit produced a file per edit that nobody opened,
and the hook could not see edits made through Bash. The reading view is wanted
rarely and deliberately.

## Decision
The `.md` is the only artefact produced by default. `/spec-html [path]` renders and
opens the view when asked. The PostToolUse hook only regenerates the spec index.
The HTML stays gitignored (`docs/superpowers/**/*.html`), as ADR 0002 decided.

## Consequences
No stray HTML; the renderer is exercised only when someone wants to read. Bulk
re-rendering is a manual `render-spec.py` run.
