# Gate: `/ship` keeps its main session lean

- **Spec:** docs/superpowers/specs/2026-10-20-lean-ship-orchestrator-design.md
- **Spec SHA-256:** 1b14366989b1f12338fe89ac3a72094c38d68ac1a75094d3a7603d63c239e8d9
- **Verdict:** pass
- **Date:** 2026-10-20
- **Rounds:** 1 discovery + 0 verification (re-gate after the user's decision on where the plan gate runs; the previous run took 3 discovery rounds and failed on that decision)

## Key decisions

- The spec gate's approval reply tells the user to `/clear` and run `/claude-kit:ship <path>`; no warning inside `/ship` (relies on `context_nudge.py`) (§1)
- One fresh general-purpose subagent on the session's own model writes the plan in the feature worktree and runs `claude-kit:plan-gate` steps 1–6, returning plan path, verdict and record path; `/ship` checks the result, retries once, keeps 3a–3e and makes every commit (§2, decided by the user)
- Step 4 never implements inline: SDD when every wave has one task and on script failure, `parallel-tasks` otherwise (§3)
- Under `/ship` only, `parallel-tasks`' three inline paths use SDD's task loop; `/ship-fast` and manual runs stay inline (§3)
- SDD's `finishing-a-development-branch` is not run; step 11 cleans up (§3)
- Step 6 skips `requesting-code-review` when step 4's final whole-branch review ran (§4)
- `token-report.py --ship` judges runs on total cost, subagents included, one count per `message.id` (§5)
- `/ship-fast` and `/ship-many` are not edited (Scope)
- New ADR 0037 amends ADR 0017; version 0.26.0 (Scope)
- Post-merge: recomputed baseline, then at least 30% lower median total cost, peak main context under 250k, no quality regression over 3 runs (Post-merge evaluation)

## Findings fixed

- round 1 [blocking] Failed parallel-task fallback still implements inline under `/ship`: `parallel-tasks`' failed-task and non-zero fallbacks also use SDD's task loop under `/ship`; Scope and Testing updated.
- round 1 [minor] ADR 0037 overstates per-task review: reworded; multi-task waves keep plain subagents.
- round 1 [minor] Conventions sentences not identified: named the `## Parallel plan tasks` sentence and the new one.
- round 2 [blocking] Plan-writer repository path ambiguous: the prompt names the feature worktree root, and `/ship` checks the file there.
- round 2 [minor] Where the "Next:" line appears: the reply confirming approval ends with it.
- round 2 [minor] SDD's destructive stop settled by a ruling: such a ruling declines the action unless the spec requires it.
- round 3 [blocking] Decisions and Design disagree on when SDD runs: Decisions bullet now says "every wave has one task".
- round 3 [blocking] `--ship` cost counting of repeated records: each `message.id` counts once; baseline recomputed before evaluation; fixture covers a repeated record.
- round 3 [minor] Step-6 test wording: test looks for "final whole-branch review".
- re-gate: §2 rewritten for the user's decision (a): the plan subagent also runs the plan gate; the false claim that subagents cannot dispatch subagents is removed; step-3 tests updated.
- re-gate round 1 [minor] "Do not rewrite an existing plan" could block gate fixes: reworded to allow the gate's own fixes.
- re-gate round 1 [minor] §3 "no longer invoked" sentence vs criterion 4: marked as rationale; `ship.md` step 4 names neither skill.

## Plan questions

- Is a red suite after an SDD task fixed by resuming its implementer or in the main session, and does step 4's "before every commit" sentence stay? (§3)
- Do SDD's "Rulings I made" and parked or deferred findings go into the PR body and step-12 report, and under which heading? (§3, §4)
- What evidence does step 6 use to know step 4's final review ran, given SDD deletes its workspace? (§4)
- How is step 4 worded to satisfy success criterion 4 (no `executing-plans` in ship.md)? (§3, Success criteria)
- How does `parallel-tasks` learn its caller is `/ship` (an argument or the session's command context)? (§3)
- Before the plan-subagent retry with an existing plan, are the gate's in-place edits and an overwritten older record restored from git or left? (§2)
- Does `--ship` match headless `/ship-many` children (`claude -p "/claude-kit:ship ..."`), and is a run resumed across sessions one row or several? (§5)
- `--ship`: peak context formula, date source, interplay with `--project`/`--all`, whether it replaces the normal report, median of non-numeric columns. (§5)

## Open

- none
