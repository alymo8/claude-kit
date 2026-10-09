# ADR 0025: `present` skill builds decks from a bundled template and checks every slide

- **Status:** accepted
- **Date:** 2026-10-08

## Context
Client presentations of a POC, spec or plan were written by hand as one-off
HTML. Baseline runs without a skill produced sound decks but rebuilt the deck
engine each time (about 90k tokens, a different look and controls per deck),
looked at only some of the rendered slides, and presented a superseded spec
without telling the user.

## Decision
- A kit skill, `present` (`/present [repo | spec.md [plan.md]]`), that Claude
  also picks up when asked for a presentation or deck.
- Decks are `plugin/skills/present/template.html` with its slides replaced: a
  fixed 16:9 stage, keyboard navigation, a start time and counter per slide,
  print CSS, no network resources.
- The skill asks audience, length/demo and save location once (default
  `presentation/index.html`, uncommitted), keeps a claim list with sources,
  labels spec features without code as Planned, and asks which version to
  present when a spec was superseded.
- `plugin/scripts/check-deck.py` checks start times and network resources and
  renders every slide headless into a fresh folder; the skill requires looking
  at each PNG, and rerendering changed slides after an edit.

## Consequences
Decks share one look; a client brand needs template CSS edits. Rendering
needs Chrome or Edge (`DECK_BROWSER` overrides the path); without one the
checks still run and the skill reports that slides were not rendered.
