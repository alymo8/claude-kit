# Plan gate: User-config audit (`audit --user`) Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-16-user-config-audit.md
- **Plan SHA-256:** 03292b8567d1adf91c942eeeec354ea2eea0003b0e85d5a89eb3f4d6659a6da9
- **Spec:** docs/superpowers/specs/2026-11-15-user-config-audit-design.md
- **Spec SHA-256:** cff7d31a17b3865f20accd4eb175b117405751d21824653a955894b8cac1cccf
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-17
- **Approved by:** /ship (auto)
- **Date:** 2026-11-17
- **Rounds:** 2 discovery + 0 verification

Re-gate after the spec's D4 change (mask secrets in commands, `args` and
`url`), which added Task 5 to the plan. The first gate (2026-11-16) passed
in 1 discovery round with its decisions approved by /ship.

## Plan-introduced decisions

- `enabled` for every install entry (including project-scope ones) comes from the user-level `enabledPlugins`, `settings.local.json` overriding `settings.json`, `null` when neither lists the plugin; for project-scope items the report says that project's settings decide and were not read (Task 2, Task 3)
- The model, not the inventory, resolves a hook's target script with a fixed rule (substitute `${CLAUDE_PLUGIN_ROOT}`, `~`, `$HOME`, `%USERPROFILE%`; skip a listed interpreter); a command with no resolvable script is judged on its text and listed as not read (Task 3)
- Default production bar "one person's workstation: agents with tool access to their private repos, accounts and credentials", marked default in the report header (Task 3)
- Files outside the home directory are cited by absolute posix path; files inside a linked skills entry are cited through the entry path, with the target reported separately (Task 1, Task 2, Task 3)
- The inventory does not parse a `hooks` field in a plugin's `plugin.json`; it flags `manifest_hooks: true` and the model reads that manifest and the hooks files it names (Task 2, Task 3)
- Findings on masked items cite the inventory's `file:line`, quote the masked text as Evidence with `***` and escaped parts written as `...`, and take Confidence `inferred (from: inventory)` (Task 5)
- Criterion 2's secret search skips env/header values shorter than 8 characters as chance matches, printing their count (Task 6)
- For a duplicate key in one JSON object, the last one wins for `line`, as in `json.loads` (Task 1)

## Findings fixed

- round 1 [blocking] Task 4 Step 1 named a test and versions that do not exist: now `test_version_is_0_32_0` asserting `0.32.0`, bumped and renamed to the next minor (`0.33.0` today), expected `FAIL (0.32.0 != 0.33.0)`.
- round 1 [blocking] Criterion 2 secret search would report false hits on short env values: the snippet skips values under 8 characters, prints `skipped <k> short values`, and the step says a hit on a checked value is a leak.
- round 1 [minor] Task 5 consumed `settings_item` and `mcp_item`, which no earlier task defines: Task 5 now says to factor them out first if they are not separate functions, with their signatures.
- round 1 [minor] Task 5 Step 1 used `pytest -q`: now `-v`.
- round 2 [minor] `~` is not expanded for a native program in PowerShell 5.1: Task 6 Step 2 uses `"$HOME"`.
- round 2 [minor] Masking check in Task 6 Step 3b had no snippet: added a `python -I` snippet that loads the script's `redact` and counts fields it would still change; prints `fields <n>, unmasked 0`.
- round 2 [minor] Masking test left out installed-plugin hooks: fixture adds an installed plugin hook `Y=SECRET-INSTALLED-7 node x.js` and asserts `Y=***`.

## Open

- none
