# Gate: `/ship-fast`: a spec the user drives, and product decisions asked out loud

- **Spec:** docs/superpowers/specs/2026-10-07-ship-fast-user-driven-spec-design.md
- **Spec SHA-256:** 0d52568de752a68357ec853a68ea7d570820fce22df94d279e8c6dbd5989eb85
- **Verdict:** pass
- **Date:** 2026-10-07
- **Rounds:** 3 discovery + 2 verification

## Key decisions

- Spec creation moves inside `/ship-fast` as the only behaviour (no flag): brainstorming (approaches and one full design, no clarifying questions), then a grill limited to product areas; ADR 0022 amends ADR 0021.
- An empty argument or free text starts the interview, replacing "newest spec"; a `.md` argument naming no file is a stop.
- Question budgets: at most 7 in step 0 (idea, Home and the approach choice included); step 3b at most 3 product plus at most 3 non-risky engineering questions; choices not asked are written down as assumed.
- Risky engineering choices (irreversible data, real credentials or paid services, outside interfaces) are always asked, outside every budget; this replaces the old stop rule's data and interface cases.
- Late product and risky questions are asked inline and never end the run; parallel subagents report them as a failed task.
- Non-interactive runs: step 0 stops; product and non-risky questions take recommended answers, listed as assumed; a risky choice stops with a handoff.
- The grill confirmation is the spec approval; still no gates.
- Home: any git repository other than claude-kit is the home without asking; a new repository's spec is written to `~/.claude/ship-fast-specs/` and copied in by step 1; every stop after step 0 states the spec path for the rerun.
- User-answered questions (product or engineering) go under PR Decisions; only unasked engineering choices go under Assumptions.
- `/ship-fast` never deletes, or suggests deleting, a repository; the live-run repo `ship-fast-demo` is kept.
- No change to `/ship`, `/ship-many`, gates, `parallel-plan.py`, brainstorming, grill or parallel-tasks; version 0.14.0.

## Findings fixed

- round 1 [blocking] Step 0 asks engineering questions it says it never asks: Home and the approach choice named as the only engineering questions in step 0, inside its budget; criterion 5 updated.
- round 1 [blocking] Step 3b on a resumed run: Resume rule skips 3b when the task list has `## Decisions`.
- round 1 [minor] Step 3b budget wording: Decisions now say 3 product + 3 non-risky engineering.
- round 1 [minor] Nonexistent `.md` argument: now a stop rule.
- round 1 [minor] Criterion 4 loosely checkable: names the word `interview`.
- round 2 [blocking] No behaviour for non-interactive runs: decision asked; Non-interactive runs rule added (user's choice).
- round 2 [minor] Progress-line coverage: steps 0 to 8 including 3b, in Design and criterion 5.
- round 2 [minor] Manifest check already passed: checks the text after `/ship-fast`.
- round 2 [minor] Approval wording omitted risky questions: added; progress lines are not reports.
- round 2 [minor] Live-run gitleaks CI risk: noted as fixable inside `ship-fast-demo`.
- round 3 [blocking] Rerun spec path undefined: new-repo spec in `~/.claude/ship-fast-specs/`; every stop states the spec path.
- round 3 [minor] `/ship-many` child example removed.
- round 3 [minor] PR placement of answered engineering questions: under Decisions.
- round 3 [minor] Criterion 4 grep on wrapped lines: paragraph-level check; manifest test asserts only the version.
- verify 1 [blocking] Rerun path keyed on folder existing: keyed on the spec copy being committed.

## Plan questions

- How does the extra "do not guess product/risky choices" instruction reach `parallel-tasks` subagents (an override in `ship-fast.md`, or the task list header)? (Product questions during the build)
- When step 3b asks nothing, is a `## Decisions` section with "none" written, so Resume and inline appends have a target? (Step 3b; Unchanged)
- If the user picks a non-recommended approach, is the design re-presented or folded into the grill summary, and does a follow-up round count against the budget? (Step 0 items 3–4)
- Is brainstorming's visual-companion offer suppressed in step 0, or counted against the budget? (Step 0 item 3)
- Does `ship-fast.md` tell grill to skip its `## Coverage` hand-off? (Step 0 items 4–5)
- What signal marks a session as non-interactive? (Approval wording)
- Is a relative `.md` argument resolved against the cwd? (Input)
- How is "do not run its spec review" worded without the literal `spec-gate` the existing test forbids? (Step 0 item 3)

## Open

- none
