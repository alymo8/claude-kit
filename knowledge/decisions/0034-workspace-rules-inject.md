# ADR 0034: Workspace rules injected outside the kit folder

- **Status:** accepted
- **Date:** 2026-10-13

## Context
Claude Code loads the workspace `CLAUDE.md` only for repos inside the kit
checkout. A contributor who clones project repos elsewhere gets the plugin
and the kit map (ADR 0032) but none of the workspace rules.

## Decision
- A SessionStart hook (`workspace_rules_inject.py`, no matcher) injects the
  workspace `CLAUDE.md` up to its `## Developing the kit` section.
- It is silent when the project dir is the kit root or inside it, and when
  the project is a git worktree of the kit (its git common dir is the kit's
  `.git`), because those sessions load a kit `CLAUDE.md` natively.
- On by default; `CLAUDE_KIT_WORKSPACE_RULES=0` switches it off.

## Alternatives
- An `@` import in `~/.claude/CLAUDE.md`: loads twice inside the kit tree,
  includes the kit-development rules, and edits a personal file.
- Requiring every repo to live under the kit checkout.

## Consequences
About 2k to 2.5k tokens (about 9,000 characters) per session, in repos
outside the kit folder only. There the rules arrive as hook context rather
than as a `CLAUDE.md`. Claude Code truncates hook context above 10,000
characters, so a test caps the injected text at 9,500: growing the workspace
part of `CLAUDE.md` past that means trimming it or splitting the rules.
