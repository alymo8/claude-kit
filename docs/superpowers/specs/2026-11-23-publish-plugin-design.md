# Publish the kit as a Claude Code plugin (agent-kit)

- **Status:** draft
- **Date:** 2026-11-23

## Purpose

Today the kit installs only by cloning this repo and running
`plugin/install.py`, which links `~/.claude/skills/claude-kit` to the
checkout. A managed work laptop, where the admin allowlists plugin sources,
blocks that, and it asks strangers to clone a repo of kit history just to
use the kit. The user wants to install the kit on their work machine and,
ideally, have other people install and use it.

This change publishes the kit to Claude Code:

- a marketplace hosted in this repo, so a user installs with two commands
  and no clone, and a company admin allows the whole kit with one
  marketplace entry in managed settings;
- the plugin renamed from `claude-kit` to `agent-kit`, because
  `claude plugin validate` flags the `claude-` prefix as reserved.

A native Mistral Vibe plugin is a separate, later spec (spec B, Out). Until
then Vibe, Codex and Cursor keep installing through `install.py --agent`,
and this change keeps that path working.

Anti-goal: an installed plugin that loads but silently loses the kit map,
the workspace rules or the playbooks they point to. An installed Claude Code
plugin is a copy of `plugin/` only, so whatever the kit needs at run time
must live under `plugin/`.

## Scope

**In:**

1. **Self-contained `plugin/`.**
   - `conventions/` moves to `plugin/conventions/` (new) with `git mv`; the
     root `conventions/` folder is gone.
   - The workspace rules (the root `AGENTS.md` above its
     `## Developing the kit` heading) move to `plugin/rules.md` (new). Links
     in it resolve from `plugin/`, so its `conventions/…` links keep working.
   - `plugin/rules.md` opens with the H1 `# Workspace conventions` and one
     line saying these rules apply to every repo that uses the kit. The
     "This file plays two roles" sentence stays only in the root
     `AGENTS.md`.
   - Prose in `plugin/rules.md` naming checkout-only paths changes too:
     `python ../plugin/scripts/render-spec.py` becomes
     `python <plugin root>/scripts/render-spec.py`, and `docs/setup.md`
     becomes its GitHub URL.
   - The root `AGENTS.md` keeps a short header, a line importing the rules
     (an `@` line naming `plugin/rules.md`), and its `## Developing the kit` section.
     `CLAUDE.md` stays `@AGENTS.md`.
   - Links from shipped files (`plugin/rules.md`, `plugin/conventions/`,
     skills, commands, references, templates) to unshipped kit history
     (`knowledge/`, `docs/`) become absolute GitHub URLs
     (`https://github.com/alymo8/claude-kit/blob/main/<path>`), so they
     work from an installed copy.
   - Every live mention of the root `conventions/` path, links and prose
     alike, is updated. "Live" means every tracked file except
     `docs/superpowers/`, `docs/audit/` (dated reports), `vendor/` and the
     ADR files `knowledge/decisions/0*.md` (history, left as written; the
     ADR index `knowledge/decisions/README.md` is live). The files today
     are:
     - `AGENTS.md` (becomes `plugin/rules.md`), `README.md`;
     - `knowledge/decisions/README.md` (its link repointed to
       `plugin/conventions/`);
     - `plugin/commands/ship.md`, `plugin/hooks/kit_map_inject.py`,
       `plugin/scripts/vendor-superpowers.py`;
     - `plugin/skills/spec-gate/rubric.md`: its kit-repo note ("In the kit
       repo, `conventions/decision-log.md` is the workspace convention
       itself") now names `<plugin root>/conventions/decision-log.md`, the
       plugin root stated in the kit map. Its repo-first lookup of a
       project's own `conventions/decision-log.md` stays.
     - `plugin/skills/review/SKILL.md` keeps its repo-first lookup of a
       project's own `conventions/engineering-practices.md`, whose fallback
       is already the kit map; no change.
     - `tests/test_docs.py`, `tests/test_kit_map_inject.py`,
       `tests/test_plan_gate_skill.py`, `tests/test_ship_command.py`,
       `tests/test_spec_gate_skill.py`.
   - `.gitignore` ignores every top-level entry and whitelists named
     folders. It gains a whitelist line for `.claude-plugin/` (new) and loses
     the one for the root conventions folder.
2. **One plugin-root rule instead of `~/.claude/skills/claude-kit`.**
   - Shipped files name that path today as the fallback for
     `${CLAUDE_PLUGIN_ROOT}` (8 commands, 4 references, and the
     `audit`, `plan-gate`, `pr-review-respond`, `present`, `review` and
     `spec-gate` skills). A marketplace install has no such path.
   - The kit map (item 3) states the plugin's absolute root. Each fallback
     becomes "the plugin root stated in the kit map, else
     `~/.claude/skills/agent-kit`". That works for a marketplace copy, a
     contributor link and the other agents; the second part covers a user
     who turned the kit map off.
   - No shipped file names `skills/claude-kit` afterwards, except the
     legacy constants in `plugin/install.py` and
     `plugin/scripts/install-statusline.py` that item 7 uses to find and
     replace old links and status lines.
3. **Hooks that work from an installed copy.**
   - `plugin/hooks/kit_map_inject.py` builds the map from the folder next
     to the hook (`Path(__file__)`), wherever the plugin is installed:
     - a `Plugin root: <absolute path>` line;
     - the playbooks under `plugin/conventions/`.
     It no longer requires a kit checkout and no longer lists the kit's ADR
     folder, which is not shipped. `CLAUDE_KIT_KIT_MAP=0` still turns it
     off.
   - `plugin/hooks/workspace_rules_inject.py` reads the rules from
     `plugin/rules.md` next to the hook and follows the table below.
4. **Rename to `agent-kit`.**
   - `plugin/.claude-plugin/plugin.json` `name` becomes `agent-kit`.
   - Every `claude-kit:<skill>` reference becomes `agent-kit:<skill>`: in
     skills, commands, references, `plugin/rules.md`, the conventions,
     `README.md`, `docs/`, and the generated wrapper skills (regenerated
     with `plugin/scripts/agent-skills.py`).
   - `plugin/references/ship-fast-spec.md` recognises the kit repo by
     `plugin.json` name `agent-kit`, not `claude-kit`.
   - Not renamed: the dated
     reports under `docs/audit/` and the history under
     `docs/superpowers/`.
   - User-facing text and log prefixes become `agent-kit`, for example
     `[agent-kit]`, `Kit map (agent-kit)`, `Workspace rules (agent-kit, …)`.
   - The contributor link becomes `~/.claude/skills/agent-kit`.
   - Identifiers that already sit in files and resources outside this repo
     keep working:
     - `plugin/scripts/spec-index.py` writes the new marker
       (`generated by agent-kit spec-index.py`), and also regenerates a
       README carrying the old `claude-kit` marker, held as a legacy
       constant. Every existing generated index keeps updating.
     - The Docker label `claude-kit.task` and the context-nudge temp paths
       (`<scratch>/claude-kit/nudge-level`, `claude-kit-nudge-<session>`)
       keep their names, like the other state paths (D5).
5. **Claude Code marketplace.**
   - `.claude-plugin/marketplace.json` (new) at the repo root holds:
     - marketplace `name` `agent-kit` and `owner.name` `alymo8`;
     - one plugin entry, `{ "name": "agent-kit", "source": "./plugin",
       "description": … }`, with no `version`, since `plugin.json` keeps it.
6. **Manifest and strict validation.**
   - `plugin/.claude-plugin/plugin.json` gets version `1.0.0` and
     `author` `{ "name": "alymo8" }` (strict validation fails without it).
   - The YAML frontmatter of `plugin/skills/review/SKILL.md` and
     `plugin/commands/new-project.md`, which `claude plugin validate`
     reports as failing to parse today, is fixed without changing its
     meaning.
7. **Installer (contributors, Codex, Cursor, Vibe).**
   - `plugin/install.py` (Claude Code) runs in this order:
     1. In every case, it removes an old `~/.claude/skills/claude-kit`
        link that points into a kit checkout, and rewrites a status line
        that runs a script through that old link to the status line the
        kit installs today (item 8's command when a marketplace copy is
        present, else the one through `~/.claude/skills/agent-kit`).
     2. When a marketplace-installed `agent-kit` is present, it says so and
        does not link, so two copies never load.
     3. Otherwise it links `~/.claude/skills/agent-kit`.
   - `install.py --agent vibe|codex|cursor` works as today with the new
     names:
     - the managed blocks it writes use `agent-kit` markers;
     - the fallback line looks for `Kit map (agent-kit)`;
     - a rerun replaces an old `claude-kit` block in the same file (the
       agent's `hooks.toml`/`hooks.json` and `AGENTS.md`) instead of
       adding a second one.
   - Docs tell Vibe, Codex and Cursor users to rerun the installer after
     updating.
8. **Status line command.**
   - A plugin cannot set the status line, so a new `/agent-kit:statusline`
     command, `plugin/commands/statusline.md` (new), adds the kit's status
     line to `~/.claude/settings.json` when none is set.
   - The command it writes keeps working after a plugin update, which
     changes the cache path with the version.
   - Not in the generated wrapper skills, like `ship-many` (Claude-only).
9. **`/new-project` from an installed copy.** The default parent for a new
   project, checked in this order:
   - the main working tree of the kit checkout containing the current
     folder. In a git worktree of the kit (such as
     `<kit>/.claude/worktrees/<name>`) that is the main checkout, found from
     `git rev-parse --git-common-dir`, never the worktree;
   - the main working tree of the kit checkout the plugin runs from
     (contributor link);
   - the current folder.
   It is never the plugin cache or a kit worktree.
   `plugin/commands/new-project.md` says so.
10. **Docs.**
    - `README.md` and `docs/setup.md` lead with the marketplace install:
      ```
      /plugin install superpowers@claude-plugins-official
      /plugin marketplace add alymo8/claude-kit
      /plugin install agent-kit@agent-kit
      ```
      then the optional `/agent-kit:statusline`.
    - A "For your company admin" subsection gives a managed-settings
      snippet:
      - `strictKnownMarketplaces` with `anthropics/claude-plugins-official`,
        `alymo8/claude-kit` and `{ "source": "skills-dir" }`;
      - `extraKnownMarketplaces` registering `agent-kit`;
      - `enabledPlugins` for `agent-kit@agent-kit` and
        `superpowers@claude-plugins-official`;
      - a link to https://code.claude.com/docs/en/plugins/org.md.
    - `install.py` is described as the path for contributors and for
      Vibe, Codex and Cursor.
11. **ADRs.**
    - `knowledge/decisions/0052-published-plugin.md` (new) and its row in
      `knowledge/decisions/README.md`.
    - An "Amended by ADR 0052" note on ADR 0032 (the kit map no longer
      lists the ADR folder and works without a checkout), ADR 0034 (the
      rules come from `plugin/rules.md`) and ADR 0050 (the rules table
      change and the renamed markers), ADR 0005 (a marketplace install now
      exists beside the contributor link, renamed `agent-kit`) and ADR 0033
      (the installer migrates old links and markers), with their index
      rows.
12. **Tests** for every behaviour above (see Success criteria), with the
    existing tests updated for the moves and the rename.

**Workspace-rules injection.** The Claude Code column is today's
behaviour. In the other column, the first two rows change from silent to
inject, because those agents read `AGENTS.md` without expanding its
`@` import of the rules, so they would otherwise lose the rules in the
kit and its worktrees.

| Where the session runs | Claude Code | Vibe / Codex / Cursor |
|---|---|---|
| Inside a kit checkout (its root or a child repo) | silent (loaded natively through the import) | inject (root: changed) |
| A git worktree of the kit, wherever it lives | silent | inject (changed) |
| Any other repo | inject | inject |

A "kit checkout" is a folder holding both `plugin/rules.md` and
`.claude-plugin/marketplace.json` with marketplace name `agent-kit`. The
hook finds it by walking up from the project folder, so the result is the
same whether the plugin runs from a checkout or from Claude Code's plugin
cache. A "git worktree of the kit" is still detected as today, by comparing
the project's `git rev-parse --git-common-dir` with a kit checkout's `.git`.
That also covers a worktree of a branch from before this change, which has
no `plugin/rules.md`. The kit checkout compared against is the one found by
the walk-up, else the checkout the plugin runs from. Accepted transitional
behaviour: a kit checkout still on a branch from before this change (no
`plugin/rules.md`), opened while the plugin runs from the marketplace
cache, is not recognised, so Claude Code gets the rules twice there until
that checkout is updated.

**Out:**
- Spec B, a native Mistral Vibe plugin (an Agent Plugins manifest, Vibe
  plugin hooks and skills, a `~/.vibe/plugins/` install). It starts with a
  check of how a Vibe plugin declares hook commands and extra skill folders.
- Submitting to Anthropic's plugin directory, a later separate step once
  the marketplace works on the user's work machine.
- Renaming the GitHub repo; it stays `alymo8/claude-kit`.
- Renaming the `CLAUDE_KIT_*` environment variables or the on-disk state
  paths (such as `~/.claude/claude-kit/`).
- Historical specs, plans and gate records under `docs/superpowers/`, and
  their index rows.
- Other repos that mention `claude-kit:` skills (for example
  second-brain-kit); their owners update them.
- The user's auto-memory (updated by capture-learnings, outside this diff).
- Getting the user's employer to allowlist the marketplace.

## Decisions

- **D1 (self-contained plugin):** what the kit needs at run time moves
  under `plugin/`; the kit's own history stays at the root, unshipped.
  Decided by the user. Rejected:
  - the whole repo as the plugin (every install carries tests, specs,
    gate records and vendored superpowers);
  - `plugin/` shipped as it is (the kit map and rules go quiet).
- **D2 (name):** the plugin and the marketplace are `agent-kit`. Decided by
  the user. The repo name stays.
- **D3 (split):** Claude Code now, native Vibe plugin in spec B. Decided by
  the user after the spec gate found the combined spec too large.
- **D4 (directory later):** no directory submission now. Decided by the
  user.
- **D5 (env vars and state paths keep their names):** my call. Renaming
  them breaks existing setups and nothing checks them.
- **D6 (history links become URLs):** my call. Shipped files cannot link
  relatively to unshipped `knowledge/` and `docs/`.
- **D7 (version 1.0.0):** my call. The rename breaks every `/claude-kit:…`
  invocation, and this is the first published release. Marketplace users
  get updates only when the version changes, so every user-visible change
  keeps bumping it, as today.
- **D8 (plugin root from the kit map):** my call. One rule replaces the
  hard-coded skills-dir fallback, in every install mode.
- **D9 (`/new-project` default parent):** my call. Keeps today's behaviour
  inside a kit checkout and never writes into the plugin cache.
- **D10 (nothing frozen):** the rename and moves touch most tests, so no
  evaluator is frozen.

## Design: ADR 0052, the kit is a published Claude Code plugin

Template fields:
- Status `accepted`, Date 2026-11-23.
- Context: the kit installed only from a clone, which managed work laptops
  block and strangers find heavy; an installed Claude Code plugin is a copy
  of its folder only.
- Decision: D1, D2, D3, D5 to D9 above.
- Consequences:
  - Marketplace users get updates only on a version bump.
  - Anything a shipped file needs must live under `plugin/`.
  - ADR 0005 (in-place loading) still holds for contributors.
  - Vibe, Codex and Cursor users rerun `install.py --agent` after updating
    until spec B.

## Success criteria

1. `claude plugin validate ./plugin --strict` and `claude plugin validate .`
   (repo root) both exit 0.
2. `pytest` passes and `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean. New tests show:
   - `.claude-plugin/marketplace.json` holds the fields above, and
     `plugin.json` has name `agent-kit` and version `1.0.0`;
   - from a copy of `plugin/` in a temp folder outside any kit checkout:
     - the kit-map hook prints a plugin root inside that copy and lists
       every playbook inside it;
     - the workspace-rules hook injects `plugin/rules.md` in an unrelated
       repo;
   - each cell of the workspace-rules table holds;
   - no file under `plugin/` has a relative link that resolves outside
     `plugin/`;
   - no live file (as item 1 defines it) mentions the old root
     `conventions/` path, apart from the repo-first lookups of a project's
     own copy in `plugin/skills/review/SKILL.md` and
     `plugin/skills/spec-gate/rubric.md`;
   - no file under `plugin/` names `skills/claude-kit`, apart from the
     legacy constants of item 2;
   - `git ls-files .claude-plugin/marketplace.json` prints the file;
   - `spec-index.py` regenerates a README with the old `claude-kit` marker
     and one with the new marker;
   - `install.py` with a temp `--skills-dir` replaces an old `claude-kit`
     link with `agent-kit` and rewrites a status line through it; with a
     faked marketplace copy present, it removes the old link, rewrites the
     status line and creates no link;
   - the status line command writes a status line when none is set,
     leaves an existing unrelated one alone, and the line it writes still
     runs after a simulated version change of the plugin cache path;
   - `install.py --agent vibe|codex|cursor` with a temp `--home` replaces
     old `claude-kit` blocks instead of adding second ones;
   - `scaffold.py` run from a temp copy of `plugin/` with no kit checkout
     around creates the project in the current folder; with the current
     folder inside a kit checkout's child repo it creates it at that
     checkout's root; with the current folder in a kit worktree it creates
     it in the kit's main checkout.
3. Live check, in an isolated config dir (`CLAUDE_CONFIG_DIR` set to a temp
   folder):
   - `claude plugin marketplace add <worktree>` and
     `claude plugin install agent-kit@agent-kit` succeed;
   - running each SessionStart command from `hooks.json` against the cached
     copy, with `CLAUDE_PLUGIN_ROOT` set to it:
     - prints the kit map with its plugin root and playbooks inside the
       cache;
     - prints the workspace rules for a temp repo outside any kit
       checkout.
4. `git grep -n "claude-kit"` outside `docs/superpowers/` and `docs/audit/`
   lists only:
   - the repo URL `alymo8/claude-kit`;
   - ADR bodies and other `knowledge/` history;
   - the legacy-marker and legacy-link constants in `plugin/install.py`,
     `plugin/scripts/install-statusline.py` and
     `plugin/scripts/spec-index.py`, and their tests;
   - the state paths and labels kept under D5: the `CLAUDE_KIT_*`
     variables, `~/.claude/claude-kit/`, the context-nudge temp paths and
     the Docker label `claude-kit.task`.
5. Privacy: `git diff main` grepped for the machine username and every
   non-public repo name in the user's auto-memory index prints nothing.
6. A PR is open against `main` for the user to merge (`gh pr view` shows
   it open).

## Verification

Run the commands in criteria 1, 2, 4 and 5 and paste their output into the
PR's test plan. Run check 3 by hand and record what it printed.
