# Gate: Learning decay: prune stale learnings at ship

- **Spec:** docs/superpowers/specs/2026-11-15-learning-decay-design.md
- **Spec SHA-256:** 9ab4678be6b15ce3493528b06ccc96a1a650f55b884cad70cd1d65c18af8a94d
- **Verdict:** pass
- **Date:** 2026-11-15
- **Rounds:** 2 discovery + 0 verification

## Key decisions

- Prune stale learnings inside capture-learnings at ship time, limited to what the feature's diff changed, instead of per-entry confidence or "last confirmed" stamps; sweep-only rejected (D1, Design: Prune step)
- Auto-memory is in scope for Prune: project memories are resolved or rewritten, and deleted only when nothing in them stays true (D2, D3)
- Feedback and user memories are never edited or deleted; possible conflicts are only reported (D3)
- ADRs are never edited; a contradicted ADR is reported as `not written: ADR <NNNN> may be superseded` (D4)
- The audits get a staleness check for `knowledge/` docs only and never read auto-memory, so memory contents stay out of repo files (D5)
- No approval pause, with or without `--auto`: the PR diff is the review for repo edits and the summary for memory edits (D6)
- Nothing is frozen; the behavioural check is a manual scenario (D7)
- Memory edits use exact replacement after a fresh re-read, because `/ship-many` children may write at the same time
- New ADR 0046, minor version bump to 0.31.0, and no changes to `/ship`, `/ship-fast`, `/ship-many` or the PR-body reference

## Findings fixed

- round 1 [blocking] Existing step-order test breaks under the renumbering: Testing now updates `test_harden_step_sits_between_route_and_commit` to the 3→7 order.
- round 1 [blocking] Scenario expects a pending item the feature does not resolve: the scenario memory now records "pending: fix <the bug>" (resolved) and "first live run pending" (must stay unchanged).
- round 1 [minor] ADR content not summarised: added a Design "ADR" paragraph naming the decisions it records.
- round 1 [minor] Overlap with the existing CLAUDE.md audit bullet: the staleness bullet now covers `knowledge/` docs only.
- round 1 [minor] No Frozen header bullet: added D7 (nothing frozen, with the reason).
- round 2 [minor] "Written by step 3" names the wrong step: now "routed in step 3 of this run (written in step 6)" and "this run's new entries".
- round 2 [minor] Testing points to a check that is not there: removed the clause.
- round 2 [minor] ADR number wording: "the highest is 0045 today, so 0046".
- round 2 [minor] README location: "in the `plugin/` bullet after the skill list".
- round 2 [minor] ADR contents leave out D2: the ADR records D2 and states its relation to ADR 0043.

## Plan questions

- How is step 2's "write nothing and return `none`" reworded so a zero-learnings run still prunes, and does `test_none_is_a_valid_result` change? (Design: Filter; summary lines)
- Does Prune edit files in place in step 4, with step 6 committing them alongside the new entries? (Design: Prune step)
- Does Prune also read targets on `origin/main`, as step 2 does, to avoid redoing a parallel run's edit? (Design: Prune step, Inputs)
- Do Prune and the audit both include nested `knowledge/**` docs (excluding `knowledge/decisions/`)? (Design: Prune step; Audit staleness check)
- Which files does a `knowledge/` doc "describe" for the `last_updated` comparison: the paths it names, its `sources:`, or both? (Design: Audit staleness check)
- For a multi-entry, mixed-confidence staleness finding, what go in **Where**, **Evidence** and **Confidence**? (Design: Audit staleness check)
- Section 4 applies only when the repo has Claude config; should the staleness bullet apply whenever `knowledge/` exists? (Design: Audit staleness check)
- Is `ship-finish.md`'s "keep one copy of each duplicate entry" conflict rule enough for removed or rewritten entries under `/ship-many`? (Scope Out)
- How does the scenario's hand run use a scratch memory directory, and what tells the skill the branch fixed the bug (commit message or spec)? (Success criteria 2)
- What does a resolved memory item look like (body and `MEMORY.md` line)? (Design: Auto-memory)

## Open

- none
