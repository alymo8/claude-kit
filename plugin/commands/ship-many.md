---
description: Use to ship several approved specs at once — gates them, groups the ones that share no files, runs each as a headless /ship, and reports one table
argument-hint: <spec.md> [<spec.md> ...] [--max N] [--dry-run]
disable-model-invocation: true
---

Ship the specs in `$ARGUMENTS` concurrently where they share no files.

Invoking `/ship-many` is the user's approval for every listed spec, including
the merges, as `/ship` is for one. Do not ask for confirmation at any step.
`--max N` (default 3) limits concurrent specs only; each child `/ship` still
runs up to 3 task subagents at a time. Scripts are run as
`python "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"`, with the fallback
`~/.claude/skills/claude-kit/scripts/<name>.py` when the variable is not
expanded. Report once, at the end.

## Stop rules

These are the only reasons to stop. When one fires, report the reason and end
without launching any child.

- `claude` is missing or `claude --version` is older than 2.1.259.
- `git fetch origin` fails in step 1.
- `--max` is below 1.
- Every spec is excluded (in step 1 or step 2).
- `parallel-plan.py specs` exits non-zero in step 3 (report its stderr).

## Steps

1. **Pre-flight.** Check `claude --version` (2.1.259 or later, needed for
   `--permission-prompts`), run `git fetch origin`, and check `--max`. The
   **main checkout** is the first entry of `git worktree list`. If this
   session is worktree-isolated, leave the worktree first (`ExitWorktree`
   with `keep`), because later steps run commands against the main checkout.
   Resolve each spec argument to an absolute path and compare paths after
   normalising separators and drive-letter case, by whole path components
   (as Python's `Path.is_relative_to` decides). Exclude, with the reason, and
   continue with the others:
   - a spec that does not exist: `not found`;
   - a spec not under the main checkout's root, or under the root of another
     entry of `git worktree list` (such as `.claude/worktrees/...`):
     `outside the main checkout`;
   - a spec whose `git -C <spec's folder> rev-parse --show-toplevel` is not
     the main checkout's root (a separate repository nested under it):
     `not in this repository`;
   - a spec whose resolved path repeats an earlier argument: `duplicate`.

   Refer to every remaining spec by its path relative to the main checkout,
   with `/` separators; steps 2–4 use that path. Record the start time (UTC)
   and the output of `git worktree list --porcelain`.
2. **Gate.** For each spec, run `spec-lint.py --verify-record <spec>`.
   - With `--dry-run`: only report each result. Never run the gate, edit a
     spec, or write a record. A dry run is read-only except for `git fetch`
     (step 1), which updates remote-tracking refs.
   - Otherwise, a spec that does not print `ok:` goes through the
     `claude-kit:spec-gate` skill, steps 1–6, in this session. A spec that
     passes is set to `approved`. A spec that fails is excluded and reported
     with its record's Open items; the others continue.
   - Then record each remaining spec's **title**: the first line outside code
     fences that starts with `# `, with the `# ` prefix and trailing
     whitespace removed. Step 5 uses this recorded title and never re-reads
     the file, because a child `/ship` deletes the main checkout's untracked
     copy. A spec whose title repeats an earlier one is excluded as
     `duplicate title` (with `--dry-run`, it is only reported).
3. **Group.** From the main checkout, run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" specs <specs> --max N`
   on the specs not excluded (with
   `--dry-run`, on every spec not excluded in step 1). With `--dry-run`, print
   the gate results, the waves, the overlaps, and the exact child command for
   each spec, with the log directory step 4 would create (from the step 1
   start time, not created), then stop without launching anything.
4. **Run.** Create `<tmp>/claude-ship-many/<repo>-<timestamp>/` (`<tmp>` the
   OS temp directory, `<repo>` the main checkout's directory name,
   `<timestamp>` the start time as `YYYYMMDD-HHMMSS`). For each wave, in
   order, start one background Bash command per spec, with the main checkout
   as its working directory and a 2-hour timeout:

   ```
   claude -p "/claude-kit:ship <spec>" --permission-mode auto --permission-prompts none --output-format json > <log>/<log-name>.json 2> <log>/<log-name>.err
   ```

   `<spec>` is the path relative to the main checkout. `<log-name>` is the
   spec's file name without `.md`; repeated file names get `-2`, `-3`, … in
   argument order. Wait for every command in the wave to end before starting
   the next wave. One child failing never stops the others or later waves.
5. **Collect.** An excluded spec keeps status `excluded`. For each child that
   ran:
   - Its exit code comes from the background command's result; its cost
     (`total_cost_usd`) and `result` text from its JSON file, when the file
     holds a JSON object.
   - Its PR: run
     `gh pr list --state all --limit 50 --json url,title,state,mergeCommit,headRefName,createdAt`
     and keep the PRs whose `title` equals the recorded title exactly
     (compared as strings) and whose `createdAt` is after the start time. If
     several remain, take the newest; if none, the child has no PR.
   - Its status is the first that applies: `merged` (its PR is `MERGED`),
     `timed out` (the timeout ended the command), or `stopped` (any other
     ending, including no PR; its handoff says why).
   - For `timed out` and `stopped` children, list the PR's head branch (if
     any) and any worktree on that branch as that child's leftovers. Also
     list as run-level leftovers every `feat/` worktree in
     `git worktree list --porcelain` that was not in the step 1 list. Never
     delete them.
6. **Finish.** For each `timed out` child, look up its PR once more as in
   step 5. If it is now `MERGED`, set the status to `merged`, fill in the PR
   and merge commit, and drop its head branch from the leftovers; otherwise
   keep `timed out` and note that it may still be running. Run
   `git fetch origin`, then bring local `main` up with `/ship` step 11's safe
   fast-forward rule. Report one table (spec, wave, status, exit code, PR,
   merge commit, cost, log file), the total cost, every `overlaps` entry from
   step 3, and the leftovers.
