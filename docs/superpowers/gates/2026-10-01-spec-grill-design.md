# Gate: Spec grill: an opt-in interview before the spec is written

- **Spec:** docs/superpowers/specs/2026-10-01-spec-grill-design.md
- **Spec SHA-256:** 385a1d619e8e4b8ea25d15d471bd6bd02680edab4c7da07e640d4504b93ce694
- **Verdict:** pass
- **Date:** 2026-10-01
- **Rounds:** 1

## Key decisions

- The grill is a separate pass after the brainstorming design summary; it does not replace brainstorming's questions, and `superpowers:brainstorming` is not edited (Decisions; Scope Out)
- Opt-in, off by default: `CLAUDE_KIT_GRILL` exactly `"1"` is on, anything else off (Decisions; Design, The switch)
- The switch controls only the injected rule and `L9-coverage`; `/grill` stays invocable either way (Decisions)
- Coverage is recorded in a required `## Coverage` spec section with nine fixed areas, and linted (Design; Decisions)
- `L9-coverage` checks only specs dated on or after 2026-10-01; no backfill; plans never checked (Decisions; Scope Out)
- Rounds by default, no question or round cap; one at a time only if the user's instructions ask (Decisions; Scope Out)
- Every spec is grilled while the switch is on, no per-spec skip (Decisions)
- `coverage.md` is the single source of area names, read by the linter relative to the script (Decisions; Design)
- The grill never answers its own decision questions; N/A without asking only when a fact settles it (Design, SKILL.md)
- Spec-gate rubric does not judge Coverage quality; plans not grilled (Scope Out)
- New ADR 0019; plugin version 0.9.0 → 0.10.0 (Scope In)

## Findings fixed

- round 1 [minor] CLAUDE.md note clashes with "Designing a spec": exact sentence given; existing text kept
- round 1 [minor] "Valid date" undefined: L9 parses with `date.fromisoformat`, unparsable skips; Coverage entry reworded
- round 1 [minor] Area bullet parsing edge cases: continuation lines count; unknown areas ignored; first duplicate checked
- round 1 [minor] README diagram node: named by Mermaid ids (`dec --> grill --> spec`, class `gate`)
- round 1 [minor] L9 tests depend on developer env: tests set or delete `CLAUDE_KIT_GRILL` themselves

## Open

- none
