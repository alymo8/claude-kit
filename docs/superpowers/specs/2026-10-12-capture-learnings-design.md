# Capture learnings when a feature is finished

- **Status:** approved
- **Date:** 2026-10-12

## Purpose

A session learns things a later session would otherwise rediscover or get
wrong: a gotcha, a command that works when the obvious one does not, a
convention the user set, a correction to how Claude works. Today those
survive only when someone happens to write them down; `/handoff` step 1
moves findings, decisions and plan changes, but nothing records operational
learnings when a feature ends, and `/ship` and `/ship-fast` have no such
step at all.

This change makes capturing learnings part of finishing a feature or
change: a `capture-learnings` skill, invoked by `/ship` and `/ship-fast`
before the PR is opened and by the workspace rule for manual finishes,
writes each learning to the home the conventions already define, inside the
feature's PR.

## Scope

**In:**
- `plugin/skills/capture-learnings/SKILL.md` (new): the skill (see Design).
- `plugin/commands/ship.md`: step 7 (PR) starts with the learnings step;
  step 12 (Report) gains a Learnings line.
- `plugin/commands/ship-fast.md`: step 7 (PR) starts with the learnings
  step; step 9 (Report) gains a Learnings line.
- `CLAUDE.md` (workspace): the "A feature is not finished until its
  workspace is gone" paragraph adds the learnings step for manual finishes.
- `conventions/project-memory.md`: a short "Capturing learnings" section
  that names the skill and the routing table, so the convention and the
  skill agree.
- `knowledge/decisions/<next>-capture-learnings-at-feature-finish.md`: an
  ADR for the decisions below.
- `tests/test_capture_learnings_skill.py` (new); additions to
  `tests/test_ship_command.py` and `tests/test_ship_fast_command.py`.
- `README.md`: one line naming the skill where the other skills are listed.
- `plugin/.claude-plugin/plugin.json`: minor version bump.

**Out:**
- Any `SessionEnd` or `Stop` hook. A hook cannot run a skill once the model
  has stopped, and a headless `claude -p` over the transcript costs tokens
  on every session and writes unreviewed files.
- `/handoff`: unchanged. Its step 1 already moves durable findings.
- `/ship-many`: unchanged. Each child runs `/ship`, which runs the step.
- `superpowers:finishing-a-development-branch`: not owned by the kit; the
  workspace `CLAUDE.md` rule covers manual finishes instead.
- Back-filling learnings from past sessions or past PRs.

## Design

### The skill

`plugin/skills/capture-learnings/SKILL.md`, frontmatter:

- `name: capture-learnings`
- `description:` starts "Use when /ship or /ship-fast reaches its PR step,
  or when a feature or change is finished by hand before its branch
  merges." and states that it writes the session's learnings into the
  feature branch.
- No `disable-model-invocation`; the user can also invoke it by name.

Body, in this order:

1. **Collect candidates** from this session's work on the feature: user
   corrections and stated preferences, commands that failed before one
   worked, surprises (CI failures with a non-obvious cause, platform
   quirks, things that look wrong but are intentional), and conventions the
   user set. Also read the branch's handoff file
   (`.claude/handoffs/<branch>.md`, `/` written as `_`) when present,
   because a feature may span sessions.
2. **Filter.** Keep a candidate only if a competent newcomer to the repo
   would otherwise waste time on it or get it wrong. Drop anything the
   commit messages, the diff, the spec, the plan or an existing ADR already
   says. Drop anything already recorded at its destination (read the
   destination first; update an existing entry instead of adding a
   duplicate). Zero learnings is a valid result: write nothing and report
   "none".
3. **Route** each kept learning by kind:

   | Kind | Destination |
   |---|---|
   | Repo command, gotcha, or convention | The repo's root `CLAUDE.md`, in the matching section of the kit's project template (Setup / prerequisites; Build, run, test; Conventions; Gotchas) |
   | Durable finding about the domain or the code | `knowledge/<topic>.md` (existing file on the topic, else a new one), linked from `CLAUDE.md` only if it is something every session needs |
   | A decision with alternatives that a later change could reopen | A new ADR under `knowledge/decisions/`, following the repo's `knowledge/decisions/0000-template.md` (else its `knowledge/decisions/README.md`, else the format of its newest ADR) and the repo's next number. Not on a `poc/` branch (a `/ship-fast` POC, where ADRs are not required): there list the decision in the summary instead |
   | A preference about how Claude should work that holds beyond this repo | Auto-memory (the session's memory directory and its `MEMORY.md` index, following the session's memory instructions); never a tracked file |

   If the repo has no root `CLAUDE.md`, create it holding only the new
   entries under a `## Gotchas` (or matching) heading. If `CLAUDE.md` has more than 100 lines
   after the addition (a file already over that limit always qualifies), put the entry in
   `knowledge/` and link it from `CLAUDE.md` instead. If the repo has no
   `knowledge/` folder, put durable findings in `CLAUDE.md` under
   `## Gotchas`. If it has no `knowledge/decisions/` folder, write no ADR:
   list the decision in the summary instead. If the session has no
   auto-memory directory, list preference learnings in the report instead
   of writing them.
4. **Write and commit.** Entries are terse and imperative, with exact
   commands in code spans or fences. Never write secrets, credentials,
   connection strings or personal data, and no names of other private
   repos or of user accounts (applied to every repo, since visibility can
   change). Commit the repo files on the feature branch as
   one commit, subject `Capture learnings`, with the session's attribution
   line. Auto-memory writes are not committed.
5. **Return** a Learnings summary for the caller's report: one line per
   learning, `<destination>: <learning>`; then one line per decision or
   preference listed instead of written (step 3), marked `not written:`;
   then, when nothing was written, `none` followed by each dropped
   candidate with the step-2 rule that dropped it.

No approval pause: the learnings ride in the feature's PR and are visible in
its diff, and the summary is in the report.

### `/ship`

Step 7 (PR) begins: "First run the `claude-kit:capture-learnings` skill; if
it committed, push before creating the PR." The step numbers do not change.
Step 12 (Report) adds "the Learnings summary from step 7".

### `/ship-fast`

Step 7 (PR) begins: "First run the `claude-kit:capture-learnings` skill,
then `git push -u origin poc/<slug>`." That push carries any learnings
commit, so no extra push is needed.
Step 9 (Report) adds "the Learnings summary from step 7". The Cleanup
section is unchanged.

### Manual finishes

In the workspace `CLAUDE.md`, the paragraph starting "A feature is not
finished until its workspace is gone." gains, before cleanup: "Before the
branch merges, run the `claude-kit:capture-learnings` skill so the
feature's learnings land in its PR."

### Convention

`conventions/project-memory.md` gains a "Capturing learnings" section of at
most 12 lines: learnings are captured when a feature finishes, by the
`capture-learnings` skill, routed by the table above (stated in words, with
a pointer to the skill as the single source of the table), and land in the
feature's PR.

## Decisions

- **At feature finish, not session end.** Verified with the user. A
  `SessionEnd` hook cannot run the model; finishing a feature is a natural
  boundary every flow already passes through.
- **In the PR, before merge.** Verified with the user. The learnings land
  in the same squash commit and are reviewable in the diff; capturing after
  merge would need a second PR or a direct push to `main`.
- **No approval pause; listed in the report.** Verified with the user.
  Keeps `/ship`'s no-check-in promise.
- **`/handoff` unchanged.** Verified with the user.
- **One flow-invoked skill, not copies in each flow.** Verified with the
  user. Commands run in other repos, which cannot read the kit's
  `conventions/`; only `plugin/` is reachable. Same pattern as
  `parallel-tasks`.
- **Route by kind to existing homes.** Verified with the user. No new
  learnings file to grow without bound or overlap `CLAUDE.md`.

## Testing

`tests/test_capture_learnings_skill.py`:
- `test_frontmatter`: `name` is `capture-learnings`, `description` starts
  with "Use when" and mentions `/ship` and `/ship-fast`, no
  `disable-model-invocation`.
- `test_routes_every_kind`: the body names `CLAUDE.md`, `knowledge/`,
  `knowledge/decisions/` and `MEMORY.md`.
- `test_none_is_a_valid_result`: the body contains "none" as a report
  value, says to write nothing in that case, and says to list each dropped
  candidate with the rule that dropped it.
- `test_missing_homes_have_fallbacks`: the body names `0000-template.md`
  and says what to do when `knowledge/` or `knowledge/decisions/` is
  missing.
- `test_never_writes_secrets`: the body forbids secrets and personal data.
- `test_commits_on_the_feature_branch`: the body contains the commit
  subject `Capture learnings` and says auto-memory is not committed.

`tests/test_ship_command.py`:
- `test_learnings_are_captured_before_the_pr`: `_step(7)` contains
  `claude-kit:capture-learnings`, and it appears before `gh pr create`.
- `test_report_lists_learnings`: `_step(12)` contains "Learnings".

`tests/test_ship_fast_command.py`: the same two tests, with `_step(7)`
before `git push -u origin poc/<slug>` and `_step(9)`.

`tests/test_docs.py` (or the existing doc test that fits): the workspace
`CLAUDE.md` and `conventions/project-memory.md` both name
`capture-learnings`.

## Success criteria

1. `pytest` passes (full suite), and `ruff check plugin tests` and
   `ruff format --check plugin tests` pass.
2. All tests listed under Testing exist and pass: `pytest tests/test_capture_learnings_skill.py tests/test_ship_command.py tests/test_ship_fast_command.py tests/test_docs.py` exits 0.
3. **Live check.** The kit loads commands and skills from the main
   checkout, so the run that lands this spec still reads the old `ship.md`.
   Before opening this change's PR, follow the new `SKILL.md` as written in
   the feature worktree, on that run's own session: the PR either contains
   a `Capture learnings` commit whose entries are each in their routed
   destination, or the report says `Learnings: none` with the candidates it
   dropped and why. Either way the report has the Learnings line.
4. The kit stays free of private repo names and usernames in tracked files:
   check with `git grep` for them before each commit, as for every kit change.
