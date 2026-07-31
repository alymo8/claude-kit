# Workspace preferences

My personal working conventions, skills, and shared tooling for building software
with [Claude Code](https://claude.com/claude-code). This repo is the workspace-level
setup that sits above my individual project repos — it defines *how* I work, not
*what* any one project does.

## What's here

- **[`CLAUDE.md`](CLAUDE.md)** — the workspace instructions Claude Code reads: how we
  work, decision verification, spec/HTML rendering, environment, and file-opening
  conventions.
- **[`conventions/`](conventions/)** — four self-contained playbooks that generalize
  my way of working to any new project:
  - [Knowledge layer](conventions/knowledge-layer.md) — a version-controlled,
    domain-organized knowledge base as the foundation.
  - [Decision log (ADRs)](conventions/decision-log.md) — locked-in decisions as
    numbered, durable records.
  - [Spec-driven development](conventions/spec-driven-development.md) — brainstorm →
    spec → plan → build.
  - [Engineering practices](conventions/engineering-practices.md) — test-first,
    coding standards, and a CI + AI + human review gate.
- **[`skills/`](skills/)** — custom Claude Code skills.
- **[`scripts/`](scripts/)** — shared tooling (e.g. the spec → HTML renderer).

## Scope

By design this repo tracks **only** the files above. The project folders that also
live under `Github/` are ignored via a whitelist [`.gitignore`](.gitignore), so
nothing project-specific (or any secrets) is ever committed here.
