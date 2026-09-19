# ADR 0002: Spec/plan HTML is a local view, never committed

- **Status:** superseded by [ADR 0010](0010-spec-html-on-demand-only.md) (auto-render part; the HTML is still never committed)
- **Date:** 2026-09-14

## Context
Specs and plans are Markdown; a co-located HTML rendering exists so they can be
read comfortably in a browser (including RTL Arabic content). Committing the HTML
doubled every doc change, produced noisy diffs, and drifted from the `.md` in
three of four repos.

## Decision
The `.md` is the only source of truth and the only tracked file. Every repo
gitignores `docs/superpowers/**/*.html`. The HTML is regenerated locally by the
shared renderer, automatically via the kit's PostToolUse hook.

## Consequences
Clean diffs and no drift to police. Anyone without the kit sees only Markdown,
which is fine — the HTML was always a convenience.
