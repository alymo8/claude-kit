# ADR 0018: `/ship-many` runs independent specs as headless `/ship` children

- **Status:** accepted
- **Date:** 2026-10-01

## Context
`/ship` lands one spec per run, so approved specs that touch different files
still ship one after another. A subagent cannot run a slash command, so
`/ship` cannot simply be delegated to subagents.

## Decision
`/ship-many` gates every listed spec in the user's session, groups specs whose
Scope In paths share no file (`parallel-plan.py specs`; the generated spec
index never counts, same-numbered ADR files do), and runs each wave's specs as
background `claude -p "/claude-kit:ship <spec>"` children with
`--permission-mode auto --permission-prompts none`, at most 3 at once by
default. Children are found afterwards by exact PR title, so `/ship` titles
its PR with the spec's H1 through a title file. Excluded or failing specs never
stop the others; leftovers are reported, not deleted.

## Consequences
Independent specs land in parallel with their own context and cost. Overlap
is strict, so kit specs that all bump `plugin.json` still run in sequence. A
child that needs a permission prompt stops instead of waiting. Up to 9 agents
can run at once (3 children, 3 task subagents each).
