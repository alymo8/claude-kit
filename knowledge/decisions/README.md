# Decisions

Architecture Decision Records for this repo (the kit itself), following
[the decision-log convention](../../conventions/decision-log.md). New decisions take
the next number; superseded ones are never deleted.

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-whitelist-gitignore-workspace-repo.md) | Workspace prefs repo tracks only whitelisted files | accepted | 2026-07-31 |
| [0002](0002-spec-html-is-local-view.md) | Spec/plan HTML is a local view, never committed | superseded by 0010 | 2026-09-14 |
| [0003](0003-specs-under-docs-superpowers.md) | Specs and plans live under `docs/superpowers/` | accepted | 2026-09-14 |
| [0004](0004-adrs-under-knowledge-decisions.md) | ADRs live under `knowledge/decisions/` | accepted | 2026-09-14 |
| [0005](0005-kit-is-a-skills-dir-plugin.md) | Kit is a skills-dir Claude Code plugin in `plugin/`, installed by junction | accepted | 2026-09-14 |
| [0006](0006-kit-main-gate.md) | Kit `main` gate: CI on every push; PRs for feature work | accepted | 2026-09-14 |
| [0007](0007-hooks-are-python-exit-zero.md) | Hook handlers are Python scripts that always exit 0 | accepted | 2026-09-14 |
| [0008](0008-handoff-is-gitignored-per-branch.md) | Session handoff files are gitignored, per branch, per work tree | accepted | 2026-09-18 |
| [0009](0009-no-service-backed-memory.md) | No service-backed memory in the kit | accepted | 2026-09-18 |
| [0010](0010-spec-html-on-demand-only.md) | Spec/plan HTML is rendered on demand only | accepted | 2026-09-19 |
| [0011](0011-lean-context-favours-quality.md) | Lean context favours quality over tokens when reading code | accepted | 2026-09-25 |
