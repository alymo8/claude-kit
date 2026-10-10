# Gate: ADR triggers: when a decision must, should, or need not get an ADR

- **Spec:** docs/superpowers/specs/2026-10-10-adr-triggers-design.md
- **Spec SHA-256:** 6c95f8253a6ad49a5c802914a826298b4946378a345f585707b81a0b0d09b852
- **Verdict:** pass
- **Date:** 2026-10-10
- **Rounds:** 3 discovery + 1 verification

## Key decisions

- Explicit MUST / SHOULD / NOT REQUIRED lists replace the "significant and meant to stick" judgment; a NOT REQUIRED match overrides MUST and SHOULD.
- The same section goes into the scaffold template's decisions README (with a new `## Index` heading), kept identical to the convention by a test; the kit's own decisions README is unchanged.
- The spec gate enforces MUST triggers (user's choice): a missing ADR is a blocking `open-what` finding that the gate fixes itself by adding the ADR to Scope In and Design (shown under Findings fixed); SHOULD matches are only reported as minor.
- Trigger source fallback: decisions README, then the repo's `conventions/decision-log.md`, then `../conventions/decision-log.md`; otherwise check 8 is skipped, as it is for repos with no decisions directory.
- No new severity class, record format, linter or `SKILL.md` change.
- Out: the plan gate, back-filling ADRs in existing repos, `/ship-fast` POCs.
- ADR 0027 (or the next free number); minor version bump.

## Findings fixed

- round 1 [blocking] Template section had no end boundary (equality test could not pass): `## Index` heading added above the table.
- round 1 [blocking] Fallback location contradicted "read from the repository being gated": explicit three-step fallback and skip rule.
- round 1 [blocking] Precedence between MUST and NOT REQUIRED undefined: NOT REQUIRED wins, stated in the lists and check 8; first NOT REQUIRED item narrowed to "follow without changing".
- round 1 [minor] Kit's own decisions README: stated as unchanged, uses the fallback.
- round 2 [blocking] Gate's response to a check-8 finding unspecified: MUST → gate adds the ADR to Scope In and Design; SHOULD → reported only.
- round 2 [minor] Kit-repo fallback implicit: noted in the rubric text.
- round 3 [blocking] Criterion 5 hard-coded 0027: names the ADR from Scope In (0027 or next free); Design heading updated.

## Plan questions

- Where does the README line go (mermaid node label, or near the Decision log bullet)? (Scope In)
- Does the rubric test slice check 8 from `8. **ADR triggers.**` to the next `## ` heading? (Testing)
- Is the hand-run spec-gate reviewer eval in `tests/fixtures/spec-gate/README.md` re-run and its Results table updated, or skipped? (Testing)
- Is the version bump computed from `main` at merge time? (Scope In)

## Open

- none
