# Gate: Publish the kit as a Claude Code plugin (agent-kit)

- **Spec:** docs/superpowers/specs/2026-11-23-publish-plugin-design.md
- **Spec SHA-256:** 8b3ba17e9d417c82d3a0300f746466ca31140e264242743eb5892e3588da1b9a
- **Verdict:** pass
- **Date:** 2026-11-23
- **Rounds:** 3 discovery + 2 verification

## Key decisions

- What the kit needs at run time moves under `plugin/` (`conventions/` to `plugin/conventions/`, the workspace rules to `plugin/rules.md`); kit history stays at the root, unshipped (D1)
- The plugin and the marketplace are renamed `agent-kit`, which breaks every `/claude-kit:…` invocation; the GitHub repo stays `alymo8/claude-kit` (D2)
- Claude Code marketplace now; the native Vibe plugin is a later spec B (D3); no submission to Anthropic's directory yet (D4)
- `CLAUDE_KIT_*` variables, state paths, the Docker label `claude-kit.task` and the nudge temp paths keep their names; `spec-index.py` also accepts the legacy marker (D5)
- Links from shipped files to `knowledge/` and `docs/` become absolute GitHub URLs (D6)
- Version 1.0.0; marketplace users get updates only on a version bump (D7)
- The plugin root stated in the kit map replaces the hard-coded `~/.claude/skills/claude-kit` fallback, else `~/.claude/skills/agent-kit` (D8)
- `/new-project` default parent: the kit's main checkout from the current folder, else the checkout the plugin runs from, else the current folder; never the cache or a worktree (D9)
- Nothing frozen (D10)
- The kit map drops the ADR folder line and no longer needs a checkout
- Workspace rules are now injected for Vibe, Codex and Cursor in the kit root and kit worktrees; Claude Code behaviour is unchanged; double rules in an old-branch checkout opened from the marketplace copy are accepted as transitional
- `install.py` removes an old `claude-kit` link and rewrites its status line in every case, then links `agent-kit` only when no marketplace copy is present
- New `/agent-kit:statusline` command, because a plugin cannot set the status line
- Strict validation is made clean: `author` in `plugin.json`, frontmatter fixes in `review/SKILL.md` and `new-project.md`
- `.gitignore` whitelists `.claude-plugin/` so the marketplace file ships
- Admin snippet allowlists the official marketplace, `alymo8/claude-kit` and `skills-dir`
- ADR 0052, plus "amended by 0052" notes on ADRs 0005, 0032, 0033, 0034 and 0050
- ADR files are history and are not rewritten; only the ADR index link is repointed
- `plugin/rules.md` gets its own H1 and intro; checkout-only prose paths in it become `<plugin root>` paths and GitHub URLs
- The spec-gate rubric repoints only its kit-repo note; the repo-first lookups in the rubric and the review skill stay

## Findings fixed

- (first gate run) [blocking] too-large: the combined Claude + Vibe spec was split; this spec covers Claude Code, Vibe moves to spec B (user decision)
- (first gate run) [blocking] the `~/.claude/skills/claude-kit` fallback paths: replaced by the kit-map plugin-root rule (item 2)
- (first gate run) [blocking] the old Vibe `AGENTS.md` block omitted from clean-up: the installer replaces old `claude-kit` blocks in every agent file (item 7)
- (first gate run) [blocking] Vibe hook and skill registration unspecified: moved to spec B
- (first gate run) [blocking] the rules table was labelled unchanged: the changed cells are marked, with the reason
- (first gate run) [blocking] `/new-project` from an installed copy wrote into the cache: default-parent order added (item 9)
- round 1 [blocking] the root `.claude-plugin/` folder was git-ignored: `.gitignore` whitelist added, plus a `git ls-files` check
- round 1 [blocking] strict validation failed on existing errors: `author` and the frontmatter fixes added (item 6)
- round 1 [blocking] the spec-index marker rename would orphan existing indexes: legacy marker accepted; the Docker label and nudge paths are kept under D5
- round 1 [blocking] `/new-project` from a kit worktree: the default parent is the main checkout, found through `--git-common-dir`
- round 1 [blocking] the `conventions/` file list was wrong and "live" was undefined: real file list and an exclusion-based definition
- round 1 [minor] ADRs 0005 and 0033 also get amended notes
- round 2 [blocking] installer order when an old link and a marketplace copy both exist: three-step order, plus a test case
- round 2 [minor] criteria for the status line command and for `/new-project` from a child repo added
- round 2 [minor] `docs/audit/` exempted from the rename and from criterion 4
- round 2 [minor] double rules in an old-branch checkout noted as accepted transitional behaviour
- round 3 [blocking] ADRs were both "wording unchanged" and subject to the old-path test: ADR files excluded from "live"
- round 3 [minor] `ship-fast-spec.md` recognises the kit by the `agent-kit` name
- round 3 [minor] checkout-only prose paths in `plugin/rules.md` rewritten
- round 3 [minor] H1 and intro of `plugin/rules.md` stated
- verify 1 [blocking] repo-first lookups conflicted with the old-path test: the rubric changes only its kit-repo note, `review/SKILL.md` is unchanged, and the test exempts both lookups

## Plan questions

- How does `install.py` detect a marketplace-installed `agent-kit` (`installed_plugins.json`, `enabledPlugins`, cache folder), honouring `CLAUDE_CONFIG_DIR`, and how do tests fake it with temp paths? (Scope 7)
- What exact command does `/agent-kit:statusline` write so it survives a cache-path version change (resolve the newest cached copy at run time, copy to a stable path, or read the installed-plugins record), and is it a mode of `install-statusline.py`? (Scope 8)
- Does `install.py` still add a status line when none is set, on a fresh link or with a marketplace copy present? (Scope 7)
- What wording do the kit map and the workspace-rules header use for the root that relative links resolve against (the plugin root), and what does "from {where}/{name}" show? (Scope 3)
- What pattern does the old-root `conventions/` test use, so it skips `plugin/conventions/` and `../conventions/` forms? (Success criteria 2)
- Does `scaffold.py` reuse the hook's definition of a kit checkout? (Scope 9)

## Open

- none
