# {{project_name}}

Project memory file: how to build, test, and navigate this repo. Keep it to about a
screen; update it in the same PR that makes it stale. Workspace-wide rules live in
the workspace `CLAUDE.md` one level up.

**Before CI is green:** create the stack manifest with the framework's own init
(see below); the scaffolder deliberately does not.

## Setup / prerequisites

<!-- runtimes and versions; required env var NAMES (never values); services that must be running -->

## Build, run, test

{{stack_commands}}

## Architecture in brief

<!-- where things live, the module/service boundaries, the one or two flows that explain the shape -->

## Conventions

<!-- naming, layering, error handling, migration/codegen steps, commit/branch rules that differ from the workspace defaults -->

## Gotchas

<!-- things that look wrong but are intentional; steps that must run in order; flaky areas; platform quirks -->

## Pointers

- Knowledge base: [`knowledge/`](knowledge/README.md)
- Decisions: [`knowledge/decisions/`](knowledge/decisions/README.md)
- Specs and plans: [`docs/superpowers/`](docs/superpowers/README.md)
