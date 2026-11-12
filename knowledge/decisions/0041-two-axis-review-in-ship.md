# ADR 0041: Two-axis review in `/ship`

- **Status:** accepted
- **Date:** 2026-11-10

## Context
`/ship` step 6 ran the superpowers final review, one broad bug hunt. It did
not check the diff line by line against the repo's written review rules
(smells, surgical diffs), nor the diff against the spec for scope creep, so a
change could pass it and still carry unrelated edits, duplicated code or work
the spec never asked for.

## Decision
Step 6 always runs `claude-kit:review` besides the superpowers final review.
The skill runs a standards reviewer and a spec reviewer side by side, and the
two axes are reported apart, never merged into one list. This amends ADR 0037:
step 6 adds two diff-only reviewer subagents on every run, which shifts the
token baseline ADR 0037 measured.
The change that introduces the skill is checked live once, after its merge,
in step 10's detached worktree at the squash commit (the loaded plugin may not
have the skill yet, so the session follows `skills/review/SKILL.md` from the
file); that one-time check changes nothing and is not a stop rule.
Rejected: replacing the final review (the plan constrains this change to edit
no superpowers skill); running `claude-kit:review` only when
the final review did not run (the axes would then be missing on exactly the
runs that look clean).

## Consequences
Every `/ship` run spends more tokens in step 6. Step 12's report gives the
finding counts per axis so the cost can be weighed against what the second
axis catches. ADR 0037's own status and index row are unchanged.
