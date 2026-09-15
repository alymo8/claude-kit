# ADR 0005: Kit is a skills-dir Claude Code plugin in `plugin/`, installed by junction

- **Status:** accepted
- **Date:** 2026-09-14

## Context
The kit's skill was never loaded by Claude Code because nothing wired it in, and
the rules meant to be enforced (re-render HTML, clean up worktrees) were prose.
Claude Code can load skills, hooks and commands from a plugin. Two delivery
mechanisms exist: a marketplace install, which copies the plugin into a cache;
or a *skills-dir plugin*, a folder under `~/.claude/skills/` with a
`.claude-plugin/plugin.json`, loaded in place.

## Decision
Everything Claude Code loads lives in `plugin/` (manifest, `skills/`, `hooks/`,
`scripts/`). It is installed by a junction `~/.claude/skills/claude-kit ->
plugin/`, created by `plugin/install.ps1`, once per machine.

Rejected: marketplace install (cache copy means edits need reloads or version
bumps, and the kit is edited constantly); repo root as plugin root (the root
contains ~30 ignored project folders, risking a loader scan or a huge copy).

## Consequences
Edits are live; one copy of every file. The layout keeps a marketplace possible
later (`source: "./plugin"`). Each machine needs the one-line install; the
junction is not recorded in git.
