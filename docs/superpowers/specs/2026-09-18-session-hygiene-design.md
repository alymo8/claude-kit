# Session hygiene: handoff, context meter, lean exploration

- **Status:** implemented
- **Date:** 2026-09-18

## Purpose

The kit's five conventions protect quality. None of them addresses cost. A
measurement of 67 sessions across five project repos (transcripts under
`~/.claude/projects/`, analysed with the script this spec adds) showed where the
tokens go:

| Observation | Value |
|---|---|
| Fresh input tokens, all sessions | negligible |
| Cache-read input tokens, all sessions | about 4 billion |
| Average context per API call | 260k tokens |
| Median assistant turns per session | 181 (max 704) |
| Context at the end of the longest sessions | 300k to 850k tokens |
| Compaction events | 0 (the 1M window never forces one) |
| Share of tool output produced by Bash | 82% |
| Share of Bash output from cat, sed, echo, grep, ls, find, for | about 72% |
| Redundant re-reads of the same file within a session | 7 in total |

The cost is **context size multiplied by turn count**. Sessions run for hundreds
of turns, each turn re-sends everything accumulated so far, and what accumulates
is whole-file exploration output that was needed once. Sessions run long because
starting fresh is expensive: nothing carries over except `CLAUDE.md`.

Simulating a policy of "restart the session with a small handoff when context
passes a cap" against the same transcripts:

| Restart cap | Total input tokens | Versus actual |
|---|---|---|
| none (actual) | 4.05 B | |
| 300k | 2.34 B | 42% fewer |
| 200k | 1.77 B | 56% fewer |
| 150k | 1.42 B | 65% fewer |

(assuming a restart costs 45k tokens of prefix plus handoff.)

This spec makes restarting cheap and visible, and gives Claude a discipline for
exploring without bloating the main context. It adds a sixth convention,
**session hygiene**, with the plugin pieces that make it mechanical. It builds on
`2026-09-14-kit-foundation-design.md` (plugin, hooks, tests) and
`2026-09-15-project-scaffolder-design.md` (templates, commands).

## Scope

**In:**

1. A per-branch **handoff file**, gitignored, written by a `/handoff` command and
   kept current by a SessionEnd hook.
2. A **SessionStart hook** that injects the handoff into a fresh session.
3. A **context meter**: a status line script (zero token cost) and a
   UserPromptSubmit hook that nudges once per threshold crossed.
4. A **`lean-context` skill** for exploration and long-output discipline, with a
   permanent pointer in the workspace and project `CLAUDE.md`.
5. A **`token-report.py`** script that reproduces the measurement above.
6. `conventions/session-hygiene.md`, README and `CLAUDE.md` updates, template and
   scaffolder updates, installer support for the status line, tests, two ADRs.

**Out:**

- Any hook that truncates, filters or rewrites tool output. Hooks here only add
  context and write files; nothing decides what Claude never sees.
- Service-backed memory (knowledge graphs, vector stores, daemons). Re-reads are
  already rare; the gap is carry-over between sessions, which a file covers.
- The broader exploration *convention* (subagent-first exploration as a rule for
  every repo). The skill ships now; whether to make it a hard convention waits for
  a re-measurement after two weeks of use, so the handoff's effect is attributable.
- Automatic compaction or automatic session termination. The nudge is advisory.
- Changes to superpowers skills (`finishing-a-development-branch` and friends).

## Design

### 1. Handoff file

**Location.** `<work-tree>/.claude/handoffs/<branch>.md`, where `<work-tree>` is
`git rev-parse --show-toplevel` for the session's cwd (so a worktree gets its own
file) and `<branch>` is the branch name with every character outside
`[A-Za-z0-9._-]` replaced by `_` (`feature/foo` becomes `feature_foo`; detached
HEAD becomes `detached-<sha7>`). The directory is gitignored. It vanishes with a
removed worktree, never appears in a PR diff, and needs no cleanup step at merge.

**Format.** Markdown, target under 80 lines (about 3k tokens). Sections in this
order; the command writes all of them, the snapshot hook touches only **State**
and the **Written** line.

```
# Handoff: <branch>

- **Written:** 2026-09-18T14:05 by /handoff | by session-end snapshot
- **Spec / plan:** docs/superpowers/plans/2026-09-18-foo.md (or "none")

## Task
One paragraph: what is being built and why. No references to chat.

## State
<!-- generated; do not edit -->
- branch: feature/foo  (worktree: C:/.../.claude/worktrees/foo)
- upstream: origin/feature/foo, ahead 3, behind 0
- dirty: src/a.ts, tests/a.test.ts
- last commits: 1a2b3c4 Add parser, ...
- PR: https://github.com/<owner>/<repo>/pull/12 (or "none")

## Done this session
- ...

## Next
1. Concrete, ordered steps in the voice of a plan.

## Files that matter
- `src/a.ts`: why it matters

## Commands that work
```
pnpm vitest run tests/a.test.ts
```

## Open questions
- ...

## Moved to durable homes
- knowledge/foo.md, ADR 0009, or "nothing"

## Recent prompts
<!-- written by the session-end snapshot only when no /handoff was run -->
```

**Lifecycle.** Created or fully rewritten by `/handoff`; State refreshed on every
session end; injected on the next `startup` or `clear` when the branch matches and
the file is younger than 7 days; ignored otherwise. Nothing deletes it (ADR 0007):
stale files are harmless because injection is keyed by branch and age, and the
convention says `.claude/handoffs/` may be emptied at any time.

### 2. `handoff.py` and the `/handoff` command

`plugin/scripts/handoff.py <subcommand> [--cwd DIR]`:

- `path`: print the handoff path for the current branch (creates nothing).
- `state`: print the State section for the current branch to stdout, built from
  `git rev-parse`, `git status --porcelain`, `git rev-list --count` against the
  upstream, `git log --oneline -5`, and `gh pr view --json url` when `gh` is on
  PATH (skipped silently otherwise; 10 s timeout).
- `snapshot [--prompts FILE]`: create the file with a header, State and, when
  given, a Recent prompts section holding up to the last 5 user prompts; or, if
  the file exists, replace only the text between `## State` and the next `## `
  heading, update the **Written** line to "by session-end snapshot", and leave
  every other byte untouched.

Exit 0 on success; 1 outside a git work tree; errors on stderr. No output on
stdout except what the subcommand prints.

`plugin/commands/handoff.md` (frontmatter `description`, no arguments). Body:

1. Before writing anything ephemeral, ask: did this session produce something
   durable? A finding goes to `knowledge/`, a locked decision to an ADR, a change
   of plan to the plan file. Do that first and link it under "Moved to durable
   homes".
2. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/handoff.py" path` and `... state`.
3. Write the file at that path with every section of §1, State pasted verbatim,
   the rest from this session, in the self-contained voice the plans convention
   requires: concrete paths and commands, no "as discussed".
4. Keep it under 80 lines; if Next has more than 8 steps, the plan file is where
   they belong.
5. End the reply with the path and: "Run `/clear` to start fresh; the next
   session loads this handoff automatically."

### 3. Hooks

All hooks follow ADR 0007: Python, event JSON on stdin, every exception caught and
reported on stderr, exit 0 always, never delete. Registered in
`plugin/hooks/hooks.json` alongside the two existing hooks.

**`handoff_snapshot.py`** on `SessionEnd` (all reasons). Reads `cwd` and
`transcript_path` from stdin; extracts the last 5 user prompts from the transcript
tail (best effort, the transcript is written asynchronously); runs `handoff.py
snapshot` for `cwd`. Outside a git repo: exit 0, nothing written.

**`handoff_inject.py`** on `SessionStart`, matcher `startup|clear`. If a handoff
exists for the current branch and its **Written** timestamp is within 7 days,
print as `additionalContext`:

```
<handoff age="3h" path=".claude/handoffs/feature_foo.md">
Handoff from the previous session on this branch. Read it before exploring.
The State section was generated at session end; verify it against git before
trusting it.
<file contents>
</handoff>
```

Otherwise print nothing, except one line naming any other handoffs under 7 days
old for other branches ("Handoffs exist for: feature_bar (2d)"), so a session
opened on the wrong branch notices.

**`context_nudge.py`** on `UserPromptSubmit`. Reads the transcript **tail** (the
last 256 KiB, never the whole file; transcripts reach tens of MB) to find the last
`assistant` record with a `usage` block, and computes
`input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. Thresholds:
first at `CLAUDE_KIT_NUDGE_AT` (default 300000), then every `CLAUDE_KIT_NUDGE_STEP`
(default 100000). The highest threshold already fired is stored in
`<scratchpad_dir>/claude-kit/nudge-level` (`scratchpad_dir` comes from the hook
input; fallback is the system temp dir keyed by `session_id`). When the current
context passes an unfired threshold, print `additionalContext` (about 40 tokens):

```
Context is at 312k tokens; every turn now re-sends all of it. At the next natural
boundary, run /handoff and then /clear. (claude-kit session hygiene)
```

and the same text as `systemMessage` so the user sees it too. Otherwise print
nothing. Reading the tail and parsing at most a few hundred lines keeps the hook
well under 100 ms per prompt.

### 4. Status line

`plugin/scripts/statusline.py` reads the status line JSON from stdin and prints
one ASCII line:

```
ctx 312k/1M 31% | $14.20 | feature/foo
```

Fields: `context_window.total_input_tokens`, `context_window.context_window_size`,
`context_window.used_percentage`, `cost.total_cost_usd`, and the branch from
`git rev-parse --abbrev-ref HEAD` in `workspace.current_dir` (blank on failure).
Nulls (before the first API call) render as `ctx -`; a malformed stdin prints an
empty line. The percentage is colored with ANSI codes: default below 30%, yellow to
60%, red above, so the meter is legible at a glance.

**Installation.** The status line is a user-level setting a plugin cannot ship.
`plugin/scripts/install-statusline.py [--settings PATH]` reads
`~/.claude/settings.json` (creating `{}` if missing), and if no `statusLine` key
exists, adds

```json
"statusLine": {"type": "command", "command": "python \"<skills-dir>/claude-kit/scripts/statusline.py\""}
```

writing back with `indent=2` and `ensure_ascii=False`. If the key exists it
prints "statusLine already configured; left unchanged" and exits 0. The path uses
the junction, not the checkout, so it stays valid if the checkout moves.
`install.ps1` calls it after creating or confirming the junction. Nothing else in
the settings file is touched, and the file is rewritten only when a key is added.

### 5. `lean-context` skill

`plugin/skills/lean-context/SKILL.md`, under 60 lines. Frontmatter:

```
name: lean-context
description: Use before exploring a codebase, reading files, or running anything
  with long output (tests, builds, logs, git). Keeps the main context small so
  every later turn stays cheap.
```

Rules, each one line plus a one-line example:

1. **Decide what you need before reading**: a symbol, a range, or the shape. Check
   the line count of an unknown file first; read whole only under about 200 lines.
2. **Search, don't sweep.** `grep -n` with 2 to 3 lines of context and a cap;
   `sed -n 'a,bp'` for ranges; never chain `cat` over several files for an
   overview.
3. **Broad questions go to an Explore subagent** ("every caller of X", "how does
   subsystem Y fit together") asking for conclusions and `file:line` pointers,
   not dumps. Its context is discarded; the main one stays lean.
4. **Long output goes to a file first.** Redirect tests, builds and logs to the
   scratchpad, then `tail` and `grep` for failures; the full log stays on disk.
5. **Never echo what you just wrote** and never re-read a file to confirm an edit.
6. **Write down what you learned** in the plan or the handoff rather than
   re-deriving it later in the session or in the next one.
7. **Watch the meter.** Past a nudge, finish the step, `/handoff`, `/clear`.

Permanent pointer, so the skill fires without being asked for. Workspace
`CLAUDE.md` gains a short section:

```
## Token discipline

The cost of a session is context size times turn count. Before exploring or
running anything with long output, use the `claude-kit:lean-context` skill. When
the context nudge appears, finish the current step, run `/handoff`, then `/clear`.
Details: conventions/session-hygiene.md.
```

`plugin/templates/project/CLAUDE.md` gains one line under Pointers: "Session
hygiene: use `claude-kit:lean-context` when exploring; `/handoff` before `/clear`."

### 6. `token-report.py`

`plugin/scripts/token-report.py [--project DIR | --all] [--cap N ...]`. Standard
library only. Locates transcripts under `~/.claude/projects/<encoded cwd>/` where
the encoding replaces every character outside `[A-Za-z0-9]` in the absolute path
with `-` (the same scheme Claude Code uses); `--all` scans every project folder.
For every `*.jsonl` it reads `assistant` records for usage and tool calls and
`user` records for tool results. Prints:

- sessions, assistant turns, total input tokens, average context per call;
- the ten largest sessions by end context (id prefix, turns, average and end
  context, cost when a `cost-state` record exists);
- tool output characters by tool, and Bash output by command family (first word,
  with the subcommand for git, gh, npm, pnpm, npx, python, pytest, ruff, node);
- results larger than 15k characters, with the command or path that produced them;
- the restart-cap simulation for each `--cap` (default 150000, 200000, 300000)
  with a 45k restart cost.

Exit 0; a missing or empty folder prints "no transcripts found" and exits 0.
Documented in the convention as the way to re-measure.

### 7. Convention, docs, templates, manifest

- **`conventions/session-hygiene.md`** (new, the sixth playbook): the cost model
  (context times turns, with the measured numbers above); sessions are units of
  work, not days; hand off at natural boundaries and whenever the meter says so;
  what a handoff must contain and what must instead go to knowledge, ADRs or the
  plan; lean exploration (pointer to the skill); how to re-measure with
  `token-report.py`; definition of done (a handoff exists whenever a branch is
  mid-flight; no session ends above the nudge threshold without one; a fresh
  session on the branch can continue from the handoff alone).
- **`conventions/README.md`**: sixth row in the table; the "how they fit" paragraph
  adds that session hygiene is the **cadence**, keeping each session cheap while
  the other five keep the work correct.
- **Workspace `CLAUDE.md`**: sixth bullet in the conventions list; the Token
  discipline section from §5; the pre-flight section notes that `/handoff` before
  `/clear` is the normal end of a working session.
- **`README.md`**: sixth playbook; plugin description adds the handoff command,
  the three new hooks, the status line, the skill and the report script; the
  installer paragraph mentions the status line addition.
- **Templates**: `project/.gitignore` adds `.claude/handoffs/` under the worktrees
  entry; `project/CLAUDE.md` gets the Pointers line. Adopt mode's `.gitignore`
  reminder lists `.claude/handoffs/` with the two existing patterns.
- **`plugin/.claude-plugin/plugin.json`**: version `0.2.0`; description updated.
- **ADRs**: `0008-handoff-is-gitignored-per-branch.md` (ephemeral, per work tree,
  never committed; rejected: committed on the feature branch) and
  `0009-no-service-backed-memory.md` (files plus hooks; rejected: knowledge-graph
  memory, because re-reads are rare and the cost is carry-over, not recall).

### 8. Tests

All in `tests/`, using `helpers.run_script` and `load_module`; git fixtures are
temporary repos created with `git init`.

- `test_handoff.py`: `path` sanitises `feature/foo` and detached HEAD; `state`
  lists dirty files, ahead/behind and commits, and omits the PR line when `gh` is
  absent (PATH cleared in the test); `snapshot` creates the file with State and
  Recent prompts; a second `snapshot` on a command-written file replaces only the
  State section and leaves every other line byte-identical; outside a git repo
  exits 1 and writes nothing.
- `test_handoff_snapshot.py`: hook with a fake transcript writes the file; hook
  with malformed stdin or a non-repo cwd exits 0 and writes nothing.
- `test_handoff_inject.py`: injects for a matching branch under 7 days; prints
  nothing for an 8-day-old file; prints the one-line notice for a file on another
  branch; exits 0 on malformed stdin and outside a repo.
- `test_context_nudge.py`: transcript fixtures with usage at 100k, 310k, 350k,
  420k: fires once at 310k, not at 350k, again at 420k; honours the environment
  variables; only reads the tail (a fixture with 5 MB of padding before the last
  record still fires); exits 0 with no output when the transcript is missing.
- `test_statusline.py`: the documented JSON renders the expected line; nulls
  render `ctx -`; malformed stdin prints an empty line and exits 0.
- `test_install_statusline.py`: adds the key to a temp settings file, preserves
  every other key and nested value; leaves an existing `statusLine` untouched;
  creates the file when missing.
- `test_token_report.py`: a synthetic project folder with two small transcripts
  yields the expected turn count, tool totals and cap simulation; an empty folder
  prints "no transcripts found" and exits 0.
- `test_plugin_manifest.py`: `hooks.json` registers the three new hooks with the
  right events and matchers; `commands/handoff.md` and
  `skills/lean-context/SKILL.md` exist with frontmatter containing `description`.
- `test_templates.py` / `test_scaffold.py`: `.gitignore` contains
  `.claude/handoffs/`; the Pointers line is present; adopt-mode output mentions
  the new pattern.
- `test_docs.py`: unchanged; the link check covers the new convention and ADRs.

## Decisions made during design

- **Session lifecycle first, exploration convention later.** The cap simulation
  gives a 42 to 65% estimate for the handoff; the exploration convention's effect
  cannot be simulated from the transcripts. Shipping the skill now but deferring
  the convention keeps the two-week re-measurement attributable.
- **Handoff is gitignored and per branch**, not committed (ADR 0008).
- **Hooks are conservative**: they add context and write files; none truncates or
  filters tool output. Quality risk from hidden output was judged worse than the
  tokens it would save.
- **First nudge at 300k**, then every 100k, configurable. Chosen over 150k to keep
  interruptions rare; the simulation still predicts about 42% fewer input tokens.
- **Status line is installed by the installer when absent**, never overwritten.
- **Session hygiene is a sixth convention**, not a section of project-memory: it
  is a practice with its own definition of done, and the memory file is meant to
  stay static.
- **No service-backed memory** (ADR 0009).
- **Measurement ships with the kit** so the outcome criteria can be checked with
  one command instead of a throwaway script.

## Success criteria

Merge gate:

1. `ruff check`, `ruff format --check` and `pytest` green locally and in CI on
   Ubuntu and Windows, including every test in §8.
2. Manual, in a real project repo: run `/handoff`, then `/clear`; the new session's
   first context contains the handoff. Set `CLAUDE_KIT_NUDGE_AT=20000`, cross it,
   and see exactly one nudge in the conversation and one system message. The
   status line shows tokens, percentage, cost and branch after the first reply.
3. `token-report.py --all` runs against the real transcript folders and prints the
   baseline numbers from Purpose within rounding.
4. No private repo names or the Windows username in tracked files (including the
   report script, which must not hard-code any path).
5. The work lands via a feature branch and PR; worktree and branch are removed.

Outcome check, about two weeks after merge, with `token-report.py --all`. These
are a hypothesis test, not a merge gate; the result decides whether the
exploration convention is worth specifying.

| Metric | Baseline | Target |
|---|---|---|
| Average context per API call | 260k | under 200k |
| Largest session end context | 850k | under 450k |
| Sessions ending above 400k context | 12 of 67 | none |
