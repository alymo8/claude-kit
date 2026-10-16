# Gate: `/ship` approves the plan gate's decisions itself

- **Spec:** docs/superpowers/specs/2026-10-16-ship-auto-approves-plan-decisions-design.md
- **Spec SHA-256:** 3f66a46faabb7dd25c6ae5715f6130af37c5aec8decc3cb2c0c4e2c2b399e6a2
- **Verdict:** pass
- **Date:** 2026-10-16
- **Rounds:** 3 discovery + 0 verification

## Key decisions

- Under `/ship`, a plan gate `pass-with-decisions` is approved automatically, taking the plan's own choices; a gate `fail` still stops.
- An irreversible plan-introduced decision still stops `/ship`: data not regenerable from the repo, rewritten published history, or an external change a PR revert cannot undo. When unsure, `/ship` treats a decision as irreversible.
- A decision that hits a decision-log MUST trigger is approved, and `/ship` writes its ADR on the feature branch at step 3 without editing the plan.
- Audit trail: the unchanged `Decisions approved` line plus `- **Approved by:** /ship (auto)`; `spec-lint.py` is unchanged.
- A resumed record at `decisions not approved` is approved the same way, which replaces "rerunning `/ship` is never approval".
- The PR body and the final report list the auto-approved decisions; the user may first see them after the merge.
- The manual plan gate is unchanged; `/ship-many` inherits the change; `/ship-fast` is unaffected.
- ADR 0036 amends ADR 0016 and ADR 0027's sign-off consequence for `/ship` only; version 0.25.0.

## Findings fixed

- round 1 [blocking] Version bump breaks a test file not in Scope In: added `tests/test_plugin_manifest.py` to Scope In.
- round 1 [blocking] ADR MUST-trigger decisions no longer reach the user: the user chose to approve them and write their ADR; added the ADR-trigger design section, the 0027 amendment and the Decisions bullet.
- round 1 [minor] ADR 0016 index row status: Scope In now updates it.
- round 2 [blocking] Adding the ADR to the plan would make the record stale: `/ship` writes the ADR file at step 3 and never edits the plan; a repo with no ADR folder skips it.
- round 2 [blocking] 0027's status would drop "amended by 0032": it becomes `accepted; amended by 0032, 0036`.
- round 2 [minor] Ambiguous "step 5": sub-steps relabelled.
- round 3 [minor] Stale stop-rule sentence: the spec now says to replace it.
- round 3 [minor] Amended vs superseded: ADR 0036 summary explains the choice.
- round 3 [minor] Sub-step numbering collided with `/ship` steps: labelled 3a–3e.

## Plan questions

- Does the "/ship approves the spec, not decisions a plan adds later" sentence stay? (Design › Stop rule wording; answered in round 3's fix: it is replaced)
- Which exact phrases do the tests assert are absent and present for the stop rule and for step 12's list? (Testing)
- Is the kit-dev-gotchas Gates bullet reworded (answers outside Scope In become auto-approved decisions listed in the PR) or removed? (Scope In)
- After an irreversible-decision stop that the user approves, does the record get an `Approved by` line, and with what value? (Design › Stop rule wording)
- Does the "auto-approved" PR/report section depend on the record's `Approved by: /ship (auto)` line, so user-approved lists are left out or titled differently? (Design › Visibility)
- Is `test_version_is_0_24_0` renamed to `test_version_is_0_25_0`? (Scope In)

## Open

- none
