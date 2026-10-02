# ADR 0019: An opt-in grill runs between the design and the spec

- **Status:** accepted
- **Date:** 2026-10-01

## Context
Specs missed whole areas (failure modes, rollout, irreversible data) and
settled decisions silently; the spec gate (ADR 0015) caught some afterwards
as decision findings and `/ship` stopped on the rest. Brainstorming's
questions stop when the model feels it understands.

## Decision
- A `claude-kit:grill` skill, adapted from `grilling` in mattpocock/skills
  (MIT), runs after the brainstorming design summary and before the spec. It
  asks the design's open decisions plus a nine-area coverage checklist
  (`plugin/skills/grill/coverage.md`) in numbered rounds with recommended
  answers, looks facts up itself, and ends on a confirmed shared
  understanding.
- It is opt-in: a SessionStart hook injects the rule only when
  `CLAUDE_KIT_GRILL=1`. The skill stays invocable by hand either way.
- With the switch on, specs dated 2026-10-01 or later need a `## Coverage`
  section, checked by `spec-lint.py` rule `L9-coverage`, which reads the area
  names from `coverage.md`.

## Consequences
Spec design gains an interview step for users who opt in; older specs and
users who do not opt in see no change. Whether a spec needs `## Coverage`
depends on the machine's setting, so a spec gated with the switch off may
lack it. Flipping the default later needs a new ADR.
