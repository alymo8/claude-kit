# Workspace conventions (Desktop/Github)

These apply to all projects under this directory. This file plays two roles:
workspace rules for every repo, and project memory for the kit itself (last section).

## How we work

Projects follow the six conventions in [`conventions/`](conventions/) (knowledge
layer, decision log, spec-driven development, engineering practices, project
memory, session hygiene). Read the relevant file before applying it. Scale them to
the project: full strength once a project has more than one contributor, outlives a
weekend, or makes choices worth remembering; lighter for throwaway work. In a child
repo, the kit map injected at session start gives these files' absolute paths.

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
the `.md` path only. One exception: `/ship-fast` opens the `.md` of the spec
it asks me to approve (ADR 0024). `/spec-html [path]` renders and opens a view on demand (latest
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
`/ship` gates its own plan and approves the decisions it lists itself, stopping only on a `fail` or an irreversible decision ([ADR 0036](knowledge/decisions/0036-ship-auto-approves-plan-decisions.md)).

Plans must be self-contained: whoever executes one has none of our conversation
context. Apply every bullet under "Self-contained plans" in
[conventions/spec-driven-development.md](conventions/spec-driven-development.md).

## Token discipline

Follow [conventions/session-hygiene.md](conventions/session-hygiene.md); its
switches are in `docs/setup.md` (ADR 0014).

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

**A feature is not finished until its workspace is gone.** Before the branch merges,
run the `claude-kit:capture-learnings` skill so the feature's learnings land in its
PR. When the work is merged (or I have explicitly abandoned it), use
`superpowers:finishing-a-development-branch`
to integrate and clean up: the worktree removed and pruned, the branch deleted
locally and on the remote, and any scratch files created outside the repo deleted.
Clean-up never deletes a repository and never suggests deleting one; the repo's
owner does that.
Before a task first uses Docker, follow "Docker hygiene" in
[conventions/engineering-practices.md](conventions/engineering-practices.md#docker-hygiene)
(baseline, labels, clean-up; never an unfiltered prune).
The kit's session-start hook reports leftover worktrees and branches; treat that as
a to-do, but **never delete anything with unmerged commits or uncommitted changes
without asking me first.** The normal end of a working session on a feature is
`/handoff` then `/clear`; the next session on the branch starts from the handoff.

**When I invoke `/ship <spec.md>` or `/ship-many <spec.md> ...`, that is my
approval to run to a squash-merge on `main` with no further check-ins**,
stopping only on the rules in the command
([ADR 0018](knowledge/decisions/0018-ship-many-headless-children.md)).
`/ship-fast` (it interviews me for a POC spec) stops at a PR I merge myself and
cleans up only when I ask. The README describes all three.

## Developing the kit (this repo)

```
pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"   # once per machine
pytest                                                   # full suite
pytest tests/test_render_spec.py::test_title_from_h1     # one test
ruff check plugin tests; ruff format --check plugin tests
```

Hook edits (`plugin/hooks/`) need a new session or `/reload-plugins`; `SKILL.md`
and command edits are live (the plugin is loaded in place through a junction or
symlink, ADR 0005). Never run `plugin/install.py` (or its wrapper
`plugin/install.ps1`) from a test without a temporary `--skills-dir`
(`-SkillsDir`).

- This repo is public. Never write the names of private repos or a machine's
  username into tracked files; refer to them generically ("a project repo") and
  use `%USERPROFILE%` or `<repo-root>` in paths. Grep the diff for them before
  committing.
- When a new behaviour should recur (say, at the end of each session), first
  fold it into an existing flow step, such as `/ship`'s clean-up; propose
  session-end automation only as an alternative.

Known gotchas (pytest output, worktree guard, line endings, gates):
[knowledge/kit-dev-gotchas.md](knowledge/kit-dev-gotchas.md).
