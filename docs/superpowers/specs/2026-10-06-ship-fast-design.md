# `/ship-fast`: a light path from spec to PR for hour-sized POCs

- **Status:** approved
- **Date:** 2026-10-06

## Purpose

`/ship` is built for changes that land on `main` unattended: a spec gate, a
plan gate with a full writing-plans plan, a formal review round, CI watched
three times (branch, PR, `main`), a squash-merge and a verification of
`main`. For a proof of concept of about an hour, most of that time goes to
ceremony rather than the POC.

`/ship-fast <spec.md>` takes a spec to a working, tested pull request as
fast as possible while keeping the checks that catch broken work: test-first
on the core path, one correctness review, a smoke run of the real app
against the spec's acceptance criteria, and green CI on the PR. The user
reviews and merges the PR. Independent tasks run in parallel. It can start
a POC that has no repository yet.

## Scope

**In:**
- `plugin/commands/ship-fast.md` (new): the command.
- `plugin/skills/parallel-tasks/SKILL.md`: wording so it serves `/ship` or
  `/ship-fast` (it currently names only `/ship`).
- `tests/test_ship_fast_command.py` (new).
- `tests/test_plugin_manifest.py`: `ship-fast` in the expected commands and
  the user-only set.
- `README.md`: one sentence describing `/ship-fast` beside `/ship`.
- `knowledge/decisions/0021-ship-fast-skips-gates.md` (new) and its row in
  `knowledge/decisions/README.md`.
- `conventions/spec-driven-development.md`: one sentence that `/ship-fast`
  is the ungated path, citing ADR 0021.
- `CLAUDE.md`: one paragraph under "Building a new feature" describing
  `/ship-fast`, next to the `/ship` and `/ship-many` paragraphs.
- `plugin/.claude-plugin/plugin.json`: version 0.13.0, and its description
  mentions `/ship-fast`.

**Out:**
- Any change to `/ship`, `/ship-many`, the gates or `parallel-plan.py`.
- Merging the PR, verifying `main`, deleting the remote branch: the user
  merges, choosing delete-branch on merge to remove the remote branch. The
  command never names the merge command, so a test can forbid it.
- A brief-only input with no spec file.
- Running `/ship-fast` from `/ship-many`.

## Design

### Input

`$ARGUMENTS` is a spec path; if empty, the newest `*.md` under
`docs/superpowers/specs/` (named in one line). The spec is not gated and its
Status is not changed. The spec's acceptance criteria are its
`## Success criteria` section (or a section whose heading contains
"criteria" or "verification"). If the spec has none, that is a stop rule
(see below): `/ship-fast` does not invent what "done" means.

An optional header line in the spec selects a new repository:

    - **Repo:** new <name> <node|python>

Absent, `/ship-fast` works in the repository that contains the spec.

### Approval and stops

Invoking `/ship-fast` is the user's approval for every step below,
including creating a private GitHub repository when the spec has a
`**Repo:** new` line. It never merges.

Stop rules (on each: write the handoff with `claude-kit:handoff`, state the
blocker and what was tried, end the turn):

- The spec has no acceptance criteria.
- A choice needed to proceed is not settled by the spec, its ADRs or the
  existing code, and it changes scope, product behaviour, the public
  interface, or touches data irreversibly. Ask it as a question with the
  options and a recommendation; on the answer, record it under
  **Decisions** in the PR body and continue. ("How" choices the spec leaves
  open that do not change those: pick the simplest and list it under
  **Assumptions** in the PR body.)
- `git fetch origin`, `scaffold.py`, the stack's init command, or
  `gh repo create` fails.
- The baseline test suite of an existing repository is red.
- PR CI is red after 2 fix attempts (report the open PR link).

It follows `/ship`'s git lock retry rule (copied into the command).

### Steps

1. **Repo.** With a `**Repo:** new <name> <stack>` line: run
   `scaffold.py --name <name> --stack <stack>`, run the stack's init command
   the script prints, copy the spec into the new repo's
   `docs/superpowers/specs/` and commit it (the original stays where it
   was), then
   `gh repo create <name> --private --source <repo> --push`. Without the
   line: `git fetch origin` in the spec's repository.
2. **Worktree.** Use `superpowers:using-git-worktrees`; branch
   `poc/<slug>` from `origin/main` (`<slug>` from the spec file name without
   the date and `-design`). Spec hand-off as `/ship` step 2 (copy and commit
   the spec if it is missing from or differs from `origin/main`; delete the
   main checkout's copy only if untracked and identical). In an existing
   repository, run the full test suite and lint from the repo's `CLAUDE.md`
   once; red is a stop rule. For a repository created in step 1 the
   baseline run is skipped (it has no tests yet; pytest exits 5 on an empty
   suite).
   Record the start time; each later step records its own.
3. **Task list.** Write `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md`:
   title, `**Spec:**` line, `**Status:** fast (ungated)`, and 1–5 tasks
   (`### Task N: <name>`), each with a one-paragraph goal, a `**Files:**`
   block of `Create:`/`Modify:`/`Test:` bullets with backticked paths, a
   `**Depends on:**` line, and its done check (the test that proves it).
   No step-by-step code. Split the work along file boundaries so
   independent tasks share no file. Commit it. No plan gate.
4. **Implement.** Run `parallel-plan.py waves <plan>`. If it exits non-zero
   or every wave has one task, implement the tasks in order in this session
   with `superpowers:test-driven-development`. Otherwise run
   `claude-kit:parallel-tasks` with `<plan>` (at most 3 tasks at once).
   Tests cover the core path and each acceptance criterion that a test can
   check; skip edge cases the spec does not ask for. Run the full suite and
   lint before each commit; commit per task. Docker, if used, follows the
   workspace's baseline-and-label rule (as `/ship` step 4).
5. **Smoke run.** Use the `run` skill to launch the app and check each
   acceptance criterion that a test does not cover, recording the evidence
   (command output, or a screenshot path). A criterion that fails is fixed
   and rechecked, using `superpowers:systematic-debugging`.
6. **Quick review.** Run the `code-review` skill with `low --fix` on
   `origin/main..HEAD`. Keep only correctness fixes; re-run the full suite
   and lint; commit.
7. **PR.** `git push -u origin poc/<slug>`. Create the PR exactly as
   `/ship` step 7 (title is the spec's `# ` heading, Bash tool, single-quoted
   literal title, `--body-file`, one title check-and-fix). The body has:
   Summary; Acceptance criteria, each with its evidence (test name or smoke
   output); Decisions (answered questions, if any); Assumptions; Cut (what
   the POC leaves out); links to the spec and task list; Verification (the
   exact commands and results); the session's attribution line. Then
   `gh pr checks --watch --fail-fast`; on red, `gh run view <id>
   --log-failed`, fix, push, count one attempt. If the repo has no CI
   workflow, say so in the report and skip the watch.
8. **Cleanup.** Leave the feature worktree (`ExitWorktree` with `keep` if
   entered that way), clean up Docker as `/ship` step 11, then
   `git -C <main-checkout> worktree remove <path>`, `worktree prune`,
   `branch -D poc/<slug>` (the remote branch stays for the PR). Delete
   scratch files created outside the repo.
9. **Report.** One message: the PR link, each acceptance criterion with
   its evidence, Decisions and Assumptions, review fixes, CI result, and
   wall-clock minutes per step (2–7) so slow steps are visible.

### `parallel-tasks` wording

Every mention of `/ship` in `SKILL.md` (description, intro and Setup)
becomes "`/ship` or `/ship-fast`", and "the plan is committed in `/ship` step 3" becomes "the plan
is committed before this skill runs". No behaviour change.

## Decisions

- **Input is a spec file; no gates run** (user's choice). The spec carries
  the acceptance criteria that the smoke run and PR body check against.
- **Ends at an open PR with green CI; the user merges** (user's choice).
  No `main` verification.
- **One `code-review low --fix` pass replaces the review round** (user's
  choice), plus TDD on the core path and a smoke run.
- **New repos are scaffolded and pushed to a private GitHub repo** when the
  spec says `**Repo:** new` (user's choice). Invoking the command approves
  `gh repo create --private`.
- **Unsettled decisions stop and ask** (user's choice);
  "how" choices that change none of scope, behaviour, interface or data are
  assumed and listed.
- **Name `/ship-fast`** (user's choice).
- **A task list, not a writing-plans plan**: same parseable `**Files:**` and
  `**Depends on:**` format, so `parallel-plan.py` and `parallel-tasks` work
  unchanged, without per-step code.
- **Branch prefix `poc/`** so POC branches are distinguishable from `/ship`'s
  `feat/`.

## Success criteria

1. `pytest` passes, and `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean.
2. `tests/test_ship_fast_command.py` asserts that `ship-fast.md`: has
   frontmatter with `disable-model-invocation: true`; contains none of
   `spec-gate`, `plan-gate`, `gh pr merge`, `requesting-code-review`;
   contains `parallel-plan.py`, `claude-kit:parallel-tasks`,
   `code-review`, `low --fix`, `origin/main`, `poc/<slug>`,
   `gh repo create`, `--private`, `**Repo:** new`, `Assumptions`,
   `Success criteria`, and `gh pr checks --watch`.
3. `tests/test_plugin_manifest.py` lists `ship-fast` in the expected
   commands and the user-only set; manifest version is 0.13.0 and its
   description contains `/ship-fast`.
4. ADR 0021 exists with a row in `knowledge/decisions/README.md`;
   `conventions/spec-driven-development.md` cites it; `README.md` and
   `CLAUDE.md` mention `/ship-fast`.
5. **Live toy run.** After merge-ready implementation, in a fresh session
   with the branch's command loaded, run `/ship-fast` on a toy spec
   (`**Repo:** new ship-fast-toy python`: a CLI that counts words in a file,
   with three acceptance criteria). Pass when it ends with an open PR on a
   new private repo with green CI (or a stated "no CI" report), every
   criterion has evidence, and the report lists per-step minutes. The toy
   repo is deleted afterwards (`gh repo delete`, with the user's
   confirmation) and its local folder removed.
