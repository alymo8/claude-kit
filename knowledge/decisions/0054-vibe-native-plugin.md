# ADR 0054: Mistral Vibe gets the kit as two native plugins built by the installer

- **Status:** accepted
- **Date:** 2026-11-23

## Context
`python plugin/install.py --agent vibe` linked every kit skill folder into
`~/.agents/skills/` and wrote a managed block into the user's
`~/.vibe/hooks.toml` ([ADR 0050](0050-agent-agnostic-kit.md)). The kit then
had no identity in Vibe: it did not show in `/plugins`, could not be turned
off with `disabled_plugins`, its skills mixed with every other skill under
bare names, and its hooks lived in the user's own file.
[ADR 0052](0052-published-plugin.md) left a native Vibe plugin to a later
spec. Vibe 3.1.3 loads a plugin from `~/.vibe/plugins/<name>/` (a
`plugin.json` with the agent-plugins schema, skills under `skills/`, hooks
under `ai.mistral.vibe/hooks.toml`), namespaces its skills as
`/<plugin>:<name>`, and rejects any file or link that resolves outside the
plugin folder. The format is marked experimental.

## Decision
- **The installer builds a copy (D1).** `install.py --agent vibe` assembles
  the plugin from the checkout and copies it into
  `~/.vibe/plugins/agent-kit/`. Rejected: a second generated copy committed
  to the repo (heavy, can drift), and adding Vibe files to `plugin/` in
  place (the command wrapper skills and superpowers sit outside
  `plugin/skills/`, and moving the wrappers there makes Claude Code list
  every command twice). Links are not an option: Vibe rejects links that
  resolve outside the plugin folder.
- **Superpowers is its own plugin (D2).** The bundled superpowers copy
  becomes a second Vibe plugin named `superpowers`, so its skills keep the
  names the kit's text uses. Rejected: folding it into `agent-kit`, which
  renames every skill to `agent-kit:<name>`.
- **Absolute hook paths (D3).** The build writes `hooks.toml` with the
  absolute path of the copy's runner. Rejected: `${PLUGIN_ROOT}` in the hook
  command, whose expansion and Windows shell are undocumented.
- **Migration (D4).** The installer removes the kit's `hooks.toml` block,
  removes the kit's skill links only when Codex and Cursor do not use them
  (else warns about duplicates), keeps the `AGENTS.md` fallback line, and
  the version becomes 1.1.0. Rejected: leaving the old install in place,
  which runs the kit's hooks twice.
- **Refuse foreign folders (D5).** A `~/.vibe/plugins/agent-kit` or
  `superpowers` folder without the kit's marker stops the install with
  nothing changed. Rejected: replacing it (deletes the user's own work) and
  installing beside it (two same-named plugins at one scope means neither
  loads).

An install-time copy does not reopen ADR 0050 D1's rejection of per-agent
copies. That rejection was about a second copy committed to the repo, which
drifts from the first as soon as one is edited. Here nothing is committed
twice: the copy is built from the checkout at install time, so it cannot
drift from the checkout it was built from; it can only be older, and
rerunning the installer refreshes it.

## Consequences
- Vibe users rerun `install.py --agent vibe` after updating the checkout,
  since Vibe runs a copy.
- In Vibe the skills are `agent-kit:<name>` and `superpowers:<name>`, the
  same names Claude Code uses, and `/ship` is `/agent-kit:ship`.
- Codex and Cursor stay on skill links and user hook files.
- The Vibe plugin format is experimental; a format change may need a
  builder change.
