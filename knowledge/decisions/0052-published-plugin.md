# ADR 0052: The kit is a published Claude Code plugin (agent-kit)

- **Status:** accepted; extended by 0054 ([ADR 0054](0054-vibe-native-plugin.md): the native Vibe plugin of D3 now exists), 0055 ([ADR 0055](0055-directory-listing.md): directory listing and the /new-project sibling default)
- **Date:** 2026-11-23

## Context
The kit installed only from a clone: `python plugin/install.py` linked the
checkout's `plugin/` folder into the skills directory. Managed work laptops
block that, and strangers find a clone heavy. An installed Claude Code
plugin is a copy of its folder only, so anything outside `plugin/` (the
conventions, the workspace rules, the ADRs) is missing from a marketplace
install.

## Decision
- **Self-contained plugin (D1).** What the kit needs at run time moves
  under `plugin/` (`plugin/conventions/`, `plugin/rules.md`); the kit's own
  history (`knowledge/`, `docs/`) stays at the root, unshipped. Rejected:
  the whole repo as the plugin (every install carries tests, specs, gate
  records and vendored superpowers), and `plugin/` shipped as it is (the
  kit map and rules go quiet).
- **Name (D2).** The plugin and the marketplace are `agent-kit`; the repo
  name stays. A root `.claude-plugin/marketplace.json` lists `./plugin`.
- **Split (D3).** Claude Code now; a native Vibe plugin comes in a later
  spec.
- **Env vars and state paths keep their names (D5).** Every
  `CLAUDE_KIT_*` variable, `~/.claude/claude-kit/`, the context-nudge
  paths, the Docker label `claude-kit.task` and the repo URL stay. Renaming
  them breaks existing setups and nothing checks them.
- **History links become URLs (D6).** Shipped files cannot link relatively
  to unshipped `knowledge/` and `docs/`, so they link to GitHub.
- **Version 1.0.0 (D7).** The rename breaks every `/claude-kit:...`
  invocation, and this is the first published release. Marketplace users
  get updates only when the version changes, so every user-visible change
  keeps bumping it.
- **Plugin root from the kit map (D8).** One rule replaces the hard-coded
  skills-dir fallback, in every install mode.
- **`/new-project` default parent (D9).** Keeps today's behaviour inside a
  kit checkout and never writes into the plugin cache.

## Consequences
- Marketplace users get updates only on a version bump.
- Anything a shipped file needs must live under `plugin/`.
- ADR 0005 (in-place loading) still holds for contributors.
- Vibe, Codex and Cursor users rerun `install.py --agent` after updating
  until a native Vibe plugin exists.
