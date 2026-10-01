# Gate: `/ship-many`: ship independent specs concurrently

- **Spec:** docs/superpowers/specs/2026-09-30-ship-many-design.md
- **Spec SHA-256:** 5516a26c704092400198a47dd39fa6a8c84256767309dba77e2352fe4d853991
- **Verdict:** fail
- **Date:** 2026-10-01
- **Rounds:** 4 (round 4 run at the user's request)

## Key decisions

- Children are headless `claude -p "/claude-kit:ship <spec>"` processes with
  `--permission-mode auto --permission-prompts none` (Decisions)
- At most 3 concurrent specs by default (`--max`); each child keeps its own
  task wave size of 3, so up to 9 agents at once (Decisions, Scope Out)
- Overlap from Scope In paths, strict: any shared path serializes except
  `docs/superpowers/README.md`; same-numbered ADR files overlap (Design)
- Invoking `/ship-many` approves every listed spec and its merge; specs that
  fail the gate, are missing, or live outside the main checkout are excluded
  and the rest continue (Design steps 1–2)
- A dry run is read-only and never gates (Decisions)
- One child failing never stops the others; leftovers are reported, never
  deleted; a timed-out child is rechecked once (Decisions, steps 5–6)
- `/ship` changes: step 7 uses the spec's H1 verbatim as the PR title (passed
  via a file); step 9 regenerates the spec index on a rebase conflict
- ADR 0018, plugin 0.9.0

## Findings fixed

- round 1 [blocking] missing spec path: now `excluded`, others continue
- round 1 [blocking] PR lookup: exact title match, created after run start,
  newest wins, none means no PR
- round 1 [minor] main checkout, `<repo>`, timestamp defined; step 9 stages
  the regenerated index; timed-out children rechecked in step 6
- round 2 [blocking] `/ship` step 7 now titles the PR with the H1 verbatim
- round 2 [blocking] child spec path is relative to the main checkout
- round 2 [blocking] leftovers found by diffing `git worktree list --porcelain`
- round 2 [blocking] `parallel-plan.py specs` failure is a stop rule; `--max`
  validated in step 1
- round 2 [minor] dry-run log dir; all overlaps reported; `spec-index.py`
  invocation; log-name collisions; `plugin.json` description
- round 3 [blocking] spec title recorded in step 2, never re-read (fixed
  after round 3, not re-reviewed)
- round 3 [blocking] PR title passed via `--title "$(cat <title file>)"`
  and confirmed (fixed after round 3, not re-reviewed)
- round 3 [blocking] "inside the main checkout" defined (nested linked
  worktrees excluded); dry-run fixtures copied to `.ship-many-dryrun/` (fixed
  after round 3, not re-reviewed)
- round 3 [blocking] dry-run check compares before/after captures (fixed
  after round 3, not re-reviewed)
- round 3 [minor] spec with no Scope paths overlaps nothing; L8 wording;
  exit code column; excluded specs skip the PR lookup
- round 4 [blocking] one title rule for `/ship-many` and `/ship` step 7
  (first `# ` line outside fences, prefix and trailing whitespace removed);
  the false "as spec-index.py reads it" claim dropped (fixed after round 4,
  not re-reviewed)
- round 4 [blocking] step 7 title mismatch: one `gh pr edit` fix, then a new
  `/ship` stop rule (fixed after round 4, not re-reviewed)
- round 4 [minor] script invocation paths; duplicate specs excluded; what a
  stop rule does; status-order wording; fixture names and expected output

## Open

- Round 4's two blocking findings are fixed in the spec but not
  re-reviewed. Blocking findings per round: 2, 4, 4, 2.
