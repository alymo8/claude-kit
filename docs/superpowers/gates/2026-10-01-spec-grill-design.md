# Gate: Spec grill: an opt-in interview before the spec is written

- **Spec:** docs/superpowers/specs/2026-10-01-spec-grill-design.md
- **Spec SHA-256:** 17033370644b007ecf48feaef45c942b2ec9ee868ad376b08fcf45307699449e
- **Verdict:** pass
- **Date:** 2026-10-01
- **Rounds:** 2

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
- New ADR 0019; plugin version 0.10.0 → 0.11.0 (main reached 0.10.0 in #25) (Scope In)

## Findings fixed

- round 1 [minor] CLAUDE.md note clashes with "Designing a spec": exact sentence given; existing text kept
- round 1 [minor] "Valid date" undefined: L9 parses with `date.fromisoformat`, unparsable skips; Coverage entry reworded
- round 1 [minor] Area bullet parsing edge cases: continuation lines count; unknown areas ignored; first duplicate checked
- round 1 [minor] README diagram node: named by Mermaid ids (`dec --> grill --> spec`, class `gate`)
- round 1 [minor] L9 tests depend on developer env: tests set or delete `CLAUDE_KIT_GRILL` themselves

- round 2 (after rebase onto #25) plugin version bump updated to 0.10.0 → 0.11.0
- round 2 [minor] README edge quote: full chain `brain --> dec --> spec --> sgate --> sok`
- round 2 [minor] hooks.json matcher: own group, no matcher, like lean_context_inject.py
- round 2 [minor] L9 report line for empty / bare N/A: the bullet's line
- round 2 [minor] N/A case: matched case-insensitively

## Open

- none
