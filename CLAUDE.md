# Workspace conventions (Desktop/Github)

These apply to all projects under this directory. This file plays two roles:
workspace rules for every repo, and project memory for the kit itself (last section).

## How we work

Projects follow the six conventions in [`conventions/`](conventions/) (knowledge
layer, decision log, spec-driven development, engineering practices, project
memory, session hygiene). Read the relevant file before applying it. Scale them to
the project: full strength once a project has more than one contributor, outlives a
weekend, or makes choices worth remembering; lighter for throwaway work.

## Verify key decisions with me, and agree on criteria upfront

Do not let significant choices pass silently.

- **Surface key decisions for explicit verification.** When a decision would shape
  scope, architecture, product boundary, data/irreversible actions, or the
  interpretation of what I asked for, **stop and have me confirm it explicitly**
  before proceeding — call the decision out by name with the options and your
  recommendation, rather than folding it into the work. The goal is that nothing
  important is decided by default or missed. (Verified decisions worth keeping become
  [ADRs](conventions/decision-log.md).)
- **Agree on evaluation & verification criteria before doing the work.** Up front,
  **outline the specific criteria you will use to evaluate the result and to verify
  it is correct** — what "done and correct" means, how you will check it (tests,
  eval/benchmark, manual steps, expected output), and any acceptance thresholds — and
  get my agreement before building. Then verify against exactly those criteria and
  report the evidence (see the `superpowers:verification-before-completion` skill).

## Designing a spec

When designing a spec with me, present the design once, in full, then write
the spec: no approval pause between design sections. Ask me only the
questions the design needs (decisions under "Verify key decisions with me");
I take part by answering them and giving instructions. The spec gate and the
plan gate review the documents, and my sign-off is each gate's verdict and
key decisions.

With `CLAUDE_KIT_GRILL=1`, the `claude-kit:grill` skill runs between the
design summary and the spec
([ADR 0019](knowledge/decisions/0019-spec-grill-opt-in.md)); its rounds and the
shared-understanding confirmation are the only pause.

## Specs and plans

Specs and plans are Markdown under `docs/superpowers/specs/` and
`docs/superpowers/plans/`; the `.md` is the only source of truth. **Never open a
spec or plan (neither the `.md` nor an HTML view) and never render one unless I
ask**, even when asking me to review it; after writing or updating one, tell me
the `.md` path only. `/spec-html [path]` renders and opens a view on demand (latest
spec/plan when no path is given). Bulk render from inside a repo:
`python ../plugin/scripts/render-spec.py [spec.md]` (needs `pip install markdown`);
never copy the renderer into a repo.

**Gate every spec.** After writing or revising a spec, run the
`claude-kit:spec-gate` skill on it before asking me to review it. My review is
the gate's verdict and key decisions, answered in one line; I do not read the
spec in full ([ADR 0015](knowledge/decisions/0015-spec-gate-replaces-full-read.md)).
`/ship` requires a passing gate record under `docs/superpowers/gates/`.

**Gate every plan.** After writing or revising a plan, run the
`claude-kit:plan-gate` skill on it before offering an execution choice. A
`pass` goes straight to the execution choice; `pass-with-decisions` needs my
one-line OK on the decisions it lists first; I do not read the plan
([ADR 0016](knowledge/decisions/0016-plan-gate-signs-off-on-new-decisions-only.md)).
`/ship` gates its own plan and stops on any plan-introduced decision.

Plans must be self-contained: whoever executes one has none of our conversation
context. Apply every bullet under "Self-contained plans" in
[conventions/spec-driven-development.md](conventions/spec-driven-development.md).

## Token discipline

The lean-context rule is injected at session start by the kit's
`lean_context_inject.py` hook, on by default. To switch it off, set
`"CLAUDE_KIT_LEAN_CONTEXT": "0"` under `env` in `~/.claude/settings.json` and deny
`Skill(claude-kit:lean-context)` (ADR 0014). Details:
[conventions/session-hygiene.md](conventions/session-hygiene.md).

## Open files and folders for me

Whenever you want me to update a file or look at a specific folder structure,
open the file / folder for me (`Invoke-Item <path>` for a file, `explorer <path>`
for a folder) rather than only telling me the path. Exception: specs and plans
are never opened unless I ask (see "Specs and plans").

## Building a new feature: pre-flight, worktree, clean up

**Before implementing any new feature, run a pre-flight branch check and get my
go-ahead:**

1. **Confirm we are on `main`.** Run `git branch --show-current`. If not on `main`,
   **stop and warn me** — tell me the current branch and do not start until I
   confirm how to proceed.
2. **Confirm `main` is up to date.** `git fetch`, then check `git status -sb` /
   `git rev-list --count main..@{u}`. If local `main` is behind or ahead of the
   remote, **stop and warn me** — do not start until `main` is updated or I tell
   you to proceed anyway.

Only once both checks pass (or I have explicitly waived them) should you begin.

Then build in an isolated worktree using `superpowers:using-git-worktrees`, after
pulling the latest `main` so the worktree branches from up-to-date code.

**A feature is not finished until its workspace is gone.** When the work is merged
(or I have explicitly abandoned it), use `superpowers:finishing-a-development-branch`
to integrate and clean up: the worktree removed and pruned, the branch deleted
locally and on the remote, and any scratch files created outside the repo deleted.
Docker is part of the workspace. Before a task first uses Docker, make its objects
identifiable. Record the IDs that already exist (`docker ps -aq`, `images -q`,
`volume ls -q`, `network ls -q`) in a scratch file outside the repo. Label what the
task creates (`--label claude-kit.task=<slug>`, compose `-p <slug>`) and build with
its own builder (`docker buildx create --name <slug>`). At cleanup, before removing
the worktree: stop and remove the task's containers (`docker compose -p <slug> down
--volumes --rmi local` for a stack), remove the images, volumes and networks it
created or pulled that are not in the baseline, and remove its builder
(`docker buildx rm <slug>`, which drops that build cache). Never run a prune
(`docker system|volume|image|container|network|builder prune`) without a
`label=claude-kit.task=<slug>` filter, and never remove anything in the baseline.
The kit's session-start hook reports leftover worktrees and branches; treat that as
a to-do, but **never delete anything with unmerged commits or uncommitted changes
without asking me first.** The normal end of a working session on a feature is
`/handoff` then `/clear`; the next session on the branch starts from the handoff.

**Once I approve a spec, `/ship <spec.md>` is my instruction to continue
autonomously** through plan → implement → CI → review → PR → green CI →
squash-merge → verify `main` → cleanup, with no further check-ins. Invoking it is
my explicit approval for the merge; it stops only on the rules listed in the
command.

**`/ship-many <spec.md> ...` ships several approved specs at once.** It gates
each spec, groups the ones whose Scope In lists share no file
(`parallel-plan.py specs`), and runs each group's specs as concurrent
headless `/ship` runs (at most 3 by default); specs that share a file run in
sequence. Invoking it is my approval for every listed spec and its merge, like
`/ship`. Use `--dry-run` first to see the waves without launching anything
([ADR 0018](knowledge/decisions/0018-ship-many-headless-children.md)).

**`/ship-fast [spec.md | idea]` is the light path for an hour-sized POC.**
Given an idea (or nothing), it first interviews me for the spec: a
brainstorming design, then product questions with recommended answers (at
most 7 questions in all); my confirmation approves the spec. Given a spec, it skips that.
No gate runs; it writes a short task list, asks at most 3 product and 3
engineering questions the task split exposed (plus any risky choice), builds
independent tasks in parallel, runs one `code-review low --fix` pass and a
smoke run against the spec's acceptance criteria, and stops at an open PR
with green CI that I review and merge. Product or risky questions that come
up later are asked inline and never end the run. A
`- **Repo:** new <name> <node|python>` spec header makes it scaffold the
project and create a private GitHub repo; it never deletes a repo
([ADR 0021](knowledge/decisions/0021-ship-fast-skips-gates.md),
[ADR 0022](knowledge/decisions/0022-ship-fast-user-driven-spec.md)).

## Developing the kit (this repo)

```
pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"   # once per machine
pytest                                                   # full suite
pytest tests/test_render_spec.py::test_title_from_h1     # one test
ruff check plugin tests; ruff format --check plugin tests
```

Hook edits (`plugin/hooks/`) need a new session or `/reload-plugins`; `SKILL.md`
and command edits are live (the plugin is loaded in place through a junction,
ADR 0005). Never run `plugin/install.ps1` from a test without `-SkillsDir <tmp>`.
