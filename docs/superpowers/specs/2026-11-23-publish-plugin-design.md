# Publish the kit as an installable plugin (agent-kit)

- **Status:** draft
- **Date:** 2026-11-23

## Purpose

Today the kit installs only by cloning this repo and running
`plugin/install.py`, which links `~/.claude/skills/claude-kit` to the
checkout. That is hard to get past a managed work laptop, where the admin
allowlists plugin sources, and it asks strangers to clone a repo of kit
history to use the kit.

This change makes the kit a published plugin:

- **Claude Code:** a marketplace hosted in this repo. A user installs with
  two commands and no clone. A company admin allows the whole kit with one
  marketplace entry in managed settings.
- **Mistral Vibe:** a native Vibe plugin, from the same `plugin/` folder.
- **Rename:** the plugin is renamed from `claude-kit` to `agent-kit`.
  `claude plugin validate` flags the `claude-` prefix as reserved.

The user wants to install the kit on their work machine and, ideally,
have other people install and use it.

Anti-goal: an installed plugin that loads but silently loses the kit map,
the workspace rules or the playbooks they point to. An installed Claude Code
plugin is a copy of `plugin/` only, so whatever the kit needs at run time
must live under `plugin/`.

## Scope

**In:**

1. **Self-contained `plugin/`.**
   - `conventions/` moves to `plugin/conventions/` (new) with `git mv`;
     the root `conventions/` folder is gone.
   - The workspace rules (the root `AGENTS.md` above its
     `## Developing the kit` heading) move to `plugin/rules.md` (new).
     Links in `plugin/rules.md` resolve from `plugin/`, so `conventions/…`
     links keep working there.
   - The root `AGENTS.md` keeps a short header, an `@plugin/rules.md`
     line, and its `## Developing the kit` section. `CLAUDE.md` stays
     `@AGENTS.md`.
   - Links from shipped files (`plugin/rules.md`, `plugin/conventions/`,
     skills, commands, templates) to unshipped kit history
     (`knowledge/`, `docs/`) become absolute GitHub URLs
     (`https://github.com/alymo8/claude-kit/blob/main/<path>`), so they
     work from an installed copy.
   - Every other live link to `conventions/` is updated to
     `plugin/conventions/`: `README.md`, `docs/setup.md`, `knowledge/`
     (ADRs, `knowledge/decisions/README.md`), tests.
2. **Hooks that work from an installed copy.**
   - `plugin/hooks/kit_map_inject.py` lists the playbooks from
     `plugin/conventions/` next to the hook (`Path(__file__)`), in
     whatever folder the plugin was installed to. It no longer requires
     a kit checkout and no longer lists the kit's ADR folder.
   - `plugin/hooks/workspace_rules_inject.py` reads the rules from
     `plugin/rules.md` next to the hook, and keeps today's behaviour,
     shown in the table below.
3. **Rename to `agent-kit`.**
   - `plugin/.claude-plugin/plugin.json` `name` becomes `agent-kit`.
   - Every `claude-kit:<skill>` reference becomes `agent-kit:<skill>`.
     That covers skills, commands, `plugin/rules.md`, the conventions,
     `README.md`, `docs/`, and the generated wrapper skills.
   - User-facing text and log prefixes become `agent-kit`, for example
     `[agent-kit]`, `Kit map (agent-kit)` and `Workspace rules (agent-kit, …)`.
4. **Claude Code marketplace.**
   - `.claude-plugin/marketplace.json` (new) at the repo root: marketplace
     `name` `agent-kit`, `owner.name` `alymo8`, and one plugin entry
     `{ "name": "agent-kit", "source": "./plugin", "description": … }`.
   - The entry has no `version`; `plugin.json` keeps it.
5. **Version** `1.0.0` in `plugin/.claude-plugin/plugin.json` and in the
   Vibe manifest, which must match.
6. **Mistral Vibe plugin.**
   - `plugin/plugin.json` (new) is an Agent Plugins 1.0 manifest:
     - `$schema` `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`;
     - `name` `agent-kit`, `version`, `description`, `license` `MIT`,
       `repository`;
     - `extensions."ai.mistral.vibe"` with `schemaVersion: 1` and
       `displayName` `agent-kit`.
   - The kit's SessionStart and Stop hooks run in Vibe from the plugin,
     calling `plugin/hooks/run.py --agent vibe` as today's user hook does.
   - Each kit command except `ship-many` is available in Vibe as
     `/agent-kit:<command>`, as its generated wrapper skill is today.
   - In Claude Code each command still appears exactly once: no duplicate
     skill with the same name as a command.
   - `plugin/install.py --agent vibe`:
     - links `~/.vibe/plugins/agent-kit` to the checkout's `plugin/`
       folder (a junction on Windows, a symlink elsewhere);
     - removes what the previous Vibe install wrote: the kit block in
       `~/.vibe/hooks.toml` and the kit skill links in
       `~/.agents/skills/` that point into `plugin/skills` or
       `plugin/agent-skills`;
     - keeps linking the bundled superpowers skills
       (`vendor/superpowers/skills/`) into `~/.agents/skills/`, as today.
7. **Claude Code installer and status line.**
   - `plugin/install.py` (Claude, the contributor path) keeps linking the
     checkout in place. When a marketplace-installed `agent-kit` is also
     present it says so and does not link, so two copies never load.
   - A plugin cannot set the status line, so a new
     `/agent-kit:statusline` command (new, `plugin/commands/statusline.md`)
     adds the kit's status line to `~/.claude/settings.json` when none is
     set. The command it writes keeps working after a plugin update,
     whose cache path changes with the version.
8. **Docs.**
   - `README.md` and `docs/setup.md` lead with the marketplace install:
     ```
     /plugin install superpowers@claude-plugins-official
     /plugin marketplace add alymo8/claude-kit
     /plugin install agent-kit@agent-kit
     ```
     followed by the optional `/agent-kit:statusline`.
   - A "For your company admin" subsection gives the managed-settings
     snippet:
     - `strictKnownMarketplaces` entries for
       `anthropics/claude-plugins-official` and `alymo8/claude-kit`, plus
       `{ "source": "skills-dir" }`;
     - `extraKnownMarketplaces` registering `agent-kit`;
     - `enabledPlugins` for `agent-kit@agent-kit` and
       `superpowers@claude-plugins-official`;
     - a link to https://code.claude.com/docs/en/plugins/org.md.
   - The Vibe section gives clone + `python plugin/install.py --agent vibe`.
   - Codex and Cursor stay as today. `install.py` becomes "for contributors
     and for Codex/Cursor".
9. **Tests** for every behaviour above (see Success criteria), with the
   existing tests updated for the moves and the rename.
10. **ADR 0052** (new, `knowledge/decisions/0052-published-plugin.md`) and
    its row in `knowledge/decisions/README.md`.

**Workspace-rules injection (unchanged behaviour, new rules source):**

| Where the session runs | Claude Code | Vibe / Codex / Cursor |
|---|---|---|
| Inside a kit checkout (its root or a child repo) | silent (loaded natively via `CLAUDE.md` → `AGENTS.md` → `@plugin/rules.md`) | inject |
| A git worktree of the kit, wherever it lives | silent | inject |
| Any other repo | inject | inject |

A "kit checkout" is any folder holding both `plugin/rules.md` and
`.claude-plugin/marketplace.json` whose marketplace name is `agent-kit`. The
hook finds it by walking up from the project folder, so it works whether
the plugin itself runs from the checkout or from Claude Code's plugin cache.
Vibe in the kit root now gets the rules injected (row 1), because Vibe does
not expand the `@plugin/rules.md` line.

**Out:**
- Submitting to Anthropic's plugin directory (a later, separate step once
  the marketplace is proven on the user's work machine).
- Renaming the GitHub repo; it stays `alymo8/claude-kit`.
- Renaming the `CLAUDE_KIT_*` environment variables or the on-disk state
  paths (such as `~/.claude/claude-kit/`).
- Codex and Cursor packaging; they keep the `install.py --agent` path.
- Historical specs, plans and gate records under `docs/superpowers/`, and
  their index rows.
- Other repos that mention `claude-kit:` skills (for example
  second-brain-kit); their owners update them.
- The user's auto-memory (updated by capture-learnings, outside this diff).
- Getting the user's employer to allowlist the marketplace.

## Decisions

- **D1 (self-contained plugin):** what the kit needs at run time moves
  under `plugin/`; the kit's own history stays at the root, unshipped.
  Decided by the user. Rejected: making the whole repo the plugin
  (every install carries tests, specs, gate records and vendored
  superpowers) and shipping `plugin/` as is (the kit map and rules go
  quiet).
- **D2 (name):** the plugin and the marketplace are `agent-kit`. Decided by
  the user. The repo name stays.
- **D3 (directory later):** no directory submission now. Decided by the
  user.
- **D4 (env vars and state paths keep their names):** my call. Renaming
  them breaks existing setups and nothing checks them.
- **D5 (history links become URLs):** my call. Shipped files cannot link
  relatively to unshipped `knowledge/` and `docs/`.
- **D6 (version 1.0.0):** my call. The rename breaks every
  `/claude-kit:…` invocation, and this is the first published release.
  Updates reach marketplace users only when the version changes, so every
  user-visible change keeps bumping it, as today.
- **D7 (Vibe keeps the bundled superpowers):** my call. The installer keeps
  linking `vendor/superpowers/skills/` as ADR 0050 D4 set, so Vibe users
  need no extra step. Earlier I proposed asking Vibe users to install
  superpowers themselves; this keeps today's behaviour instead.
- **D8 (Vibe still needs a clone):** Vibe has no marketplace or install
  command, so the plugin is linked from a clone. Cloning the repo straight
  into `~/.vibe/plugins/agent-kit` would put the repo root there, not
  `plugin/`, so the installer's link is the supported path.
- **D9 (nothing frozen):** the rename and moves touch most tests, so no
  evaluator is frozen.

## Design: ADR 0052, the kit is a published plugin

Template fields:
- Status `accepted`, Date 2026-11-23.
- Context: the kit installed only from a clone, which managed work laptops
  block and strangers find heavy; an installed Claude Code plugin is a copy
  of its folder only.
- Decision: D1 to D8 above.
- Consequences:
  - Marketplace users get updates only on a version bump.
  - Anything a shipped file needs must live under `plugin/`.
  - ADR 0005 (in-place loading) still holds for contributors.
  - ADR 0050's Vibe install changes from user hook and skill links to a
    plugin link.

## Success criteria

1. `claude plugin validate ./plugin --strict` and `claude plugin validate .`
   (repo root) both exit 0.
2. `pytest` passes and `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean. New tests show:
   - `.claude-plugin/marketplace.json` and `plugin/plugin.json` are valid
     (fields above, both versions `1.0.0`, `plugin.json` versions match);
   - from a copy of `plugin/` placed in a temp folder outside any kit
     checkout, the kit-map hook lists every playbook inside that copy and
     the workspace-rules hook injects `plugin/rules.md` in an unrelated
     repo;
   - the workspace-rules table above holds for each row and both agent
     columns;
   - no file under `plugin/` has a relative link that resolves outside
     `plugin/`, and no live file links to the old root `conventions/`;
   - `install.py --agent vibe` with a temp `--home` creates
     `.vibe/plugins/agent-kit`, removes an old kit `hooks.toml` block and old
     kit skill links, and links the vendored superpowers skills;
   - no wrapper skill duplicates a Claude Code command name.
3. Live Claude Code check, in an isolated config dir
   (`CLAUDE_CONFIG_DIR` set to a temp folder):
   - `claude plugin marketplace add <worktree>` and
     `claude plugin install agent-kit@agent-kit` succeed;
   - running each SessionStart command from `hooks.json` against the cached
     copy (with `CLAUDE_PLUGIN_ROOT` set to it) prints the kit map with
     paths inside the cache, and prints the workspace rules for a temp repo
     outside any kit checkout.
4. Live Vibe check: after `python plugin/install.py --agent vibe`,
   `vibe -p` in a temp git repo confirms that the context holds the kit map
   naming `~/.vibe/plugins/agent-kit` paths and the workspace rules, and
   that `/agent-kit:handoff` is an available skill. If Vibe cannot
   authenticate on this machine, the check is reported as not run, with
   the reason.
5. `git grep -n "claude-kit:"` lists only historical files under
   `docs/superpowers/`, ADR bodies and `knowledge/` history, and the
   GitHub repo URL `alymo8/claude-kit`; no live skill reference.
6. Privacy: `git diff main` grepped for the machine username and every
   non-public repo name in the user's auto-memory index prints nothing.
7. A PR is open against `main` for the user to merge (`gh pr view` shows
   it open).

## Verification

Run the commands in criteria 1, 2, 5 and 6 and paste their output into the
PR's test plan. Run checks 3 and 4 by hand and record what each printed,
or why it could not run.
