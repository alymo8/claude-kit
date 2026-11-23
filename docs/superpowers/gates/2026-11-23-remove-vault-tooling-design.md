# Gate: Remove the vault tooling that moved to second-brain-kit

- **Spec:** docs/superpowers/specs/2026-11-23-remove-vault-tooling-design.md
- **Spec SHA-256:** 8d0073cfe4f5f3103ee96d9842e274cea3fe60f4b378c82a0b6b112bff196f59
- **Verdict:** pass
- **Date:** 2026-11-23
- **Rounds:** 3 discovery + 0 verification

## Key decisions

- claude-kit removes all vault tooling (command and its agent-skill wrapper, hook, scripts, ingest and task-prompt skills, template, tests and fixtures); second-brain-kit is the only home, named without a URL (Scope, D2)
- ADRs 0040 and 0047 keep their full bodies and get status `moved` rather than `superseded`, outside the convention's status list, following ADR 0012 (D1)
- New ADR 0051 records the split; the knowledge-layer convention keeps the principle and the rule that repos link to vault pages only by name (Scope, Design)
- Historical specs, plans, gate records and `docs/audit/` stay untouched (D3, Out)
- Version bumps to 0.36.0 as a user-visible removal (D4)
- claude-kit stops reading and documenting `CLAUDE_KIT_VAULT` (D5)
- The audit user-mode check on scheduled untrusted-content tasks stays, reworded to "notes ingest" (Scope)
- No evaluator is frozen because the change edits its own tests (D6)
- The kit-map hook has no vault lines, so nothing to change there (Out)

## Findings fixed

- round 1 [blocking] Criterion 4's allow-list leaves out lines the spec itself requires: criterion 4 now allows the `## Personal vault` headings, pointer lines and the new ADR test
- round 1 [minor] Version-test update missing from Scope: `test_version_is_0_35_0` renamed to `test_version_is_0_36_0`
- round 1 [minor] README line 140 has two vault sentences: both named
- round 1 [minor] `moved` vs `superseded`: D1 gives the reason
- round 2 [blocking] Scope omits `tests/test_run_hooks.py`: SessionStart count 7 becomes 6 added to Scope
- round 2 [minor] `moved` outside the template's status list: D1 says so
- round 2 [minor] Frozen evaluator not stated: D6 added
- round 2 [minor] Privacy criterion relied on session knowledge: criterion 5 names `%USERPROFILE%` and the auto-memory index
- round 2 [minor] Knowledge-layer edit dropped the link-by-name rule: the sentence is kept

## Plan questions

- What exactly does the new moved/split ADR test assert (0051 exists and is indexed, 0040/0047 rows and files read `moved` and name ADR 0051, following `test_agent_agnostic_adr_amends_0034_and_0035`)? (Scope, `tests/test_docs.py`)

## Open

- none
