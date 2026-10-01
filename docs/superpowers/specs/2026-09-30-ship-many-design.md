# `/ship-many`: ship independent specs concurrently

- **Status:** draft
- **Date:** 2026-09-30

## Purpose

`/ship` lands one spec per run. When several approved specs are waiting,
they are shipped one after another even when they touch different files.
`/ship-many` gates several specs, groups the ones that share no files, and
runs each group's specs as concurrent `/ship` runs. Specs that share a file
keep their order.

A spec already names the files it changes in its Scope **In:** list (the spec
gate's `L8-path` rule checks those that contain a `/`). That list is the overlap
declaration; no new field is added.

This spec builds on two specs and assumes both have merged:

- the plan gate (`docs/superpowers/specs/2026-09-30-plan-gate-design.md`);
- parallel plan tasks
  (`docs/superpowers/specs/2026-09-30-parallel-plan-tasks-design.md`), whose
  `parallel-plan.py` path and overlap helpers and `/ship` git lock retry rule
  this spec reuses.

## Scope

**In:**

- `plugin/scripts/parallel-plan.py`: a `specs` command that groups specs into
  waves by their Scope In paths.
- `plugin/commands/ship-many.md` (new): `/ship-many`.
- `plugin/commands/ship.md`: in step 7, the PR title is the spec's first
  `# ` heading text, verbatim; in step 9, a rebase conflict in the generated
  index `docs/superpowers/README.md` is resolved by regenerating it.
- `CLAUDE.md` (workspace): one paragraph on `/ship-many`.
- `knowledge/decisions/0018-ship-many-headless-children.md` (new): ADR 0018,
  plus its row in `knowledge/decisions/README.md`.
- Tests: `tests/test_ship_many_command.py` (new), and additions to
  `tests/test_parallel_plan.py`, `tests/test_ship_command.py` and
  `tests/test_plugin_manifest.py`.
- `tests/fixtures/parallel/specs/` (new): three small specs for the dry-run
  check.
- `plugin/.claude-plugin/plugin.json`: version 0.8.0 → 0.9.0, and
  `/ship-many` appended to its `description`.

**Out:**

- The first real `/ship-many` run on real specs. It happens on the user's
  next use; this PR verifies the grouping, a dry run, and that a headless
  child starts with the chosen flags.
- Specs in different repositories in one call.
- Resuming an interrupted `/ship-many` run. Each child `/ship` leaves its own
  handoff, as today.
- Any merge queue beyond `/ship` step 9's existing rebase, retest and retry.
- Changing the wave size inside each child `/ship` (it stays 3).

## Design

### `plugin/scripts/parallel-plan.py specs`

```
python parallel-plan.py specs SPEC.md [SPEC.md ...] [--max N]
```

`--max` defaults to 3; below 1 is a usage error. Exit 0 on success, 2 on bad
usage or an unreadable file. Output is one JSON object on stdout.

A spec's paths are the paths (as defined in the parallel plan tasks spec:
root files such as `CLAUDE.md` count) in the lines of its `## Scope` section
before the `**Out...:**` label, outside code fences. Overlap is the same
relation as for tasks, with two adjustments:

- `docs/superpowers/README.md` never counts, because it is generated and
  step 9 regenerates it on a conflict.
- Two paths under `knowledge/decisions/` also overlap when their file names
  start with the same four-digit number, because two specs creating ADR 0019
  under different names would collide.

Specs have no declared dependencies. Waves are assigned in argument order by
the same rule as tasks: a spec goes into the first wave after the waves of
every earlier spec it overlaps that holds fewer than `--max` specs. Output:

```json
{"waves": [["a.md", "b.md"], ["c.md"]],
 "overlaps": [["a.md", "c.md", ["plugin/commands/ship.md"]]]}
```

A spec with no paths (no `## Scope` section, or none before its Out label)
overlaps nothing.

Spec names are the arguments as given. `overlaps` lists each overlapping pair
once, earlier spec first, with the paths of the earlier spec that overlap.

### `/ship-many` (`plugin/commands/ship-many.md`)

`/ship-many <spec.md> [<spec.md> ...] [--max N] [--dry-run]`, user-only
(`disable-model-invocation: true`). Invoking it is the approval for every
listed spec, including the merges, as `/ship` is for one. `--max` (default 3)
limits concurrent specs only; each child `/ship` still runs up to 3 task
subagents at a time.

1. **Pre-flight.** `claude --version` is 2.1.259 or later (needed for
   `--permission-prompts`); `git fetch origin` succeeds; `--max` is at least
   1. The **main checkout** is the first entry of `git worktree list`,
   wherever `/ship-many` itself was started. Each spec argument is resolved
   to an absolute path. A path is **inside the main checkout** when it starts
   with the main checkout's root and does not start with the root of any
   other entry of `git worktree list` (a linked worktree nested under it,
   such as `.claude/worktrees/...`, does not count). A spec that does not
   exist, or is not inside the main checkout, is reported as `excluded` (with that reason)
   and the other specs continue. Every remaining spec is then referred to
   by its path relative to the main checkout root, with `/` separators;
   that relative path is what steps 2–4 use. Record the run's start time
   (UTC) and the output of `git worktree list --porcelain`, for steps 4–5.
2. **Gate.** For each spec, run `spec-lint.py --verify-record`.
   - With `--dry-run`: only report each result. Never run the gate, edit a
     spec, or write a record.
   - Otherwise, a spec that does not print `ok:` goes through the
     `claude-kit:spec-gate` skill, steps 1–6, in this session. A spec that
     passes is set to `approved`. A spec that fails is excluded and reported
     with its record's Open items; the others continue.
   - Then record each remaining spec's **title**: the text of its first
     `# ` heading outside code fences (as `spec-index.py` reads it),
     verbatim. Step 5 uses this recorded title and never re-reads the file,
     because a child `/ship` deletes the main checkout's untracked copy.
3. **Group.** Run `parallel-plan.py specs <specs> --max N` from the main
   checkout on the specs not excluded so far (with `--dry-run`, on every spec
   not excluded in step 1). If it exits non-zero, that is a stop rule. With
   `--dry-run`, print the gate results, the waves, the overlaps, and the
   exact child command for each spec, with the log directory that step 4
   would create (built from the step 1 start time, not created), then stop
   without launching anything.
4. **Run.** Create a log directory `<tmp>/claude-ship-many/<repo>-<timestamp>/`
   (`<tmp>` is the OS temp directory, `<repo>` the main checkout's directory
   name, `<timestamp>` the start time as `YYYYMMDD-HHMMSS`). For each wave,
   in order, start one background Bash command per spec, with the main
   checkout as its working directory and a 2-hour timeout:

   ```
   claude -p "/claude-kit:ship <spec>" --permission-mode auto --permission-prompts none --output-format json > <log>/<log-name>.json 2> <log>/<log-name>.err
   ```

   `<spec>` is the spec's path relative to the main checkout (step 1).
   `<log-name>` is the spec's file name without `.md`; when two specs share a
   file name, the later ones get `-2`, `-3`, … in argument order.

   Wait for every command in the wave to end before starting the next wave.
   One child failing never stops the others or later waves.
5. **Collect.** An excluded spec skips this step and keeps status
   `excluded`. For each child that ran:
   - Its exit code comes from the background command's result. Its cost and
     `result` text come from its JSON file when the file holds a JSON object.
   - Its PR is found by title, because `/ship` titles the PR with the spec's
     title: run
     `gh pr list --state all --limit 50 --json url,title,state,mergeCommit,headRefName,createdAt`
     and keep only PRs whose `title` equals the title recorded in step 2
     exactly (backticks and punctuation included, compared as strings, so
     nothing is quoted into a search) and whose `createdAt` is after the
     run's start time. If several remain, take the newest. If none remain,
     the child has no PR.
   - Its status is the first that applies: `merged` (its PR is `MERGED`),
     `timed out` (the timeout ended the command), or `stopped` (any other
     ending, including no PR; the child's handoff says why).
   - For `timed out` and `stopped` children, list the PR's head branch (if
     any) as that child's leftover, and also any worktree whose branch equals
     that `headRefName`. Separately, list as run-level leftovers every
     worktree on a `feat/` branch in `git worktree list --porcelain` now that
     was not in the step 1 list. Do not delete any of them.
6. **Finish.** For each `timed out` child, look up its PR once more as in
   step 5 (a child the timeout did not kill may have merged since), and
   note in the report that it may still be running. `git fetch origin`.
   Bring local `main` up with the same safe fast-forward rule as `/ship`
   step 11. Report one table (spec, wave,
   status, exit code, PR, merge commit, cost, log file), the total cost, every entry of
   `overlaps` from step 3, and the leftovers.

**Stop rules:** `claude` is missing or older than 2.1.259; `git fetch origin`
fails in step 1; `--max` is below 1; every spec is excluded (in step 1 or
2); `parallel-plan.py specs` exits non-zero in step 3 (report its stderr).

### `/ship` change (`plugin/commands/ship.md`)

In step 7, the PR title is the spec's first `# ` heading text, verbatim
(backticks and punctuation kept), so `/ship-many` can find the PR by exact
title. Because backticks, `$` and quotes in a shell argument can be
expanded, step 7 writes the title to a file outside the repo and passes it
as `--title "$(cat <title file>)"`: a command substitution's output is not
expanded again, so the title arrives unchanged. Step 7 then confirms with
`gh pr view --json title` that the title matches the heading.

In step 9, when the rebase onto `origin/main` conflicts in
`docs/superpowers/README.md`, run
`python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py" docs/superpowers`
(fallback if the variable is not expanded:
`~/.claude/skills/claude-kit/scripts/spec-index.py`) and
`git add docs/superpowers/README.md` instead of merging it by hand; resolve
any other conflicted files as before; then `git rebase --continue`.
Concurrent children each commit that generated file, so this conflict is
expected.

## Decisions

- **Headless `claude -p` children** rather than in-session subagents: a
  subagent cannot run a slash command, so it would need a second copy of
  `/ship`'s steps. A child is a normal `/ship` with its own context and a
  per-run cost. (User decision.)
- **Children run with `--permission-mode auto --permission-prompts none`**:
  the same classifier as an interactive auto-mode session; anything that
  would prompt is denied, and the child ends through `/ship`'s own stop
  rules. (User decision.)
- **At most 3 concurrent specs by default**, overridable with `--max`. (User
  decision.)
- **Ship after parallel plan tasks**, as a separate spec. (User decision.)
- **Overlap comes from Scope In**, which the spec gate already checks, not
  from a new field.
- **Strict overlap.** Any shared path serializes, except the generated spec
  index. Two kit specs that both bump `plugin.json` therefore run in
  sequence. A looser rule would depend on agents resolving rebase conflicts
  correctly, which is the risk this design avoids.
- **A dry run is read-only**: it reports gate state but never gates, so it
  can be run on any specs without side effects.
- **One child failing does not stop the others.** Later waves start from
  `origin/main`, which never contains a stopped spec's work.
- **Leftovers are reported, not deleted.** A stopped or timed-out child may
  have work worth resuming from its handoff.

## Success criteria

1. `pytest tests/test_parallel_plan.py` passes, with `specs` tests that:
   disjoint specs share a wave; a shared Scope In path splits them and is
   listed in `overlaps`; a shared root file (`CLAUDE.md`) splits them;
   `docs/superpowers/README.md` alone does not; two different ADR files with
   the same number do; paths after the `**Out:**` label are ignored; `--max`
   caps a wave; a spec with no Scope paths overlaps nothing; a missing file
   and `--max 0` exit 2.
2. Structure tests pass: `tests/test_ship_many_command.py` asserts
   `disable-model-invocation: true`, the exact child flags
   `--permission-mode auto --permission-prompts none --output-format json`,
   `--max` defaulting to 3 and limiting specs only, `--dry-run` never running
   the gate, the version check `2.1.259`, the status order
   (`merged`, `timed out`, `stopped`, `excluded`), the exact-title PR match
   with `createdAt`, a missing spec reported as `excluded`, the timed-out
   recheck in step 6, the child's spec path relative to the main checkout,
   the `git worktree list --porcelain` leftover check, and the five stop
   rules; `tests/test_ship_command.py` asserts step 7 titles the PR with the
   spec's `# ` heading verbatim through `--title "$(cat <title file>)"`, and
   step 9 regenerates
   `docs/superpowers/README.md` with `spec-index.py` and stages it with
   `git add`;
   `tests/test_plugin_manifest.py` lists `ship-many` as user-only.
3. Dry-run check, run by hand because the plugin loads from the main checkout
   until merge: copy the three fixture specs in
   `tests/fixtures/parallel/specs/` (a and b disjoint, c sharing a path with
   a) to a scratch folder `.ship-many-dryrun/` at the main checkout's root, so
   they are inside the main checkout. Before and after the dry run, capture
   `git -C <main checkout> status --porcelain -- docs/superpowers/`,
   `git worktree list`, and
   `gh pr list --state all --limit 50 --json number`. The executing session
   then follows `/ship-many` steps 1–3 with `--dry-run` itself, using the
   feature worktree's scripts, on the three copies. It passes when it prints
   waves `[[a, b], [c]]` (as relative paths under `.ship-many-dryrun/`), one
   overlap, and three child commands, and each captured output is identical
   before and after. Then delete `.ship-many-dryrun/`. The output is in the
   PR.
4. Headless smoke check:
   `claude -p "Reply with OK" --permission-mode auto --permission-prompts none --output-format json`
   exits 0 and its JSON has `result` and `total_cost_usd`. The output is in
   the PR.
5. Docs check in `tests/test_ship_many_command.py`: the workspace `CLAUDE.md`
   names `/ship-many`, and ADR 0018 exists and has a row in
   `knowledge/decisions/README.md`. A manual check confirms `plugin.json`
   says `0.9.0`.
6. `pytest` and `ruff check plugin tests; ruff format --check plugin tests`
   pass, locally and in CI.
