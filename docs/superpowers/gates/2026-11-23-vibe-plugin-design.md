# Gate: Install the kit in Mistral Vibe as a native plugin

- **Spec:** docs/superpowers/specs/2026-11-23-vibe-plugin-design.md
- **Spec SHA-256:** 646de5dc3959d05721d0fdad2ca7e0a7a4989b00f4c6c8372b4f9479bb9e9b56
- **Verdict:** pass
- **Date:** 2026-11-23
- **Rounds:** 3 discovery + 0 verification

## Key decisions

- `install.py --agent vibe` builds a plain-file copy into `~/.vibe/plugins/agent-kit/`; nothing generated is committed and nothing Vibe-specific goes into `plugin/` (D1). Vibe runs a copy, so edits need a rerun of the installer.
- The bundled superpowers ships as a second Vibe plugin named `superpowers`, so `superpowers:<name>` names keep working (D2).
- Hook commands name the copy's runner by absolute path, not `${PLUGIN_ROOT}` (D3).
- Migration: the kit's `~/.vibe/hooks.toml` block (current and legacy) is removed, and the file is deleted if left empty; old `~/.agents/skills/` links are removed only when no Codex or Cursor kit hook exists, else kept with a duplicates warning; the `~/.vibe/AGENTS.md` fallback line stays, repointed to the copy (D4).
- Version 1.1.0: the Vibe `agent-kit` manifest follows the Claude manifest, `superpowers` follows `vendor/superpowers/VERSION` (D4).
- A foreign `agent-kit` or `superpowers` folder in `~/.vibe/plugins/` (including a user's own upstream superpowers plugin) stops the install with nothing changed (D5).
- Nothing is frozen (D6).
- User scope only: no project-scope install, no Vibe marketplace, no Vibe `knowledge/` folders; Codex and Cursor stay on links (Scope Out).
- The live run installs against the real home and is covered by the go-ahead on this spec.
- ADR 0053 is added; ADR 0052 is marked extended and ADR 0050 amended by it.

## Findings fixed

- round 1 [blocking] Superpowers manifest version had two rules: Design 4 and D4 now say agent-kit follows the Claude manifest and superpowers follows `VERSION`.
- round 1 [blocking] Version bump broke `tests/test_plugin_manifest.py`: added to Scope In and Success criteria (asserts 1.1.0).
- round 1 [minor] Unnamed "Claude output unchanged" check: names `test_agent_claude_matches_default` and the Claude-output cases in `test_workspace_rules_inject.py`.
- round 1 [minor] "Codex and Cursor tests unchanged" vs parametrized tests: now "Codex and Cursor cases keep their assertions".
- round 1 [minor] marketplace.json hedge: states it carries no version and is unchanged.
- round 1 [minor] Vibe docs passages: setup.md's "until a native Vibe plugin exists" sentence named.
- round 1 [minor] No Frozen header: added D6 (nothing frozen).
- round 1 [plan→minor] Staging folder location: staging lives outside the plugins folder (`~/.vibe/.agent-kit-staging/`), removed on success, failure, and when stale.
- round 2 [blocking] README "update note" did not exist: Design 5 names the two real README passages.
- round 2 [minor] Later Codex/Cursor install re-creates links: docs note added.
- round 2 [minor] Foreign `superpowers` folder untested: criterion covers both folders.
- round 2 [minor] Live check method: quote the kit map and workspace-rules header lines.
- round 3 [minor] ADR 0050 not amended: Status line amended; ADR 0053 explains why an install-time copy does not reopen 0050 D1.
- round 3 [minor] `install.ps1` help text: added to Design 5.
- round 3 [minor] "Every file byte-identical" vs runtime `__pycache__`: now "every file the build writes".

## Plan questions

- In what order does the installer check both foreign-folder markers and the hooks.toml/AGENTS.md markers so that every check runs before any build or write? (Design 2)
- How is `vendor/superpowers/VERSION` (`version:` and `source:` lines) parsed, and is a missing line a build error? (Design 1)
- How does the swap work on Windows (rename old aside, rename new in, delete old?), and what is the staging folder for a standalone `--out DIR`? (Design 1)
- Do the two hooks set a `timeout`, given `run.py` runs six SessionStart scripts at 10 s each? (Design 1)
- Should both plugins be staged before either swaps, and is a mixed state acceptable when the second swap fails? (Design 1)
- Does an unreadable Codex/Cursor `hooks.json` count as "in use" (keep links, warn)? (Design 2.3)
- Is matching the current checkout's skill roots enough when removing old links, or should leftover kit-named links into another checkout be reported? (Design 2.3)
- Does Vibe 3.1.3 ignore the copied Claude-format `hooks/hooks.json` in a plugin? If not, how are the Claude hooks kept from registering? (Design 1)
- Does standalone `vibe_plugin.py --out DIR` also refuse an unmarked folder, and what is its default `--python`? (Design 1)
- What counts as a `hooks.toml` "left empty" (zero bytes or whitespace only)? (Design 2.2)

## Open

- none
