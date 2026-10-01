# Gate: Parallel plan tasks: independent tasks run as concurrent subagents

- **Spec:** docs/superpowers/specs/2026-09-30-parallel-plan-tasks-design.md
- **Spec SHA-256:** b967288fd0677cc0ad7d62d217d44a38ed0bec5afd00e6f37ec8997b9687dd83
- **Verdict:** pass
- **Date:** 2026-10-01
- **Rounds:** 4 (round 4 run at the user's request; plus 1 round on the combined spec it was split from)

## Key decisions

- Builds on the plan gate and ships after it merges (ADR 0016, 0.7.0 assumed);
  this spec takes ADR 0017 and 0.8.0 (Purpose, Decisions)
- Split from `/ship-many`, which ships second and reuses the overlap helpers
  (Decisions)
- Wave size fixed at 3 in `/ship` (Scope Out, Decisions)
- Overlap from existing `**Files:**` blocks; only non-file dependencies need
  the optional `**Depends on:**` line; a missing line means "after every
  earlier task", so existing plans run as today (Design, Decisions)
- Root files without a dot (`Makefile`, `LICENSE`) are not paths; a missed
  overlap on them surfaces as a merge conflict (Design)
- One worktree and branch per task under the OS temp dir, merged back with
  `--no-ff` in task order; conflicts resolved keeping both sides, with a
  Ruling (Design)
- A failed task subagent or a failing `waves` run falls back to
  one-at-a-time work, not a `/ship` stop rule (Decisions)
- Repo-wide git lock retry (5 s, up to 5 times) for every git command
  (Design, Decisions)
- `/ship` step 3 adds `**Depends on:**` lines; superpowers is not edited
  (Scope Out)

## Findings fixed

- combined-spec round: [blocking] split into two specs (user decision)
- round 1 [blocking] path rule contradicted its own examples
- round 1 [blocking] task subagents not covered by the lock retry
- round 1 [blocking] failed task branch: merged or discarded (now discarded)
- round 1 [minor] leftover task worktrees on resume; back-compat criterion
  wording; skill frontmatter
- round 2 [blocking] skill "stop" vs /ship's closed stop rules (now a
  fallback with a Ruling)
- round 2 [blocking] resume after an interrupted wave (per-task ledger
  lines, skip complete tasks)
- round 2 [minor] "shared files need no line" wording; file-suffix
  definition; empty plan and repeated tasks; fixture header; step 4 command
  path and order; `<branch-slug>`
- round 3 [blocking] `**Depends on:**` grammar defined exactly (fixed after
  round 3, not re-reviewed)
- round 3 [minor] smoke output format; ledger line format; merged-branch
  check on resume; repo-relative `<plan>`
- round 4 [blocking] resume check counted a never-committed task branch as
  merged; now requires a merge commit whose second parent is the task
  branch's tip (fixed after round 4, not re-reviewed)
- round 4 [minor] parser owner named (`spec-lint.py`); bulleted/indented
  Depends lines accepted; objective commit check (`git rev-list --count`);
  shorter path rule; prompt framing; empty temp dir removed

## Open

- none. Pass recorded on the user's decision (2026-10-01): round 4's blocking
  finding (resume check) was fixed as the reviewer proposed but not
  re-reviewed. Blocking findings per round: 3, 2, 1, 1.
