# ADR 0041: Two-axis review in `/ship`

- **Status:** accepted
- **Date:** 2026-11-10

## Context
`/ship` step 6 ran the superpowers final review, which checks the change
against the spec. Nothing checked the code's own quality (smells, surgical
diffs, the repo's review standards) as a separate axis, so a change could pass
the spec check and still carry unrelated edits or duplicated code.

## Decision
Step 6 always runs `claude-kit:review` besides the superpowers final review.
The skill runs a standards reviewer and a spec reviewer side by side, and the
two axes are reported apart, never merged into one list. This amends ADR 0037:
step 6 adds two diff-only reviewer subagents on every run, which shifts the
token baseline ADR 0037 measured.
The live check runs in step 10's detached worktree at the squash commit,
before it is removed; if the loaded plugin has no `review` skill yet, the
session follows `skills/review/SKILL.md` from the file. It changes nothing and
its findings are not a stop rule.
Rejected: replacing the final review (the plan constrains this change to edit
no superpowers skill); running `claude-kit:review` only when
the final review did not run (the axes would then be missing on exactly the
runs that look clean).

## Consequences
Every `/ship` run spends more tokens in step 6. The post-merge check in step
10 reports the finding counts per axis so the cost can be weighed against what
the second axis catches. ADR 0037's own status and index row are unchanged.
