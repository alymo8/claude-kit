---
description: Use for a proof of concept of about an hour - take a spec to a tested, smoke-run pull request with green CI, with no gates, no review round and no merge; independent tasks run in parallel
argument-hint: [path-to-spec.md]
disable-model-invocation: true
---

Ship the spec at `$ARGUMENTS` fast (if empty: the newest `*.md` under
`docs/superpowers/specs/`; name it in one line and continue). This is the
light path for a proof of concept of about an hour: no gate runs on the spec
or on the task list, there is no formal review round, and the run ends at an
open pull request with green CI. The user reviews and merges it; never merge
it yourself.

Invoking `/ship-fast` is the user's approval for every step below,
including creating a private GitHub repository when the spec asks for one.
Do not ask for confirmation except under the Stop rules. Where a skill this
command invokes says "ask" or "wait for the answer", take the path this
command names and continue. Report once, at the end.

## Input

- **Acceptance criteria:** the spec's `## Success criteria` section, or else
  the first `##` section whose heading contains "criteria" or
  "verification" (any case). If there is none, that is a stop rule: never
  invent what "done" means.
- **New repository:** a header line `- **Repo:** new <name> <node|python>`
  in the spec. Without it, work in the git repository that contains the
  spec.
- `<slug>`: the spec's file name without `.md`, without a leading
  `YYYY-MM-DD-` and without a trailing `-design`.

## Stop rules

These are the only reasons to stop. When one fires: write the handoff with
the `claude-kit:handoff` skill, state the blocker and what you tried, and
end your turn.

- The spec has no acceptance criteria.
- A choice needed to proceed is not settled by the spec, its ADRs or the
  existing code, and it changes scope, product behaviour or the public
  interface, or touches data irreversibly. Ask it as one question with the
  options and your recommendation. When the user answers, record the answer
  under **Decisions** in the PR body and continue from where you stopped. A
  "how" choice that changes none of those is not a stop: pick the simplest
  option, list it under **Assumptions** in the PR body, and continue.
- `git fetch origin`, `scaffold.py`, the stack's init command, or
  `gh repo create` fails.
- The baseline test suite of an existing repository is red.
- An acceptance criterion still fails the smoke run after 2 fix attempts.
  No PR is opened.
- PR CI is red after 2 fix attempts. Report the open PR link.

## Git lock retry

Any git command in this repository, in the main checkout or any worktree,
that fails with `Unable to create '...lock': File exists` or
`cannot lock ref` is retried after 5 seconds, up to 5 times. All worktrees
share one `.git` directory, so concurrent worktrees can collide on its locks.
A command still failing after that is handled like any other failed command.

## Resume

A rerun after a stop continues where the last run stopped:

- With `**Repo:** new`, if the repository folder already exists as a git
  repository with an `origin` remote, step 1 only runs `git fetch origin`
  there.
- With `**Repo:** new`, if the repository folder exists as a git
  repository without an `origin` remote (a stop in step 1): skip
  `scaffold.py`, run the stack's init commands only if their output
  (`pyproject.toml` or `package.json`) is missing, commit anything
  uncommitted, then run `gh repo create` as in step 1.
- In both cases above, "the spec" is the copy at
  `docs/superpowers/specs/<spec file name>` in the repository, as after
  step 1.
- If you are already in a worktree on `poc/<slug>`, skip step 2. If
  `git worktree list` shows a worktree on `poc/<slug>`, enter it
  (`EnterWorktree` with its path, or change directory) and skip step 2. If
  only the branch `poc/<slug>` exists, run
  `git worktree add <path> poc/<slug>` (no `-b`) and skip the rest of
  step 2.
- If `docs/superpowers/plans/*-<slug>.md` with `**Status:** fast (ungated)`
  exists on the branch, skip step 3, and in step 4 implement only the tasks
  whose commit message (`<slug>: task N`) is not yet in
  `git log origin/main..HEAD`.

## Steps

Record the wall-clock time at the start of each step from 2 to 7.

1. **Repo.** With a `**Repo:** new <name> <stack>` line, run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" --name <name> --stack <stack>`
   (fallback if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/scaffold.py`). Pass no `--parent`:
   the repository is created beside the other project repos in the
   workspace, and `<repo>` is the path the script prints. In `<repo>`, run
   the stack's init commands the script prints, copy the spec to
   `docs/superpowers/specs/<spec file name>` (the original stays where it
   was), and commit the init output and the spec together. Then run
   `gh repo create <name> --private --source <repo> --push`. The first
   `main` CI run on that push may be red because the repository has no
   tests yet (pytest exits 5 on an empty suite); that is expected, not a
   stop, and the report says so. From here on, "the spec" is the copy at
   `docs/superpowers/specs/<spec file name>` in `<repo>`. Without the line,
   run `git fetch origin` in the spec's repository.
2. **Worktree.** Use `superpowers:using-git-worktrees` in the repository;
   branch `poc/<slug>` from `origin/main`, not local `main` (the git
   fallback is `git worktree add <path> -b poc/<slug> origin/main`). If the
   spec is missing from `origin/main` or differs from it, copy it to the
   same path in the worktree and commit it; then, only if the main
   checkout's copy is untracked and identical to the committed one, delete
   it from the main checkout. In an existing repository, run the full test
   suite and lint from the repo's `CLAUDE.md` once; red is a stop rule. For
   a repository created in step 1, skip this baseline run.
3. **Task list.** Write `docs/superpowers/plans/<YYYY-MM-DD>-<slug>.md`: a
   `# ` title, a `**Spec:**` line with the spec's path in backticks,
   `**Status:** fast (ungated)`, and 1 to 5 tasks. Each task is a
   `### Task N: <name>` heading with a one-paragraph goal; a `**Files:**`
   block of `- Create:`, `- Modify:` and `- Test:` bullets with backticked
   paths; a `**Depends on:**` line (`none`, or `Task 1, Task 3`); the test
   that proves it is done; and its commit message, `<slug>: task N <name>`.
   No step-by-step code. Split the work along file boundaries so that
   independent tasks share no file. Commit the task list. No gate runs.
4. **Implement.** Run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" waves <plan>`
   (fallback: `~/.claude/skills/claude-kit/scripts/parallel-plan.py`). If it
   exits non-zero, or every wave has one task, implement the tasks in order
   in this session with `superpowers:test-driven-development`. Otherwise
   run `claude-kit:parallel-tasks` with `<plan>` as its argument (at most 3
   tasks at once). Tests cover the core path and every acceptance criterion
   a test can check; skip edge cases the spec does not ask for. Before each
   commit run the full suite and lint; commit per task with its commit
   message. Before the first Docker command, record the baseline
   (`docker ps -aq`, `docker images -q`, `docker volume ls -q`,
   `docker network ls -q`) in a scratch file outside the repo; then label
   every object the task creates `claude-kit.task=<slug>` (compose:
   `-p <slug>`) and build with `docker buildx create --name <slug>`.
5. **Smoke run.** Use the `run` skill to launch the app and check every
   acceptance criterion that no test covers. Record the evidence for each
   (command output, or a screenshot path). A criterion that fails is fixed
   with `superpowers:systematic-debugging` and rechecked, at most 2 times
   per criterion; a criterion still failing after that is a stop rule.
6. **Quick review.** Run the `code-review` skill with the arguments
   `low --fix poc/<slug>` (the branch is the target, so it covers every
   commit on it). Then read `git diff`: keep each edit that fixes a
   correctness bug and revert the rest. Re-run the full suite and lint, and
   commit `<slug>: review fixes` if anything is left.
7. **PR.** `git push -u origin poc/<slug>`. The PR title is the spec's
   title: the first line outside code fences that starts with `# `, with the
   `# ` prefix and trailing whitespace removed. Run, with the Bash tool (not
   PowerShell), `gh pr create --title '<title>' --body-file <file>`, with
   the title written out literally inside single quotes and each `'` in it
   written as `'\''`. The body has: Summary; Acceptance criteria, each with
   its evidence (the test name or the smoke-run output); Decisions (the
   user's answers, if any); Assumptions; Cut (what the POC leaves out);
   links to the spec and the task list; Verification (the exact commands
   and their results); and the attribution line the session requires. Then
   compare `gh pr view --json title` with the title; on a mismatch run
   `gh pr edit --title '<title>'` once. Then `gh pr checks --watch
   --fail-fast`. On red: `gh run view <id> --log-failed`, fix with
   `superpowers:systematic-debugging`, commit, push, count one attempt. If
   the repository has no CI workflow, skip the watch and say so in the
   report.
8. **Cleanup.** Leave the feature worktree first (`ExitWorktree` with
   `keep` if the session entered it with `EnterWorktree`, otherwise change
   directory). If the task used Docker: stop and remove the containers
   labelled `claude-kit.task=<slug>` (`docker compose -p <slug> down
   --volumes --rmi local` for a stack), remove the images, volumes and
   networks it created or pulled that are not in the step-4 baseline, and
   `docker buildx rm <slug>`; never run a prune without a
   `label=claude-kit.task=<slug>` filter. Then
   `git -C <main-checkout> worktree remove <worktree-path>`,
   `git -C <main-checkout> worktree prune` and
   `git -C <main-checkout> branch -D poc/<slug>`. The remote branch stays for
   the PR; the user deletes it when merging. A handoff an earlier stop
   wrote on this branch (`.claude/handoffs/poc_<slug>.md`) lives in the
   feature worktree and goes with `worktree remove`; leave the main
   checkout's handoff files alone. Delete any scratch files you created
   outside the repo.
9. **Report.** One message: the PR link; each acceptance criterion with its
   evidence; Decisions and Assumptions; the review fixes; the CI result
   (and, for a new repository, that its first `main` run was red because it
   had no tests yet); and the wall-clock minutes of steps 2 to 7.
