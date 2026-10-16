# ADR 0036: /ship approves the plan gate's decisions itself

- **Status:** accepted
- **Date:** 2026-10-16

## Context
ADR 0016 has the user sign off on the decisions a plan adds that its spec did
not settle. Under `/ship`, that stop interrupted autonomous runs, and the user
approved the lists as written, so each stop cost a round trip with no change in
outcome. ADR 0027 relied on the same sign-off to bring ADR-worthy plan
decisions to the user.

## Decision
- Under `/ship`, a plan gate `pass-with-decisions`, and a resumed record at
  `decisions not approved`, is approved by `/ship` itself. The record gets
  `- **Decisions approved:** <date>` plus `- **Approved by:** /ship (auto)`.
- An irreversible decision still stops the run: data not regenerable from the
  repo, rewritten published history, or an external change a PR revert cannot
  undo. When unsure, a decision counts as irreversible. The stop writes
  `- **Stopped on irreversible:** <date>` in the record, so a rerun of
  `/ship` stops again instead of judging the decision afresh; only the user's
  answer clears it.
- A decision that hits a decision-log MUST trigger gets its ADR written by
  `/ship` on the feature branch, without editing the plan, whether `/ship` or
  the user approved it.
- A plan gate `fail` still stops the run.
- Running the plan gate by hand is unchanged: it still asks the user.

## Consequences
- The user first sees these decisions in the PR's
  `Plan decisions (auto-approved)` section and in the final report, possibly
  after the merge. Reverting the PR undoes them, which is why irreversible
  decisions still stop.
- This amends rather than supersedes ADRs 0016 and 0027, because ADR 0016
  still governs the manual plan gate.
