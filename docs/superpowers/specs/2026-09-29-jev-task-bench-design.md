# jev task bench: 10 real tasks, with and without jev

- **Status:** implemented
- **Date:** 2026-09-29
- **Extends:** the jev triage pilot
  (`docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md`)

## Purpose

Prompt-level labelling turned out to be a poor measure: most sampled prompts
were replies or follow-ups that mean nothing out of context, and a per-prompt
score cannot show whether a whole task went better. The question that matters
is task-level: **given a real task, does Claude do it better, and at what cost,
when jev's hints are on?**

This bench replays 10 real past tasks from the user's own sessions, runs each
with jev hints on and off, and compares quality and cost.

## Scope

**In:**

- A generic harness, `plugin/scripts/jev-bench.py` (in the kit, public), with
  subcommands `check`, `run`, `grade` and `report`.
- 10 task files, authored from the user's session history and kept **local**
  (`~/.claude/claude-kit/jev/bench/tasks/`). They contain private prompts, repo
  paths and commits and never enter a repository.
- A safe, isolated sandbox per run, a simulated user, blind grading, and a cost
  and quality report.
- Running the **no-jev arm now** (20 runs). The jev arm (20 runs) runs when a
  `TYPESAFE_API_KEY` is available, with the same tasks, commits and judge.

**Out:**

- Changes to the jev hook, its questions or thresholds.
- A stand-in judge (OpenRouter) for the jev arm.
- Parallel runs. Runs are sequential, to avoid rate limits and clashes over
  local databases.
- Reproducing live-app or dev-database state. Bugs that needed the running app
  are judged on the code change against the reference, not by running the app.

## The tasks

Chosen by the user from a shortlist of their sessions since 2026-08-01, across
four repositories (three private projects and this kit). The list, with repo
names and prompts, lives only in the local task files; this public spec records
the mix:

| Type | Tasks |
|---|---|
| new feature | 3 (one of them in this kit) |
| bug | 2 |
| vague (bug, UX, or vague + feature) | 3 |
| key decision (one with a feature, one a verification) | 2 |

### Task file (`<id>.json`, local)

| Field | Content |
|---|---|
| `id`, `type` | e.g. `t01`, `feature` / `bug` / `vague` / `decision` |
| `repo` | absolute path of the repository |
| `base_commit` | the commit the real session started from |
| `reference` | commit range of what the real session delivered (`<base>..<sha>`) |
| `prompt` | the user's original opening prompt, verbatim |
| `brief` | what the user actually wanted, and the facts and choices they gave in the real session, for the simulated user |
| `rubric` | 3–6 pass/fail checks for "done right", derived from what the real session delivered |
| `verify` | optional offline command (e.g. a unit test run); empty when none works offline |

Task files are drafted by Claude from the real session and commits, and **the
user approves every brief and rubric before any run**. `check` validates each
file: fields present, repo exists, both commits exist, rubric has 3–6 items.

## Design

### Sandbox (one per run)

- Location: `Desktop/Github/.jev-bench/<task>-<arm>-<n>/`. This is inside the
  workspace, so the workspace `CLAUDE.md` rules (the ones jev reinforces) still
  apply, and it is ignored by the kit's whitelist `.gitignore`.
- A local `git clone` of `repo`, checked out at `base_commit`, then
  `git remote remove origin`, so nothing can be pushed.
- Child environment: `os.environ` minus any variable whose name matches
  `TOKEN|SECRET|PASSWORD|KEY|SUPABASE|AZURE|AWS|GH_|GITHUB|DATABASE_URL`.
  `TYPESAFE_API_KEY` is re-added for the jev arm only. `CLAUDE_KIT_JEV` is set
  to `active` (jev arm) or `off`.
- Denied tools, passed as `--disallowedTools`: `Bash(git push:*)`,
  `Bash(gh:*)`, `Bash(supabase:*)`, `Bash(npx supabase:*)`, `Bash(az:*)`,
  `Bash(vercel:*)`, and `PowerShell` and `Bash` forms of `Invoke-Item`,
  `explorer` and `start`. The last three matter because the workspace
  `CLAUDE.md` asks Claude to open files for the user, which would otherwise pop
  up windows on every run.
- Permission mode: `bypassPermissions`, inside the sandbox only. Deny rules
  still apply in that mode; the spike confirms it.
- The sandbox is deleted after grading unless `--keep` is given.

### One run

1. `claude -p "<prompt>" --model opus --output-format json
   --permission-mode bypassPermissions --disallowedTools … --max-budget-usd
   <cap>`, run in the sandbox. This records `session_id`, `total_cost_usd`,
   `num_turns`, `duration_ms` and the final `result` text.
2. The simulated user reads the final text and either replies or says `DONE`.
3. When it replies: `claude -p "<reply>" --resume <session_id> …` and back to 2.
   Stop at `DONE`, after 6 replies, when the per-run budget is spent, or on an
   error.
4. Record: status (`done` / `max_replies` / `budget` / `error`), cost, turns and
   duration summed over the calls, number of replies, the simulated user's cost
   (separate), and the number of jev evaluations (log records with scores for the
   run's session). Also save the diff (`git diff <base_commit>` including
   uncommitted changes, plus `git log <base_commit>..HEAD`), the final text, and
   the session id so the transcript can be found. Written to
   `~/.claude/claude-kit/jev/bench/results/<task>-<arm>-<n>.json`.

### Simulated user

A separate `claude -p --model haiku` call in an empty temporary directory with
all tools denied. It gets the brief, the original prompt, and Claude's latest
message, with the instruction: reply as this user would, in at most three
sentences; answer questions from the brief; approve reasonable specs and plans;
when asked to choose, choose what the user chose in the real session; never write
code; reply exactly `DONE` when the task looks finished or nothing is being
asked. Its cost is recorded separately and is identical in kind for both arms.

### Grading (`grade`)

- **Rubric score.** One `claude -p --model opus` call per run, blind to the arm.
  It gets the brief, the rubric, the reference diff (`git diff <reference>` in the
  original repo) and the run's diff and final text. Any line mentioning jev is
  redacted, and diffs over 60,000 characters are cut with a marker. It returns
  JSON: one pass/fail per rubric item, an overall score from 1 to 5, and a short
  rationale. A malformed reply is retried once, then recorded as a grading error.
- **Head-to-head.** For each task, jev run *n* against no-jev run *n*, shown as
  A and B in random order, with the verdict mapped back afterwards. It returns
  JSON: `{"winner": "A" | "B" | "tie", "reason": …}`.
- **Rule-following.** From the run's transcript, using the existing *preflight*
  and *asked* definitions from `jev-eval.py`: pre-flight skipped on a
  `new_feature`/`decision` task, and no question asked on a `vague`/`decision`
  task.
- **`verify`.** When set, run in the sandbox and record pass/fail.
- Every grade goes to `grades.csv` so the user can check any of them.

### Report (`report`)

Per task and overall, jev vs no jev: rubric pass rate and mean score,
head-to-head win rate (jev wins / ties / losses), rule misses, `verify` pass
rate, cost per task (Claude, jev evaluations, simulated user and judge, each
separate), turns, replies and wall time. The reading rule is printed with it:
jev is worth keeping only if quality is equal or better, it wins more than half
the head-to-heads, and it adds under about 10% Claude cost. With 20 runs per arm
only a large effect can show, and the report says so. While the jev arm has not
run, the report shows the no-jev arm alone as the baseline.

### Hardening added after review, and known limits

- **Pushes and credentials.** Every child process gets `GIT_CONFIG_PARAMETERS`
  with `credential.helper=` (git uses no stored credentials) and
  `pushInsteadOf` rules that send any push to `https://invalid.invalid/`, even
  to a remote the run re-adds. Also `GIT_TERMINAL_PROMPT=0`,
  `GCM_INTERACTIVE=Never`, and `GH_CONFIG_DIR` and `NPM_CONFIG_USERCONFIG`
  pointing at an empty directory. `cmd`, `pwsh`, `powershell` and the
  `npx`/`pnpm dlx`/`bunx` forms of `supabase` and `vercel` are denied as well.
- **No MCP servers or connectors.** Every call passes `--strict-mcp-config`.
  Without it, headless runs loaded the user's claude.ai connector tools.
- **Guard prompt.** Task runs get `--append-system-prompt` (`GUARD`), identical in
  both arms: stay inside the current directory, don't copy sibling repos'
  `.env` files, don't push, deploy or open windows.
- **Cost accounting.** `claude -p` reports `total_cost_usd` and `num_turns`
  cumulatively for a session, `--resume` included (measured). Each session
  therefore counts once at its latest value, and `--max-budget-usd` gets the run
  budget minus what other sessions spent. Wall time is measured by the harness.
  A call that crashes or times out is charged at its whole remaining cap toward
  `--max-total-usd` (`uncounted_usd`), since its real cost is unknown.
- **Worktrees.** The run's diff covers every git worktree of the sandbox, each
  labelled by branch, and the log covers every branch. The workflow builds
  features in worktrees, so the main tree alone would miss the work. Kit-hook
  output (`.claude/handoffs/`, the spec index) is left out of the diff.
- **Process trees.** A timed-out call is killed with everything it started
  (`taskkill /T` on Windows). A sandbox that cannot be removed is recorded in
  `cleanup_error` and does not stop the batch.
- **Blind grading.** Lines mentioning jev, triage, TypeSafe or the hint phrases
  are dropped silently in both arms. A marker would itself reveal the arm.
- **Known limit: no filesystem isolation.** `bypassPermissions` allows reads
  and writes anywhere. The guard prompt asks Claude to stay in the sandbox but
  cannot enforce it, and deny rules on paths are easy to bypass (e.g. `cat` via
  Bash). Because sandboxes sit inside the workspace, sibling repositories and
  their `.env` files are reachable, and for the kit task the real kit repo
  is the sandbox's parent. This is a known limit to settle with the user before
  any real run.

### Budget

- Per run: `--max-budget-usd 10` on each call, and the harness stops the run once
  the summed cost reaches $10.
- Per `run` invocation: `--max-total-usd`, default $150 (about 20 runs). The
  harness refuses to start a run that could push the total over the cap.

## Decisions

| Decision | Chosen | Rejected, and why |
|---|---|---|
| Unit of evaluation | Whole real tasks | Per-prompt labels: replies and follow-ups carry no context |
| Task source | Replay 10 of the user's real sessions | Invented tasks: less realistic, no known intended outcome |
| User side | Simulated user (Haiku) with a brief from the real session | Fixed answers: can't answer specific questions. User drives: 40 sessions of their time |
| Runs and model | 2 runs per arm, Opus | 1 run: can't separate effect from noise. Sonnet: not the user's model |
| jev arm timing | No-jev arm now, jev arm when the key arrives | Stand-in judge: doesn't measure jev |
| Sandbox location | Inside `Desktop/Github` so workspace rules apply | A temp dir: loses the rules jev is meant to reinforce |
| Grading | Blind Opus judge with rubric and reference, plus head-to-head | Judge only, or user only: judge-only lacks a reference; user-only is slow and not blind |
| Task data | Local only | In the repo: private prompts in a public repo |
| **Budget caps** (confirm) | $10 per run, $150 per `run` invocation | No caps: 40 Opus runs with tool loops can run away |

## Success criteria

### Build is done and correct when

- `pytest` passes, with no network and no real `claude` calls. The harness takes
  the `claude` command as an injectable runner, and tests use a fake one.
  - Sandbox: clones at `base_commit`, has no remote, lives under the bench root,
    and is removed after the run unless `--keep`.
  - Environment: secret-looking variables are removed; `TYPESAFE_API_KEY` is
    present only in the jev arm; `CLAUDE_KIT_JEV` is set per arm.
  - Every denied tool is passed on every call; the model and budget flags are
    passed.
  - The loop stops at `DONE`, at 6 replies, when the budget is spent, and on an
    error, each with the right status, and costs are summed.
  - The result JSON has every field. Task files that fail validation are rejected
    by `check`.
  - Grading: jev lines are redacted, long diffs cut, a malformed judge reply is
    retried once then recorded as an error, and the head-to-head order is
    randomised and mapped back correctly.
  - Report arithmetic is right on a fixture of results and grades, including the
    baseline-only case.
- `ruff check plugin tests` and `ruff format --check plugin tests` pass; CI is
  green.
- No private prompt, repo name, path or username in any tracked file, fixtures
  included.

### Spike (before any real run)

One real headless run in a sandbox of the kit repo (a throwaway prompt), with
`CLAUDE_KIT_JEV=shadow` and no key. It passes when:

- jev's log gets a record for that session with `error: missing_key`, which
  proves the hook fires in headless mode;
- `git push` is refused, and an `Invoke-Item` attempt is refused;
- the JSON output has `session_id` and `total_cost_usd`, and `--resume` continues
  the session.

### Task authoring

10 task files that pass `check`, with base and reference commits verified in
each repo, and every brief and rubric approved by the user.

### No-jev arm (this change)

20 runs (10 tasks × 2) each end with a recorded status, total Claude cost stays
within the cap, every run is graded, and `report` prints the baseline. The jev
arm, head-to-heads and the verdict follow when the key arrives.
