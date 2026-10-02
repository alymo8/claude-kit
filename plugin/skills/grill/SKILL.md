---
name: grill
description: Use when the injected spec-grill rule applies (CLAUDE_KIT_GRILL=1), after a brainstorming design summary and before the spec is written, or when the user asks to be grilled on a plan, design or idea. Interviews the user in numbered rounds, each question with a recommended answer, over the design's open decisions plus a coverage checklist, until the user confirms a shared understanding.
argument-hint: [topic]
---

# Grill

Adapted from the `grilling` skill in
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT licence).

Interview the user until you both hold a shared understanding of the design,
with nothing left silently assumed. The spec is written from the result.

## The tree

Map the subject as a design tree: every decision branches into the decisions
that hang off it. The tree holds:

- every choice the agreed design makes or leaves open (with no design in the
  conversation, the subject is `$ARGUMENTS`);
- every area listed under `## Areas` in `coverage.md` in this skill's
  directory.

## Facts and decisions

- **Facts are your job.** When a question needs a fact from the environment,
  read the repo or dispatch an Explore subagent. Never ask the user what you
  can look up. Only the questions that depend on a running lookup wait for
  it; ask the rest now.
- Close a coverage area as N/A without asking **only** when a fact settles
  it, and state the fact.
- **Decisions are the user's.** Put each one to them and wait. Never answer
  your own decision question.

## Rounds

The frontier is every open decision whose prerequisites are settled. Ask the
whole frontier in one round, and nothing that depends on another question
still open in the same round; that question belongs to a later round. Number
each question and give your recommended answer, separating questions with
`---`:

```
❓ **Q1 - <title>**: <question, with options when there are any>

➡️ <recommended answer and a one-line reason>

---

❓ **Q2 - <title>**: <question>

➡️ <recommended answer and a one-line reason>
```

If the user's instructions ask for one question at a time, ask one per
message instead.

After each round, recompute the frontier from the answers and ask the next
round. An answer that changes an earlier one reopens that branch.

## End

When the frontier is empty, post a grill summary:

- **Decisions:** each question and the user's answer.
- **Coverage:** each area in `coverage.md`, with where the design addresses
  it, or `N/A` and the reason.

Ask the user to confirm a shared understanding, and wait. Do not write the
spec or act on the design until they confirm.

## Hand-off to the spec

The settled decisions go into the spec's `## Decisions`. The coverage list
becomes its `## Coverage` section, in the format in `coverage.md`. With
`CLAUDE_KIT_GRILL=1`, `spec-lint.py` rule `L9-coverage` checks that section.
