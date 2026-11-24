# Install the kit in Mistral Vibe as a native plugin

- **Status:** approved
- **Date:** 2026-11-23

## Purpose

ADR 0052 published the kit to Claude Code as the `agent-kit` plugin and left
a native Mistral Vibe plugin to a later spec ("spec B"). This is that spec.

Today `python plugin/install.py --agent vibe` links every kit skill folder
into `~/.agents/skills/` and writes a managed block into the user's
`~/.vibe/hooks.toml`. The kit then has no identity in Vibe: it does not show
in `/plugins`, cannot be turned off with `disabled_plugins`, its skills mix
with every other skill under bare names, and its hooks live in the user's own
file.

This change makes the same command install two native Vibe plugins,
`agent-kit` and `superpowers`, under `~/.vibe/plugins/`. Vibe then lists
them in `/plugins`, namespaces their skills (`/agent-kit:ship`,
`/superpowers:brainstorming`, the same names Claude Code uses) and runs the
kit's hooks from the plugin.

Anti-goal: a plugin that loads but silently loses what the hook-and-link
install gives today (the kit map, the workspace rules, the tool mapping, the
handoff injection, the Stop-time spec index), or that leaves the old install
in place so Vibe runs the kit's hooks twice.

### What Vibe offers (checked 2026-11-23, Vibe 3.1.3 docs)

- A plugin is a folder in `~/.vibe/plugins/<name>/` (user scope) holding a
  `plugin.json` whose `$schema` is exactly
  `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`. The folder
  name and `name` field are lowercase letters, digits, `.` and `-`.
- Vibe-only parts sit under `ai.mistral.vibe/` and load only when the
  manifest has `"extensions": {"ai.mistral.vibe": {"schemaVersion": 1}}`.
- Skills load only from `skills/<name>/SKILL.md`, whose `name` matches the
  folder; user-invocable skills become `/<plugin>:<name>`.
- Hooks load from `ai.mistral.vibe/hooks.toml` with the same `[[hooks]]`
  fields as a user `hooks.toml` (`name`, `type`, `command`, `match`,
  `timeout`). Context reaches the model only through
  `hook_specific_output.additional_context` on `session_start`, which
  `plugin/hooks/run.py --agent vibe` already prints.
- A file or link that resolves outside the plugin folder is rejected.
- There is no marketplace and no install command: copying the folder is the
  install. Sessions pin plugin content at start; `/reload-plugins` re-reads.
- Two plugins of the same name at the same scope: neither loads.
- The plugin format is marked experimental.
- Whether `${PLUGIN_ROOT}` expands inside a hook `command`, and which shell
  runs it on Windows (Git Bash or PowerShell), is not documented.

## Scope

**In:**

- `plugin/vibe_plugin.py` (new): builds the two Vibe plugin folders.
- `plugin/install.py` and `plugin/install.ps1`: `--agent vibe` installs the plugins and removes the old install.
- `plugin/references/agent-tools.md`: Vibe skill and command names.
- `plugin/.claude-plugin/plugin.json`: version 1.1.0.
- `docs/setup.md`, `README.md`, `AGENTS.md`: docs.
- `knowledge/decisions/0053-vibe-native-plugin.md` (new), `knowledge/decisions/README.md`, `knowledge/decisions/0052-published-plugin.md`, `knowledge/decisions/0050-agent-agnostic-kit.md`: ADR.
- `tests/test_install.py`, `tests/test_plugin_manifest.py` (version), and `tests/test_vibe_plugin.py` (new).

**Out:**

- A Vibe marketplace or install-from-URL path (Vibe has none).
- Project-scope installs (`.vibe/plugins/` in a repo).
- Vibe `knowledge/` folders for the conventions (the kit map already gives
  their paths).
- Codex's own plugin format; Codex and Cursor keep the link-and-hook install.
- Moving project repos to `AGENTS.md` (ADR 0050 D8).

## Design

1. **Build step.** A new module `plugin/vibe_plugin.py` (imported by
   `install.py`, runnable on its own as
   `python plugin/vibe_plugin.py --out DIR [--python CMD]`) builds the two
   plugin folders from the checkout:
   - **`agent-kit/`**
     - a copy of `plugin/` without `.claude-plugin/`, `agent-skills/`,
       `install.py`, `install.ps1`, `vibe_plugin.py`, `__pycache__/` and
       `*.pyc`;
     - `skills/` holds `plugin/skills/*` plus `plugin/agent-skills/*` (the
       seven command wrapper skills); a name in both is a build error;
     - `plugin.json`: the `$schema` above, `name` `agent-kit`, and `version`,
       `description`, `author`, `license` taken from
       `plugin/.claude-plugin/plugin.json`, plus `repository`
       `https://github.com/alymo8/claude-kit` and
       `"extensions": {"ai.mistral.vibe": {"schemaVersion": 1, "displayName": "agent-kit"}}`;
     - `ai.mistral.vibe/hooks.toml` with two hooks, the same two the user
       block holds today, but naming the copy's own runner by absolute path:
       `agent-kit-session-start` (`type = "session_start"`, command
       `<python> "<out>/agent-kit/hooks/run.py" --agent vibe --event SessionStart`)
       and `agent-kit-stop` (`type = "post_agent"`, `match = "main"`, the
       same command with `--event Stop`). The path is POSIX-style and quoted
       as `vibe_hooks` quotes it today.
   - **`superpowers/`**
     - `skills/` is a copy of `vendor/superpowers/skills/*`, plus `LICENSE`
       and `VERSION` from `vendor/superpowers/`;
     - `plugin.json`: the `$schema`, `name` `superpowers`, `version` read
       from `vendor/superpowers/VERSION`, `license` `MIT`, `repository` the
       source URL in `VERSION`, a description saying it is the copy bundled
       by agent-kit, and the `ai.mistral.vibe` extension with
       `schemaVersion` 1 (no hooks).
   - Both folders contain plain files only (no links) and a marker file
     `.agent-kit-build` (one line: the kit version) that says the kit wrote
     them.
   - The build writes each folder to a staging folder next to the output
     folder but outside it (for `~/.vibe/plugins/` that is
     `~/.vibe/.agent-kit-staging/`, so Vibe never sees two plugins of one
     name) and swaps it in, so a failed build leaves the previous copy
     intact. The staging folder is removed on success and on failure, and a
     stale one from an earlier crash is removed first.
2. **`install.py --agent vibe`** (and `install.ps1 -Agent vibe`) replaces
   what it does today with:
   1. Build both plugins into `<home>/.vibe/plugins/`.
      - A target folder that exists without `.agent-kit-build` is someone
        else's: the installer prints an error naming it, changes nothing at
        all, and exits 1.
      - A folder with the marker is replaced. A rerun on an unchanged
        checkout leaves every file the build writes byte-identical.
   2. Remove the kit's managed block (current and legacy `claude-kit`
      markers) from `<home>/.vibe/hooks.toml`, keeping everything else. A
      file left empty by that is deleted.
   3. Remove the kit's skill links from `<home>/.agents/skills/` (links
      that point into the three kit skill roots) **only when neither
      `<home>/.codex/hooks.json` nor `<home>/.cursor/hooks.json` holds a kit
      hook command** (`is_kit_command`). Otherwise keep them and print a
      warning that Vibe will list the kit's skills twice (bare and
      `agent-kit:`-prefixed) until Codex and Cursor stop using them.
   4. Keep the fallback line in `<home>/.vibe/AGENTS.md`, rewritten to name
      the copy's runner (`<home>/.vibe/plugins/agent-kit/hooks/run.py`).
   5. Print `Next: start a new Vibe session (or run /reload-plugins).`
   - `--skills-dir` keeps its meaning for Codex and Cursor; for Vibe it only
     names where step 3 looks for old links.
   - Damaged markers in `hooks.toml` or `AGENTS.md` stop the install with
     nothing changed, as today.
   - Codex and Cursor installs are unchanged.
3. **Tool mapping** (`plugin/references/agent-tools.md`): under "Skill
   names", add that in Vibe the kit's skills are the plugin skills
   `agent-kit:<name>` and `superpowers:<name>`, so Claude's names work as
   written; under "Slash commands", that in Vibe `/ship` is
   `/agent-kit:ship`. Other agents' wording is unchanged.
4. **Version.** `plugin/.claude-plugin/plugin.json` is bumped to `1.1.0`;
   the `agent-kit` Vibe manifest takes its version from it, and the
   `superpowers` manifest takes its version from `vendor/superpowers/VERSION`.
   `.claude-plugin/marketplace.json` carries no version and is unchanged.
5. **Docs.**
   - `docs/setup.md` "Using the kit with Vibe, Codex or Cursor": Vibe now
     gets two native plugins; what the installer writes and removes; rerun
     after updating the checkout (the copy does not follow edits); turn the
     kit off with `disabled_plugins = ["agent-kit"]` in
     `~/.vibe/config.toml`.
   - `README.md`: both Vibe passages, the "Contributors, and Vibe, Codex
     and Cursor users, install from a checkout" sentence and the
     agents-section paragraph on `~/.agents/skills/`, say that Vibe gets the
     two native plugins under `~/.vibe/plugins/` instead of skill links.
   - `docs/setup.md` also notes that a later Codex or Cursor install
     re-creates the skill links Vibe also reads, so Vibe then lists the
     kit's skills twice.
   - `plugin/install.ps1` help (`.DESCRIPTION`, `.PARAMETER SkillsDir`):
     `-Agent vibe` installs the two plugins under `<Home>\.vibe\plugins`,
     and for Vibe `-SkillsDir` only names where old links are removed.
   - `docs/setup.md`'s sentence telling Vibe users to rerun the installer
     "until a native Vibe plugin exists" is reworded for Vibe (Codex and
     Cursor keep rerunning after updates).
   - Contributors (root `AGENTS.md`, "Developing the kit"): Vibe runs a
     copy, so rerun `python plugin/install.py --agent vibe` (or
     `/reload-plugins` after it) to try an edit in Vibe.
6. **ADR 0053** `knowledge/decisions/0053-vibe-native-plugin.md` with the
   decisions below, its row in `knowledge/decisions/README.md`, and ADR
   0052's Status line noting it is extended by 0053 (its "until a native
   Vibe plugin exists" consequence is now done), and ADR 0050's Status line
   noting it is amended by 0053. ADR 0053 says why an install-time copy does
   not reopen 0050 D1's rejection of per-agent copies: nothing is committed
   twice, so the copy cannot drift from the checkout it was built from.

## Decisions

- **D1 (installer builds a copy):** `install.py --agent vibe` assembles and
  copies the plugin into `~/.vibe/plugins/agent-kit/`. Decided by the user.
  Rejected: a second generated copy committed to the repo (heavy, can drift)
  and adding Vibe files to `plugin/` in place (the command wrapper skills and
  superpowers sit outside `plugin/skills/`, and moving the wrappers there
  makes Claude Code list every command twice). It must be a copy: Vibe
  rejects links that resolve outside the plugin folder.
- **D2 (superpowers as its own plugin):** the bundled superpowers copy is a
  second Vibe plugin named `superpowers`, so its skills keep the names the
  kit's text uses. Decided by the user. Rejected: folding it into
  `agent-kit` (renames every skill to `agent-kit:<name>`).
- **D3 (absolute hook paths):** the build writes `hooks.toml` with the
  absolute path of the copy's runner. Decided by the user. Avoids relying on
  undocumented `${PLUGIN_ROOT}` expansion and on which shell runs hooks on
  Windows.
- **D4 (migration):** the installer removes the kit's `hooks.toml` block,
  removes the kit's skill links only when Codex and Cursor do not use them
  (else warns about duplicates), keeps the `AGENTS.md` fallback line, and
  the version becomes 1.1.0 with a test that the `agent-kit` Vibe manifest
  and the Claude manifest agree (the `superpowers` manifest matches its
  `VERSION` file). Decided by the user.
- **D5 (refuse foreign folders):** a `~/.vibe/plugins/agent-kit` or
  `superpowers` folder without the kit's marker stops the install with
  nothing changed. Builder's call: two same-named plugins at one scope means
  neither loads, and replacing a user's own folder would delete their work.
- **D6 (nothing frozen):** no `- **Frozen:**` bullet. Every test the
  success criteria name is new (`tests/test_vibe_plugin.py`) or gains or
  changes cases for this change (`tests/test_install.py`,
  `tests/test_plugin_manifest.py`). Builder's call.

## Success criteria

Agreed with the user before the build:

1. **Tests** (`pytest`, temp `--home`, never the real home):
   - the built `agent-kit/plugin.json` and `superpowers/plugin.json` have the
     exact `$schema`, a valid `name`, the `ai.mistral.vibe` extension with
     `schemaVersion` 1, and the same `version` as
     `plugin/.claude-plugin/plugin.json` (superpowers: the `VERSION` file);
   - every `skills/<dir>/SKILL.md` in both has a frontmatter `name` equal to
     `<dir>`; `agent-kit/skills/` holds exactly the 13 kit skills and the 7
     command wrappers; `superpowers/skills/` holds the 12 vendored skills;
   - `ai.mistral.vibe/hooks.toml` parses (`tomllib`) to the two hooks above,
     each naming the copy's `run.py` by absolute path;
   - neither folder contains a link or a `.claude-plugin/` folder;
   - running the built `hooks/run.py --agent vibe --event SessionStart` from
     the copy prints JSON whose `additional_context` holds "Kit map
     (agent-kit)" with the copy as plugin root;
   - install then rerun: second run changes no byte; old kit block removed
     from a `hooks.toml` that also holds a user hook (user hook kept);
     legacy `claude-kit` block removed; old kit skill links removed, a
     foreign link kept; links kept and the warning printed when a Codex or
     Cursor kit hook exists; a foreign `~/.vibe/plugins/agent-kit` or
     `superpowers` folder makes the install exit 1 with nothing changed; damaged markers exit 1
     with nothing changed;
   - `install.ps1 -Agent vibe` reaches the same result (existing wrapper
     test, updated);
   - the Codex and Cursor cases in `tests/test_install.py` keep their
     assertions (parametrized tests may drop their `vibe` case);
   - `tests/test_plugin_manifest.py` asserts version `1.1.0`.
2. **Unchanged elsewhere:** the full suite passes, including
   `tests/test_install.py::test_agent_claude_matches_default` and the
   Claude-output cases in `tests/test_workspace_rules_inject.py`; `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean.
3. **Live run in Vibe 3.1.3 on this machine** (after
   `python plugin/install.py --agent vibe` against the real home, which the
   user's go-ahead on this spec covers):
   - `/plugins` lists `agent-kit` and `superpowers` with no entry under
     "Not loaded" and no warnings;
   - a new session in a child repo receives the kit map and the workspace
     rules, confirmed by asking the agent to quote the
     `Kit map (agent-kit)` and workspace-rules header lines, with the copy
     under `~/.vibe/plugins/agent-kit` as plugin root;
   - `/agent-kit:handoff` runs and `/superpowers:brainstorming` resolves;
   - a turn ends without a hook warning (the `post_agent` Stop hook);
   - `~/.vibe/hooks.toml` no longer holds the kit block.
