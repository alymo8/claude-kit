# PR body for /ship and /ship-fast

Read by `commands/ship.md` step 7 and `references/ship-fast-finish.md` step 7 when they write the PR body file.

## Shared parts

- **Summary:** two to five lines, then the smallest visual that shows the
  change: pseudocode, a call tree, a file tree, a Mermaid diagram, or a `diff`
  sketch of one of those. One visual, two at most. A text-only change gets
  none and quotes a short before and after instead.
- **Merge danger:** two lines.
  - `**Door:** one-way | two-way`, with one line why. One-way when merging
    does something reverting the PR cannot undo, by the irreversible test of
    `/ship` step 3a: it deletes, overwrites or migrates data not regenerable
    from the repo, rewrites published git history, or changes something
    outside the repository. Otherwise two-way.
  - `**Blast radius:** <one word>` (for example `none`, `docs`,
    `one-command`, `all-sessions`, `consumers`), with one line on what could
    break.
- **Hardening proposals:** the `Hardening:` lines from the capture-learnings
  summary, verbatim. Omitted when the summary says `Hardening: none`.

## /ship body, in this order

- Summary.
- Links to the spec, the plan and the plan gate record
  (`docs/superpowers/gates/plans/<plan file name>`).
- A section listing verbatim each entry of the plan record's
  `## Plan-introduced decisions` (omitted when that list is `none`), titled
  `Plan decisions (auto-approved)` when the record has
  `- **Approved by:** /ship (auto)` and `Plan decisions` otherwise.
- Merge danger.
- Review: per `claude-kit:review` axis (Standards, Spec), one line on the
  findings fixed and one on the `judgement` findings left; plus the findings
  the final whole-branch review fixed.
- Hardening proposals.
- Verification: the exact commands and their results.
- The attribution line the session requires.

## /ship-fast body, in this order

- Summary.
- Acceptance criteria, each with its evidence (the test name or the
  smoke-run output).
- Decisions: every question the user answered, then the product choices
  "assumed (not asked)".
- Assumptions: engineering choices taken without asking.
- Cut: what the POC leaves out.
- Merge danger.
- Hardening proposals.
- Links to the spec and the task list.
- Verification: the exact commands and their results.
- The attribution line the session requires.
