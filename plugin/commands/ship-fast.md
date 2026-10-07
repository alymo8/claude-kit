---
description: Use for a proof of concept of about an hour - interview the user for the spec (or take an existing one), ask the product decisions out loud, and take it to a tested, smoke-run pull request with green CI, with no gates, no review round and no merge; independent tasks run in parallel
argument-hint: [spec.md | idea]
disable-model-invocation: true
---

Ship a proof of concept of about an hour fast, with the user deciding what
it does. `$ARGUMENTS` is a spec path or an idea (see Input). This is the
light path: no gate runs on the spec or on the task list, there is no formal
review round, and the run ends at an open pull request with green CI. The
user reviews and merges it; never merge it yourself. The run may be shown
live to a client: phrase every question in product terms.

Invoking `/ship-fast` is the user's approval for every step below,
including creating a private GitHub repository when the spec asks for one.
Do not ask for confirmation except in step 0, step 3b, a product or risky
engineering question (see Questions), and the Stop rules. Inside step 0,
`superpowers:brainstorming` and `claude-kit:grill` put their questions to
the user, within step 0's budget. Anywhere else, where a skill this command
invokes says "ask" or "wait for the answer", take the path this command
names and continue. Do not check local `main` or stop for its state, and
skip the workspace's pre-flight branch check: invoking `/ship-fast` waives
it. Never delete a repository, and never suggest deleting one: the user
does that themselves.

## Input

- `$ARGUMENTS`, resolved against the current directory, names an existing
  `.md` file: it is the spec. Skip step 0.
- `$ARGUMENTS` is a single token (no spaces) ending in `.md` that
  names no existing file: that is a stop rule (a mistyped spec path), not an
  idea. Free text that happens to end in `.md` is an idea.
- Otherwise (free text, or empty): the text is the idea; run step 0.
- **Acceptance criteria:** the spec's `## Success criteria` section, or else
  the first `##` section whose heading contains "criteria" or
  "verification" (any case). If there is none, that is a stop rule: never
  invent what "done" means.
- **New repository:** a header line `- **Repo:** new <name> <node|python>`
  in the spec. Without it, work in the git repository that contains the
  spec.
- `<slug>`: the spec's file name without `.md`, without a leading
  `YYYY-MM-DD-` and without a trailing `-design`.

## Progress lines

At the start of each step 0 to 8, including step 3b, post one
plain-language line naming the step and what it is about to do, for
example "Step 4: building the upload flow, tests first." Progress lines are
not reports; the single report is step 9.

## Questions

A **product choice** is one a user of the POC would see or feel: behaviour,
scope, data taken in, shown or kept, layout, wording, defaults, sample data.
An **engineering choice** is any other: libraries, file layout, test
approach, data storage, security hardening, interfaces between modules.

A **risky engineering choice** is one that deletes or migrates existing
data, uses real credentials or a paid external service, or changes an
interface that something outside the POC depends on. Risky choices are
always asked, outside every budget: in step 3b's engineering part when the
task list exposes them, inline when they surface later.

Other engineering choices are asked only in step 3b's engineering part (at
most 3); every one not asked takes the simplest option that fits the
repository and is listed under **Assumptions**. Step 0 asks no engineering
question except two, both inside its budget: Home (when step 0 item 2 does
not settle it) and the choice among brainstorming's approaches.

**Format.** Every question uses grill's format: numbered, with options when
there are any, and a recommended answer with a one-line reason.

**Inline questions.** A product choice or risky engineering choice still
open after step 3b is asked inline, one question in that format. The run
waits for the answer, appends it to the task list's `## Decisions`, commits
the task list, and continues from the same point. No handoff is written and
the run does not end.

**Non-interactive runs.** At the start of step 0 (or, with a spec path,
before the first question), check whether the
`AskUserQuestion` tool is available in this session (listed directly or
as a deferred tool both count as available); if it is not (for
example a scripted `claude -p` run), the session is non-interactive. In a
non-interactive session: step 0 is a stop rule (the interview needs the
user; pass a spec path). Every product or non-risky engineering question in
step 3b or later takes its recommended answer, listed as "assumed (not
asked)" in the task list's `## Decisions` and in the PR body, and the run
continues. A risky engineering choice is a stop rule, and in step 3b it
stops before `## Decisions` is written, so the rerun asks step 3b again:
the stop message and the handoff list the choice with its options and
recommendation, and say how to settle it (rerun interactively, or add the
answer to the spec's `## Decisions`, which step 3b then treats as
decided).

**Where answers go.** Every question the user answered, product or
engineering, appears under **Decisions** in the PR body and the report;
product choices taken without asking appear there as "assumed (not
asked)". Only engineering choices taken without asking go under
**Assumptions**.

## Stop rules

These are the only reasons to stop. When one fires: write the handoff with
the `claude-kit:handoff` skill, state the blocker and what you tried, and
end your turn. Every stop after step 0 also states the absolute path of the
spec to pass on the rerun, in the stop message and in the handoff: for a
new repository, the in-repository copy once step 1 has committed it, and
before that the `~/.claude/ship-fast-specs/` path.

The first two stops below happen before any repository or branch exists:
they end the run without a handoff, printing the blocker and the corrected
invocation (for example `/ship-fast <path to an existing spec.md>`).

- `$ARGUMENTS` is a single token ending in `.md` that names no existing
  file.
- Step 0 in a non-interactive session.
- A risky engineering choice in a non-interactive session.
- The spec has no acceptance criteria.
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

A rerun after a stop continues where the last run stopped. A run that
stopped before step 0 wrote the spec starts the interview again; after
that, rerun with the spec path the stop message gave.

A repository folder counts as this run's only if it holds
`docs/superpowers/specs/<spec file name>` (step 1 commits it there). Any
other existing folder at that path is a name collision: `scaffold.py`
refuses it, and that is a stop rule.

- With `**Repo:** new`, if this run's repository folder already exists as a
  git repository with an `origin` remote, step 1 only runs `git fetch origin`
  there.
- With `**Repo:** new`, if this run's repository folder exists as a git
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
- If that task list already has a `## Decisions` section, skip step 3b.

## Steps

Record the wall-clock time at the start of each step from 2 to 7, and when
step 7 ends. A resumed run reports the minutes it measured.

0. **Spec.** Only when Input says so. **Budget: at most 7 questions to the
   user in the whole step**, brainstorming and grill together, counting
   each numbered question and each single question (the idea question and
   the approach choice included). Fewer is better: a clear idea may need 2
   or 3.
   1. **Idea.** With no idea text, ask "What are we building, and for
      whom?" and wait for the answer in the user's words. This counts as 1.
   2. **Home.** If the current directory is inside a git repository that
      is not the claude-kit repository itself (the one whose
      `plugin/.claude-plugin/plugin.json` has `"name": "claude-kit"`), that
      repository is the home: state it in one line and read its stack from
      its files; do not ask. Otherwise Home is a grill question: a new
      repository (name, and `node` or `python`) or the path of an existing
      one.
   3. **Design.** Run `superpowers:brainstorming` on the idea, on its
      architectural path, with these overrides: skip its separate
      clarifying questions and its visual-companion offer; read the home
      repository, if there is one, for context; propose 2–3 approaches with
      a recommendation; present the design for the recommended approach
      once, in full, with no per-section approval. The approach choice is
      not asked on its own: it is the first question of the grill's first
      round. Stop there: do not write brainstorming's spec, run any review
      of it, or invoke writing-plans.
   4. **Grill.** Run `claude-kit:grill` on that design with these
      overrides: its tree holds the design's open product choices and the
      areas below **instead of** the `coverage.md` areas, and it asks at
      most the budget left, most important first, aiming for one round and
      two at most.
      - **Users and outcome:** who uses it and what they get.
      - **Core flows:** the steps a user takes, start to finish.
      - **In and cut:** what the POC does, and what it leaves out.
      - **Data:** what it takes in, what it shows, what it keeps.
      - **States and wording:** empty, loading and error screens, and the
        text users read.
      - **Acceptance criteria:** how the user will check the POC works.
      - **Home:** as in item 2, only when it is not settled there.

      Every open product choice that does not fit the budget takes the
      grill's recommended answer and is listed in the grill summary as
      **Assumed (not asked)**. Acceptance criteria are never only assumed:
      when they do not fit as their own question, the summary proposes them
      and the user's confirmation covers them. If the user chose an
      approach other than the recommended one, the summary states the
      chosen approach and what it changes in the design; the design is not
      presented again. The summary's coverage list names the areas above,
      not `coverage.md`'s, and the grill summary names Home (inferred in
      item 2 or answered), so the confirmation covers it. The user's
      confirmation of the summary is the
      spec's approval; a correction to an assumption in that reply is
      applied and does not count against the budget.
   5. **Write the spec.** Pick `<slug>`, a short kebab-case name for the
      POC. Write a `# <title>` line (the POC's name; step 7 uses it as the
      PR title), Status `approved`, Date, a
      `- **Repo:** new <name> <stack>` line when Home is a new repository,
      and the sections Purpose, Scope (`**In:**` and `**Out:**`), Design,
      Decisions (each question and the user's answer, then an
      **Assumed (not asked)** list) and Success criteria (the acceptance
      criteria). No `## Coverage` section. The file name is
      `<YYYY-MM-DD>-<slug>-design.md`: in an existing repository, under
      `docs/superpowers/specs/` in its main checkout (step 2 commits it on
      the branch); for a new repository, under `~/.claude/ship-fast-specs/`
      (durable across sessions and outside every repository; step 1 copies
      it in). State the path in one line, do not open it, and continue to
      step 1 without another pause. No gate runs.
1. **Repo.** With a `**Repo:** new <name> <stack>` line, run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" --name <name> --stack <stack>`
   (fallback if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/scaffold.py`). Pass no `--parent`:
   the repository is created beside the other project repos in the
   workspace, and `<repo>` is the path the script prints. In `<repo>`, run
   only the stack's init commands from the script's `next:` line (not
   `/init`, and not its `gh repo create` hint), passing `--no-workspace` to
   `uv init` so a parent `pyproject.toml` does not adopt the new project;
   copy the spec to
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

   3b. **Decisions round.** After the task list is committed and before
   step 4: one round in the question format, in two labelled parts, then
   wait for the answers (a non-interactive session takes the recommended
   answers, see Questions):
   - **Product:** the product choices that writing the tasks exposed and
     that the spec neither decides nor lists as assumed. Ask at most 3;
     any beyond 3 take their recommended answer and are listed as assumed.
   - **Engineering:** every risky engineering choice the task list exposes,
     plus at most 3 other engineering choices, picked by how much they
     shape the build (data storage, new dependencies or services,
     structure). The rest are assumed and listed under Assumptions.

   Write the answers and the assumed choices under a `## Decisions` section
   in the task list, after its header lines and before its first
   `### Task`, and commit. Leave out a part with nothing to ask. If both
   are empty, say so in one line, write `## Decisions` with the single line
   `- none new`, and commit.
4. **Implement.** Run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" waves <plan>`
   (fallback: `~/.claude/skills/claude-kit/scripts/parallel-plan.py`). If it
   exits non-zero, or every wave has one task, implement the tasks in order
   in this session with `superpowers:test-driven-development`. Otherwise
   run `claude-kit:parallel-tasks` with `<plan>` as its argument (at most 3
   tasks at once). Inside `parallel-tasks`, skip its final whole-branch
   review (step 6 below is the review) but still remove its temp directory,
   settle any pre-flight concern about the task list having no
   step-by-step code with a `Ruling:` ledger line rather than a question,
   and append this sentence to each subagent's prompt: "A product choice or
   risky engineering choice that the plan's `## Decisions` does not settle
   is not guessed: report the task as failed and name the question." When
   a task fails that way, ask its question inline (see Questions) before
   implementing that task inline. Tests cover the core path and every
   acceptance criterion a test can check; skip edge cases the spec does not
   ask for. Before each commit run the full suite and lint; commit per task
   with its commit message. Before the first Docker command, record the
   baseline (`docker ps -aq`, `docker images -q`, `docker volume ls -q`,
   `docker network ls -q`) in a scratch file outside the repo; then label
   every object the task creates `claude-kit.task=<slug>` (compose:
   `-p <slug>`) and build with `docker buildx create --name <slug>`.
5. **Smoke run.** Use the `run` skill to launch the app and check every
   acceptance criterion that no test covers. Record the evidence for each
   (command output, or a screenshot path); write screenshots and sample
   inputs to the scratchpad, not the worktree. A criterion that fails is fixed
   with `superpowers:systematic-debugging` and rechecked, at most 2 times
   per criterion; a criterion still failing after that is a stop rule.
6. **Quick review.** Run the `code-review` skill with the arguments
   `low --fix poc/<slug>` (the branch is the target, diffed against
   `origin/main`, so it covers every commit on it). Then read `git diff`: keep each edit that fixes a
   correctness bug and revert the rest. Re-run the full suite and lint, and
   commit `<slug>: review fixes` if anything is left.
7. **PR.** `git push -u origin poc/<slug>`. The PR title is the spec's
   title: the first line outside code fences that starts with `# `, with the
   `# ` prefix and trailing whitespace removed. Run, with the Bash tool (not
   PowerShell), `gh pr create --title '<title>' --body-file <file>`, with
   the title written out literally inside single quotes and each `'` in it
   written as `'\''`. The body has: Summary; Acceptance criteria, each with
   its evidence (the test name or the smoke-run output); Decisions (every
   question the user answered, then the product choices "assumed (not
   asked)"); Assumptions (engineering choices taken without asking); Cut
   (what the POC leaves out); links to the spec and the task list;
   Verification (the exact commands and their results); and the
   attribution line the session requires. Then
   compare `gh pr view --json title` with the title; on a mismatch run
   `gh pr edit --title '<title>'` once. Whether the repository has CI is
   decided only by whether `.github/workflows/*.yml` exists on the branch.
   If it does, run `gh pr checks` every 15 seconds until checks appear
   (they start a few seconds after the PR is created), then
   `gh pr checks --watch --fail-fast`. On red: `gh run view <id> --log-failed`, fix with
   `superpowers:systematic-debugging`, commit, push, count one attempt. If
   there is no workflow file, skip the watch and say so in the report.
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
   outside the repo; the spec under `~/.claude/ship-fast-specs/` is not a
   scratch file and stays. The repository itself always stays.
9. **Report.** One message: the PR link; each acceptance criterion with its
   evidence; Decisions (answered, then assumed) and Assumptions; the review
   fixes; the CI result (and, for a new repository, that its first `main`
   run was red because it had no tests yet); and the wall-clock minutes of
   steps 2 to 7 (each, and in total).
