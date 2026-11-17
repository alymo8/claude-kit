# Plan gate: User-config audit (`audit --user`) Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-16-user-config-audit.md
- **Plan SHA-256:** 79f3d0f435bd049b9112d4ae9cd3fd81d855092ce78c7ddfcd47c35a1215c92e
- **Spec:** docs/superpowers/specs/2026-11-15-user-config-audit-design.md
- **Spec SHA-256:** 808f7597738726423f325ec335cb53d29d367c49ee07a2c934129044f2f76a82
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-16
- **Approved by:** /ship (auto)
- **Date:** 2026-11-16
- **Rounds:** 1 discovery + 0 verification

## Plan-introduced decisions

- "Enabled" for an installed plugin comes only from the user-level `enabledPlugins` (`settings.local.json` overriding `settings.json`), `null` when neither lists it; the report says a project-scope install's enablement depends on that project's settings, which are not read (Task 2, Task 3)
- Files outside the home directory (`installPath`, link targets) are written and cited as absolute posix paths; files inside a linked skills entry are cited through the entry path, with the target reported separately (Task 1, Task 2, Task 3)
- The inventory does not parse a `hooks` field in a plugin's `plugin.json`; it sets `manifest_hooks: true`, and the session reads that `plugin.json` and the hooks files it names in full (Task 2, Task 3)
- The model, not the inventory, resolves a hook command to its target script with a stated substitution and interpreter-skip rule; an unresolvable command is judged on its text and listed as not read (Task 3)
- User mode replaces everything in SKILL.md after the branch (Setup 1-5, Passes 1-4, Output); default production bar "one person's workstation: agents with tool access to their private repos, accounts and credentials", marked default in the report header (Task 3)
- Criterion 2's secret search is a throwaway scratch Python script that prints only counts and the key names of any hits (Task 5)

## Findings fixed

- round 1 [minor] Task 2 Step 2 expected a test to fail that Task 1 already makes pass: expectation now 8 failing, `test_wrong_types_do_not_crash` passing.
- round 1 [minor] The fixture never said where the fake home is: fixture creates and returns `tmp_path / "home"`.
- round 1 [minor] No fixture plugin absent from `enabledPlugins`: test adds `other@market` and asserts `enabled is None`.
- round 1 [minor] README insertion point contradicted itself: insert after `compares them by domain`, before its closing `)`.

## Open

- none
