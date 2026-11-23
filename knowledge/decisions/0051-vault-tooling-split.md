# ADR 0051: The vault tooling lives in second-brain-kit

- **Status:** accepted
- **Date:** 2026-11-23

## Context
The personal-vault tooling (ADR 0040: `/vault-init`, `vault-init.py`,
`vault-pending.py`, the `vault_inject.py` session-start hook, the `ingest`
and `task-prompt` skills, the vault template; ADR 0047: the untrusted
content scanner) is personal-knowledge tooling, not a workspace
convention, and it grew (email and calendar triage, connectors) beyond the
kit's scope. A separate public plugin, second-brain-kit, now holds it.
With both installed, two vault pointers are injected at session start.

## Decision
- The vault tooling lives in the second-brain-kit plugin; claude-kit ships
  none of it and no longer reads `CLAUDE_KIT_VAULT`.
- ADRs 0040 and 0047 stay in claude-kit with status `moved` and their full
  bodies, as history. `moved` rather than `superseded`, as in ADR 0012,
  because the decisions live on in second-brain-kit rather than being
  reversed.
- The knowledge-layer convention keeps the principle (a person's knowledge
  follows the same rules; repos link to vault pages only by name) and names
  second-brain-kit for the tooling.

## Consequences
- One vault pointer at session start instead of two.
- Installing claude-kit alone no longer gives a vault; second-brain-kit is
  installed separately.
- Historical specs, plans and gate records about the vault stay under
  `docs/superpowers/` unchanged.
