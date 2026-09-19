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

## Specs and plans

Specs and plans are Markdown under `docs/superpowers/specs/` and
`docs/superpowers/plans/`; the `.md` is the only source of truth. **Do not render
or open an HTML view unless I ask**; after writing or updating one, tell me the
`.md` path only. `/spec-html [path]` renders and opens a view on demand (latest
spec/plan when no path is given). Bulk render from inside a repo:
`python ../plugin/scripts/render-spec.py [spec.md]` (needs `pip install markdown`);
never copy the renderer into a repo.

Plans must be self-contained: whoever executes one has none of our conversation
context. Apply every bullet under "Self-contained plans" in
[conventions/spec-driven-development.md](conventions/spec-driven-development.md).

## Token discipline

The cost of a session is context size times turn count. Before exploring or
running anything with long output, use the `claude-kit:lean-context` skill.
Details: [conventions/session-hygiene.md](conventions/session-hygiene.md).

## Open files and folders for me

Whenever you want me to update a file or look at a specific folder structure,
open the file / folder for me (`Invoke-Item <path>` for a file, `explorer <path>`
for a folder) rather than only telling me the path.

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
The kit's session-start hook reports leftover worktrees and branches; treat that as
a to-do, but **never delete anything with unmerged commits or uncommitted changes
without asking me first.** The normal end of a working session on a feature is
`/handoff` then `/clear`; the next session on the branch starts from the handoff.

**Once I approve a spec, `/ship <spec.md>` is my instruction to continue
autonomously** through plan → implement → CI → review → PR → green CI →
squash-merge → verify `main` → cleanup, with no further check-ins. Invoking it is
my explicit approval for the merge; it stops only on the rules listed in the
command.

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
