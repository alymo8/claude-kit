# ADR 0003: Specs and plans live under `docs/superpowers/`

- **Status:** accepted
- **Date:** 2026-09-14

## Context
The written convention said `docs/specs/` and `docs/plans/`, but the
`superpowers:brainstorming` and `superpowers:writing-plans` skills write to
`docs/superpowers/specs/` and `docs/superpowers/plans/` by default, the shared
renderer looked there, and every adopting repo used that path. The convention was
the only thing out of step.

## Decision
`docs/superpowers/specs/` and `docs/superpowers/plans/` are the convention.

## Consequences
Convention, tooling, and practice agree; nothing has to be configured or moved.
The `superpowers` name in the path is a dependency on that plugin's defaults; if
the plugin ever changes them, revisit this ADR rather than diverging silently.
