# Decisions

Architecture Decision Records for this repo (the kit itself), following
[the decision-log convention](../../conventions/decision-log.md). New decisions take
the next number; superseded ones are never deleted.

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-whitelist-gitignore-workspace-repo.md) | Workspace prefs repo tracks only whitelisted files | accepted | 2026-07-31 |
| [0002](0002-spec-html-is-local-view.md) | Spec/plan HTML is a local view, never committed | accepted | 2026-09-14 |
| [0003](0003-specs-under-docs-superpowers.md) | Specs and plans live under `docs/superpowers/` | accepted | 2026-09-14 |
| [0004](0004-adrs-under-knowledge-decisions.md) | ADRs live under `knowledge/decisions/` | accepted | 2026-09-14 |
| [0005](0005-kit-is-a-skills-dir-plugin.md) | Kit is a skills-dir Claude Code plugin in `plugin/`, installed by junction | accepted | 2026-09-14 |
| [0006](0006-kit-main-gate.md) | Kit `main` gate: CI on every push; PRs for feature work | accepted | 2026-09-14 |
| [0007](0007-hooks-are-python-exit-zero.md) | Hook handlers are Python scripts that always exit 0 | accepted | 2026-09-14 |
