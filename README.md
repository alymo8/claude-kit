# Workspace preferences

An attempt to open source my agentic coding set up, skills, and shared tooling for building software
with [Claude Code](https://claude.com/claude-code). This repo is the workspace-level
setup that sits above my individual project repos — it defines *how* I work, not
*what* any one project does.

## What's here

- **[`CLAUDE.md`](CLAUDE.md)** — the workspace instructions Claude Code reads: how we
  work, decision verification, on-demand spec HTML views, environment, and file-opening
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
  `lean-context` skills, the on-demand spec → HTML renderer, the `token-report.py`
  measurement script, a status line, and seven hooks (regenerate the spec/plan
  index after edits and at every stop; report leftover worktrees, inject the
  branch handoff and nudge past a context threshold at the right moments;
  snapshot git state at session end; an opt-in jev triage of each prompt). Install once per machine with `plugin\install.ps1` — it junctions
  `~/.claude/skills/claude-kit` to this folder so edits are live, and adds the
  kit's status line to `~/.claude/settings.json` when none is configured. If
  PowerShell refuses to run the script (execution policy), use
  `powershell -ExecutionPolicy Bypass -File plugin\install.ps1`. It also
  provides two commands: `/new-project <name> <node|python>` scaffolds a new
  repo with every convention in place, and `/adopt-conventions <node|python>`
  adds the missing pieces to an existing one. `/handoff` writes the
  per-branch handoff file before you `/clear`. `/ship <spec.md>` takes an
  approved spec all the way to a squash-merged, cleaned-up change on `main`
  without further check-ins; it stops only on the rules listed in the command
  (red CI after three fixes, a review finding that needs a decision, a refused
  merge, a failed pre-flight). `/spec-html [path]` renders a
  spec or plan (the latest one when no path is given) and opens its HTML view.
- **[`knowledge/decisions/`](knowledge/decisions/)** — this repo's own ADRs.
- **[`docs/superpowers/`](docs/superpowers/)** — specs and plans for changes to
  the kit itself.

## Trying jev (opt-in pilot)

An experiment: [jev](https://typesafe.ai), a fast "System One" judge, scores
each prompt (underspecified? new feature? key decision?) and, in `active`
mode, adds a one-line hint for Claude. It is **off by default**; see
[ADR 0012](knowledge/decisions/0012-jev-triage-pilot.md) and the
[spec](docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md).

```
pip install "typesafe-sdk>=0.7"          # once per machine
setx TYPESAFE_API_KEY <key>              # new terminals pick it up
python plugin/scripts/jev-eval.py replay # 1. judge ~60 past prompts
#    fill label_* in ~/.claude/claude-kit/jev/labels.csv with 1/0
python plugin/scripts/jev-eval.py score  # Replay gate PASS/FAIL
setx CLAUDE_KIT_JEV shadow               # 2. log only, 1-2 weeks
setx CLAUDE_KIT_JEV active               # 3. add hints, 1-2 weeks
python plugin/scripts/jev-eval.py report --since 2026-10-01
setx CLAUDE_KIT_JEV off                  # stop
```

Judgments are logged to `~/.claude/claude-kit/jev/log.jsonl`; prompts go to
TypeSafe only while the flag is `shadow` or `active`.

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
