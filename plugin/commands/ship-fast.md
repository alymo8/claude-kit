---
description: Use for a proof of concept of about an hour - interview the user for the spec (or take an existing one), have the user read and approve it, ask the product decisions out loud, and take it to a tested, smoke-run pull request with green CI, with no gates, no review round and no merge; independent tasks run in parallel
argument-hint: [spec.md | idea]
disable-model-invocation: true
---

Ship a proof of concept of about an hour fast, with the user deciding what
it does. `$ARGUMENTS` is a spec path or an idea (see Input). The user reads
and approves the spec; no gate runs, there is no formal review round, and
the run ends at an open pull request with green CI and the POC running from
its kept workspace. The user merges it; never merge it yourself. The run
may be shown live to a client: phrase every question in product terms.

Invoking `/ship-fast` is the user's approval for every step below,
including creating a private GitHub repository when the spec asks for one.
Do not ask for confirmation except in step 0 (its Approval item included),
step 3b, a product or risky engineering question (see Questions), and the
Stop rules. Inside step 0,
`superpowers:brainstorming` and `claude-kit:grill` put their questions to
the user, within step 0's budget. Anywhere else, where a skill this command
invokes says "ask" or "wait for the answer", take the path this command
names and continue. Do not check local `main` or stop for its state, and
skip the workspace's pre-flight branch check: invoking `/ship-fast` waives
it. Never delete a repository, and never suggest deleting one.

Where `${CLAUDE_PLUGIN_ROOT}` is not expanded, use `~/.claude/skills/claude-kit` in its place.

## Input

- `$ARGUMENTS`, resolved against the current directory, names an existing
  `.md` file: it is the spec. Skip step 0 except its item 6 (Approval),
  which runs when the spec's Status bullet is not `approved`.
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
before the first question), check whether `AskUserQuestion` is available
(listed directly or deferred); if not (say a scripted `claude -p` run),
the session is non-interactive and its stop rules apply. Every product or
non-risky engineering question in step 3b or later then takes its
recommended answer, listed as "assumed (not asked)" in the task list's
`## Decisions` and in the PR body. A risky engineering choice in step 3b
stops before `## Decisions` is written, so the rerun asks step 3b again:
the stop message and the handoff list the choice with its options and
recommendation, and say how to settle it (rerun interactively, or add the
answer to the spec's `## Decisions`, which step 3b then treats as
decided).

**Where answers go.** In the PR body and the report, **Decisions** lists
every answered question and every product choice "assumed (not asked)";
**Assumptions** lists only engineering choices taken without asking.

## Stop rules

These are the only reasons to stop. When one fires: write the handoff with
the `claude-kit:handoff` skill, state the blocker and what you tried, and
end your turn. A stop after step 5 launched the app leaves it running and
gives its stop command. Every stop after step 0 also states the absolute path of the
spec to pass on the rerun, in the stop message and in the handoff: for a
new repository, the in-repository copy once step 1 has committed it, and
before that the `~/.claude/ship-fast-specs/` path.

The first three stops below happen before any repository or branch exists:
they end the run without a handoff, printing the blocker and the corrected
invocation (for example `/ship-fast <path to an existing spec.md>`).

- `$ARGUMENTS` is a single token ending in `.md` that names no existing
  file.
- Step 0 in a non-interactive session.
- A spec whose Status is not `approved` in a non-interactive session:
  nobody can approve it.
- A risky engineering choice in a non-interactive session.
- The spec has no acceptance criteria.
- `git fetch origin`, `scaffold.py`, the stack's init command, or
  `gh repo create` fails.
- The baseline test suite of an existing repository is red.
- An acceptance criterion still fails the smoke run after 2 fix attempts.
  No PR is opened.
- PR CI is red after 2 fix attempts. Report the open PR link.
- `frozen-check.py` exits 1 before a push in step 7. Report each changed
  path (and the open PR link, if any). The user approves the change, and
  only then the main session runs `git commit --allow-empty`, after the
  change commit, with one `Frozen-change-approved: <path>` trailer line per
  approved path; or the user revises the spec.

## Git lock retry

A git command (any checkout or worktree of this repository) that fails with
`Unable to create '...lock': File exists` or `cannot lock ref` is retried
after 5 seconds, up to 5 times; then it is handled like any failed command.

## Resume

A rerun after a stop continues where the last run stopped. A run that
stopped before step 0 wrote the spec starts the interview again; after
that, rerun with the spec path the stop message gave.

On a rerun, before anything else, read `${CLAUDE_PLUGIN_ROOT}/references/ship-fast-resume.md`
and follow it.

## Steps

Record the wall-clock time at the start of each step from 2 to 7, and when
step 7 ends. A resumed run reports the minutes it measured.

**Step 0** (Spec), only when Input says so: read `${CLAUDE_PLUGIN_ROOT}/references/ship-fast-spec.md`
and follow it.

1. **Repo.** With a `**Repo:** new <name> <stack>` line, run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" --name <name> --stack <stack>`
   with no `--parent` (the repository goes beside the other project repos);
   `<repo>` is the path the script prints. In `<repo>`, run
   only the stack's init commands from the script's `next:` line (not
   `/init`, and not its `gh repo create` hint), passing `--no-workspace` to
   `uv init` so a parent `pyproject.toml` does not adopt the new project;
   copy the spec to
   `docs/superpowers/specs/<spec file name>` (the original stays where it
   was), and commit the init output and the spec together. Then run
   `gh repo create <name> --private --source <repo> --push`. A red first
   `main` CI run there (no tests yet) is expected, not a stop; the report
   says so. From here on, "the spec" is the copy at
   `docs/superpowers/specs/<spec file name>` in `<repo>`. Without the line,
   run `git fetch origin` in the spec's repository.
2. **Worktree.** Use `superpowers:using-git-worktrees` in the repository;
   branch `poc/<slug>` from `origin/main`, not local `main` (the git
   fallback is `git worktree add <path> -b poc/<slug> origin/main`). If the
   spec is missing from `origin/main` or differs from it, copy it to the
   same path in the worktree and commit it; then, if the main checkout's
   copy is untracked and identical to the committed one, delete it from the
   main checkout, and if it is tracked and its only change is the Status
   bullet item 6 set, restore it with `git -C <main-checkout> checkout --
   <path>`. In an existing repository, run the full test
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
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/parallel-plan.py" waves <plan>`. If it
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
   with its commit message. Before the first Docker command, follow "Docker
   hygiene" in the engineering-practices playbook (kit map), with `<slug>`
   as the task name and the baseline in
   `~/.claude/ship-fast-specs/<slug>.docker-baseline.txt` (it outlives the
   session, for a later Cleanup).
5. **Smoke run.** The user tries the app while it is checked. Use the
   `run` skill to launch it from the worktree in the background (or its containers): one
   copy, the only one the run starts. Before any check, post a **Try it
   now** line: its URL or entry command and the command to stop it (for a
   CLI app with no server, the entry command alone, for the user to run).
   Then check, against that same running copy, every
   acceptance criterion that no test covers. The checks use their own
   clearly labelled sample data and never edit or delete data the user
   created. **Restart on fixes:** after every fix commit from here to step 7
   (a smoke fix, the review fixes, a CI fix), restart that copy on the new
   code and post one progress line saying so. Record the evidence for each
   (command output, or a screenshot path); write screenshots and sample
   inputs to the scratchpad, not the worktree. A criterion that fails is fixed
   with `superpowers:systematic-debugging` and rechecked, at most 2 times
   per criterion; a criterion still failing after that is a stop rule.
6. **Quick review.** Run the `code-review` skill with the arguments
   `low --fix poc/<slug>` (the branch is the target, diffed against
   `origin/main`, so it covers every commit on it). Then read `git diff`: keep each edit that fixes a
   correctness bug and revert the rest. Re-run the full suite and lint, and
   commit `<slug>: review fixes` if anything is left (that commit restarts
   the app, as in step 5).
**Steps 7 to 9** (PR, Hand over, Report): once step 6 is done, read
`${CLAUDE_PLUGIN_ROOT}/references/ship-fast-finish.md` and follow it.

## Cleanup (on request)

Never part of the run: it runs only when the user asks for it, after
testing the POC, in this session or a later one. Find the worktree with
`git worktree list` (the one on `poc/<slug>`). If it has uncommitted
changes or commits not on `origin/poc/<slug>` (the user may have edited
while testing), list them and ask before removing anything.

Then read `${CLAUDE_PLUGIN_ROOT}/references/ship-fast-cleanup.md` and follow it.
