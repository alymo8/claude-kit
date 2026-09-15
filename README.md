# Workspace preferences

My personal working conventions, skills, and shared tooling for building software
with [Claude Code](https://claude.com/claude-code). This repo is the workspace-level
setup that sits above my individual project repos — it defines *how* I work, not
*what* any one project does.

## What's here

- **[`CLAUDE.md`](CLAUDE.md)** — the workspace instructions Claude Code reads: how we
  work, decision verification, spec/HTML rendering, environment, and file-opening
  conventions.
- **[`conventions/`](conventions/)** — five self-contained playbooks that generalize
  my way of working to any new project:
  - [Knowledge layer](conventions/knowledge-layer.md) — a version-controlled,
    domain-organized knowledge base as the foundation.
  - [Decision log (ADRs)](conventions/decision-log.md) — locked-in decisions as
    numbered, durable records.
  - [Spec-driven development](conventions/spec-driven-development.md) — brainstorm →
    spec → plan → build.
  - [Engineering practices](conventions/engineering-practices.md) — test-first,
    coding standards, and a CI + AI + human review gate.
  - [Project memory file](conventions/project-memory.md) — a checked-in `CLAUDE.md`
    per repo: build/test commands, architecture, conventions, gotchas.
- **[`plugin/`](plugin/)** — a Claude Code plugin: the `supabase-cli` skill, the
  spec → HTML renderer, and two hooks (auto-render specs/plans after edits; report
  leftover worktrees at session start). Install once per machine with
  `plugin\install.ps1` — it junctions `~/.claude/skills/claude-kit` to this folder
  so edits are live.
- **[`knowledge/decisions/`](knowledge/decisions/)** — this repo's own ADRs.
- **[`docs/superpowers/`](docs/superpowers/)** — specs and plans for changes to
  the kit itself.

## Scope

By design this repo tracks **only** the files above. The project folders that also
live under `Github/` are ignored via a whitelist [`.gitignore`](.gitignore), so
nothing project-specific (or any secrets) is ever committed here.

## Developing the kit

```
pip install "markdown~=3.10" pytest ruff     # once
pytest                                         # full suite
pytest tests/test_render_spec.py::test_title_from_h1   # one test
ruff check plugin tests && ruff format plugin tests    # lint + format
```

CI runs the same three commands on Ubuntu and Windows for every push and PR.
Feature-sized changes go through a branch and PR; one-line doc fixes may land on
`main` directly (ADR 0006).
