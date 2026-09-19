# Workspace preferences

An attempt to open source my agentic coding set up, skills, and shared tooling for building software
with [Claude Code](https://claude.com/claude-code). This repo is the workspace-level
setup that sits above my individual project repos — it defines *how* I work, not
*what* any one project does.

## What's here

- **[`CLAUDE.md`](CLAUDE.md)** — the workspace instructions Claude Code reads: how we
  work, decision verification, spec/HTML rendering, environment, and file-opening
  conventions.
- **[`conventions/`](conventions/)** — six self-contained playbooks that generalize
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
  - [Session hygiene](conventions/session-hygiene.md) — short sessions, a
    per-branch handoff file, a context meter, lean exploration.
- **[`plugin/`](plugin/)** — a Claude Code plugin: the `supabase-cli` and
  `lean-context` skills, the spec → HTML renderer, the `token-report.py`
  measurement script, a status line, and five hooks (auto-render specs/plans
  after edits; report leftover worktrees, inject the branch handoff and nudge
  past a context threshold at the right moments; snapshot git state at session
  end). Install once per machine with `plugin\install.ps1` — it junctions
  `~/.claude/skills/claude-kit` to this folder so edits are live, and adds the
  kit's status line to `~/.claude/settings.json` when none is configured. If
  PowerShell refuses to run the script (execution policy), use
  `powershell -ExecutionPolicy Bypass -File plugin\install.ps1`. It also
  provides two commands: `/new-project <name> <node|python>` scaffolds a new
  repo with every convention in place, and `/adopt-conventions <node|python>`
  adds the missing pieces to an existing one. `/handoff` writes the
  per-branch handoff file before you `/clear`. `/ship <spec.md>` takes an
  approved spec all the way to a squash-merged, cleaned-up change on `main`
  without further check-ins (it stops only on red CI after three fixes, a review
  finding that needs a decision, or a blocked merge).
- **[`knowledge/decisions/`](knowledge/decisions/)** — this repo's own ADRs.
- **[`docs/superpowers/`](docs/superpowers/)** — specs and plans for changes to
  the kit itself.

## Scope

By design this repo tracks **only** the files above. The project folders that also
live under `Github/` are ignored via a whitelist [`.gitignore`](.gitignore), so
nothing project-specific (or any secrets) is ever committed here.

## Developing the kit

```
pip install "markdown~=3.10" pytest "ruff~=0.16"       # once
pytest                                                  # full suite
pytest tests/test_render_spec.py::test_title_from_h1    # one test
ruff check plugin tests                                 # lint
ruff format plugin tests                                # format
```

CI runs the same three commands on Ubuntu and Windows for every push and PR.
Feature-sized changes go through a branch and PR; one-line doc fixes may land on
`main` directly (ADR 0006).

## License

[MIT](LICENSE).
