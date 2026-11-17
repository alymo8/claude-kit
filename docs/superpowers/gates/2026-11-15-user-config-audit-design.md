# Gate: User-config audit: `audit --user` checks the setup outside any repo

- **Spec:** docs/superpowers/specs/2026-11-15-user-config-audit-design.md
- **Spec SHA-256:** 808f7597738726423f325ec335cb53d29d367c49ee07a2c934129044f2f76a82
- **Verdict:** pass
- **Date:** 2026-11-15
- **Rounds:** 3 discovery + 1 verification

Round 1 reviewed the combined agent-config security spec, which was split
into this spec and `2026-11-15-untrusted-vault-content-design.md` on that
round's too-large finding.

## Key decisions

- The user audit is a `--user` mode of `audit`, reusing `rules.md` and `check-findings.py` unchanged; not a new skill (D1)
- `audit-deep` gets no user mode (D2)
- The report goes to `~/.claude/claude-kit/audit/user-config.md` (folder created if absent), never inside a repo; user mode overrides `rules.md`'s one write folder and repo root (home) itself (D3, Design)
- Neither the inventory nor the audit reads env or header values: key names only, and the settings files and `.claude.json` are read only at cited lines (D4)
- The audit covers settings (permissions, hooks, `statusLine`, `autoMode`), MCP servers, installed and skills-dir plugins with their hooks, skills, scheduled tasks, and user instructions (`~/.claude/CLAUDE.md`, agents, commands, output styles)
- Nothing is frozen; behaviour is checked by a manual run (D5)
- Shipped separately from untrusted vault content (D6)
- One ADR records D1, D3 and D4; minor version bump; the audit stays read-only

## Findings fixed

- round 1 [blocking] Two independent subsystems in one spec: split into this spec and the untrusted-vault-content spec.
- round 1 [blocking] User-mode output contradicts the read-only rule: user mode states that `~/.claude/claude-kit/audit/` replaces `<repo>/docs/audit/` as the one writable folder.
- round 1 [blocking] Inventory misses skills-dir plugins and their hooks: skills entries with `.claude-plugin/plugin.json` are marked `plugin: true` with their hooks; tested.
- round 1 [blocking] "That folder already belongs to the kit" is untrue: D3 reworded.
- round 1 [blocking] D3 and D7 match MUST triggers but the ADR leaves them out: this spec's ADR records D1, D3 and D4 (the env-value decision).
- round 2 [blocking] "Read every file it names" puts secrets back into context: settings files and `.claude.json` are read only at cited lines, never `env`/`headers`; D4 extended.
- round 2 [blocking] Inventory leaves out `statusLine` and `autoMode`: both added, with the `statusLine` script read; tested.
- round 2 [minor] `~/.claude/claude-kit/` already exists: "created if absent".
- round 2 [minor] Criterion 2 only checked user-settings env values: now also every env and header value in `.claude.json`.
- round 3 [blocking] User CLAUDE.md, agents, commands and output styles neither in nor out: added as the `instructions` inventory field, read in full, reported, tested.
- round 3 [minor] Source of "kit version": the `version` in the kit's `plugin.json`.

## Plan questions

- One inventory item per `installed_plugins.json` install entry, carrying `scope`/`projectPath`? Which `enabledPlugins` decides "enabled" for project-scope installs? (Design: Inventory)
- Which method finds an item's `line` in JSON, and what happens on duplicate matches? (Design: Inventory)
- How are files outside the home directory (junction targets, `installPath`) written and cited, given `check-findings.py <home>`? (Design: Inventory)
- Does the inventory read a `hooks` field in a plugin's `plugin.json`, or list such plugins as not read? (Design: Inventory)
- Who resolves a hook command (with `${CLAUDE_PLUGIN_ROOT}`, interpreters, relative paths) to its target script: the inventory or the model? (Design: Audit `--user` mode)
- Does the `--user` branch replace SKILL.md Setup steps 1-5, and which production bar does user mode state? (Design: Audit `--user` mode)
- How is the env/header value search in criterion 2 run without loading values into the model's context (a script that does not echo them)? (Success criteria 2)

## Open

- none
