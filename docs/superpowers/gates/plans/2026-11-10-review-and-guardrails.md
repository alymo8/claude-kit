# Plan gate: Two-axis review, surgical diffs, frozen evaluators, Merge Danger and a hardening retro Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-10-review-and-guardrails.md
- **Plan SHA-256:** 01d4bd38498d378cfbad723c86f3d992095f424cc494527e743aa93456b16327
- **Spec:** docs/superpowers/specs/2026-11-10-review-and-guardrails-design.md
- **Spec SHA-256:** 6fc05b191b1b9fbad2436eca0cfc63d7193e2cb959132ad02e3958a8d6d422c4
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-11
- **Approved by:** /ship (auto)
- **Date:** 2026-11-11
- **Rounds:** 1 discovery + 0 verification

## Plan-introduced decisions

- `capture-learnings` tells an automated run from a hand run by an `--auto` argument that `/ship` and `/ship-fast` pass in step 7 (Task 4, 5, 6); the spec only says proposals are never built under the commands.
- A `frozen-check.py` exit 2 under `/ship` and `/ship-fast` is debugged with `superpowers:systematic-debugging` and rerun, not a stop rule; in `claude-kit:review` it is passed to the reviewer and is not a finding (Task 2, 5, 6).
- The frozen-change approval is a separate `git commit --allow-empty` after the change commit, with one `Frozen-change-approved: <path>` trailer line per path (Task 5, 6).
- The frozen check also runs before step 7's push and in step 8's fix loop, not only before pushes in steps 5, 6 and 9 (Task 5).
- Glob semantics: a custom matcher where `*` and `?` never cross `/`, `**/` matches zero or more directories and a trailing `**` matches anything; of several approval trailers for one path, the last wins (Task 1). The spec says "`fnmatch`, with `**` matching across `/`".
- `claude-kit:review` skips the frozen check and reports `Frozen: skipped (no spec or plan)` when it finds no spec or plan (Task 2).
- Files changed by the branch's `Capture learnings` commit (`CLAUDE.md`, `knowledge/`, ADRs) count as process files and are never scope creep (Task 2).
- ADR 0037's Status line and index row are not marked "amended by 0041"; only ADR 0041's text says it amends 0037 (Global Constraints, Task 7).
- The post-merge live review runs in step 10's detached `<tmp>` worktree before its removal; if the loaded plugin has no `review` skill yet, the session follows `<tmp>/plugin/skills/review/SKILL.md` from the file (After merge section).

## Findings fixed

- round 1 [minor] /ship-fast approval commit omits "after the change commit": Task 6's `ship-fast.md` Stop rules bullet now says the `--allow-empty` commit comes after the change commit, matching Task 5.
- round 1 [minor] ADR renumbering does not name every place the numbers appear: Task 7's first Content bullet now lists the file names, index rows, the `ADRS` tuple in `tests/test_review_skill.py`, the conventions/tests mentions and a grep over the diff.
- round 1 [minor] Nothing in /ship points step 10 back to the plan's "After merge" section: the Global Constraint now tells `/ship`'s main session to reread that section before step 10.

## Open

- none
