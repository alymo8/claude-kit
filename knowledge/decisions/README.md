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
| [0012](0012-jev-triage-pilot.md) | jev triage pilot is an opt-in third-party judge | moved | 2026-09-28 |
| [0013](0013-ship-never-works-in-local-main.md) | `/ship` never works in or depends on the local `main` checkout | accepted | 2026-09-29 |
| [0014](0014-lean-context-env-switch.md) | Lean context is switched by an env var, on by default | accepted | 2026-09-29 |
| [0015](0015-spec-gate-replaces-full-read.md) | A spec gate replaces the user's full read of a spec | accepted | 2026-09-30 |
| [0016](0016-plan-gate-signs-off-on-new-decisions-only.md) | A plan gate, with sign-off only on decisions the plan adds | accepted | 2026-09-30 |
| [0017](0017-parallel-plan-tasks.md) | Independent plan tasks run as concurrent subagents | accepted | 2026-10-01 |
| [0018](0018-ship-many-headless-children.md) | `/ship-many` runs independent specs as headless `/ship` children | accepted | 2026-10-01 |
| [0019](0019-spec-grill-opt-in.md) | An opt-in grill runs between the design and the spec | accepted | 2026-10-01 |
| [0020](0020-gates-end-with-verification.md) | Gates end with a verification round; blocking is a fixed set of classes | accepted | 2026-10-02 |
| [0021](0021-ship-fast-skips-gates.md) | `/ship-fast` takes a POC spec to a PR with no gates | accepted; amended by 0022 | 2026-10-06 |
| [0022](0022-ship-fast-user-driven-spec.md) | `/ship-fast` interviews the user for the spec and asks product decisions | accepted | 2026-10-07 |
| [0023](0023-ship-fast-cleanup-on-request.md) | `/ship-fast` hands over a running POC; cleanup waits for the user | accepted | 2026-10-07 |
| [0024](0024-ship-fast-user-approves-spec.md) | `/ship-fast`: the user reads and approves the spec | accepted | 2026-10-08 |
| [0025](0025-present-skill-bundled-template.md) | `present` skill builds decks from a bundled template and checks every slide | accepted | 2026-10-08 |
