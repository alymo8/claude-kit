# ADR 0014: Lean context is switched by an env var, on by default

- **Status:** accepted
- **Date:** 2026-09-29

## Context
The token-discipline rule lived as a section of the workspace `CLAUDE.md`, so the
only way to turn it off was to comment the section out, an uncommitted edit to a
tracked file. Even then the `lean-context` skill stayed model-invocable through
its own description, so it was never fully off.

## Decision
- The rule moves out of `CLAUDE.md` into a SessionStart hook,
  `plugin/hooks/lean_context_inject.py`, which injects it as additional context.
- `CLAUDE_KIT_LEAN_CONTEXT=0` (under `env` in `~/.claude/settings.json`) turns the
  hook off. Unset or any other value means on, so the kit's default is unchanged.
- The skill itself is switched off with a `Skill(claude-kit:lean-context)`
  permission deny in the same settings file; frontmatter cannot depend on an env
  var, and `disable-model-invocation` would change the default for everyone.

## Consequences
Switching is a per-machine settings change, effective from the next session. It
takes two entries (env var and deny) to be fully off.
