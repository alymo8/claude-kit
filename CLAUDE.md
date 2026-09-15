# Workspace conventions (Desktop/Github)

These apply to all projects under this directory.

## How we work: knowledge, decisions, specs, engineering, project memory

New projects follow five working conventions, documented in full under
[`conventions/`](conventions/) (self-contained — read the relevant file before
applying it). **Scale them to the project:** these are the full-strength defaults;
apply a lighter version for small or throwaway work, but reach for the full shape
once a project has more than one contributor, outlives a weekend, or makes choices
worth remembering.

- **[Knowledge layer](conventions/knowledge-layer.md)** — capture research and
  context as a version-controlled, domain-organized, single-source-of-truth
  knowledge base (`knowledge/`), with raw sources preserved verbatim in `archive/`.
- **[Decision log (ADRs)](conventions/decision-log.md)** — record locked-in
  decisions as numbered `NNNN-slug.md` ADRs (Context / Decision / Consequences /
  Status / Date); supersede, never delete.
- **[Spec-driven development](conventions/spec-driven-development.md)** — brainstorm
  → spec → plan → build; specs and plans live dated under `docs/superpowers/specs/`
  and `docs/superpowers/plans/`.
- **[Engineering practices](conventions/engineering-practices.md)** — test-first
  development, language-agnostic coding standards, and a CI + AI + human code-review
  gate on every change to `main`.
- **[Project memory file](conventions/project-memory.md)** — every repo carries a
  checked-in `CLAUDE.md` at its root with build commands, test commands (full suite
  and single test), architectural conventions, and gotchas. Cheap to write,
  disproportionately effective, and static — so it sits in the cacheable prefix
  instead of being rediscovered every session. Keep it to about a screen, update it
  in the same PR that makes it stale, and link to `knowledge/` rather than
  duplicating it.

See [`conventions/README.md`](conventions/README.md) for how the five fit together.

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

Whenever you write or update a spec / design document (Markdown, under
`docs/superpowers/specs/`), also produce a co-located, self-contained HTML rendering
of it. Keep the original `.md` as the source of truth; the `.html` is a generated
view for easy reading in a browser.

- The HTML must live next to the `.md` with the same basename
  (e.g. `foo-design.md` → `foo-design.html`).
- The HTML must be standalone (inline CSS, no external requests), mobile-first,
  and RTL-aware (spec content may contain Arabic).
- Regenerate the HTML every time the `.md` changes, so the two never drift.
- The HTML is a **local view only — never commit it.** Every repo gitignores
  `docs/superpowers/**/*.html`; only the `.md` is tracked.

Use the shared renderer at `Desktop/Github/plugin/scripts/render-spec.py`. Run it
from inside a repo (repos live one level under `Github/`, so `../plugin/` resolves):

```
python ../plugin/scripts/render-spec.py <path-to-spec.md>   # one file
python ../plugin/scripts/render-spec.py                      # all specs in ./docs/superpowers/specs
```

Requires `pip install markdown` (once per machine). Do not copy the script into
individual repos — keep the single shared copy so it never drifts. When the
claude-kit plugin is installed (see `README.md`), a hook re-renders automatically
after every Write/Edit to a spec or plan; you only need the command for bulk
re-renders.

## Plans must be self-contained

When you write an implementation plan (under `docs/superpowers/plans/`), assume
**whoever executes it has none of our conversation context** — it may be me in a
fresh session, a subagent, or a different machine days later. The plan file is the
only handoff.

So a plan file must stand on its own:

- **State the goal and the why**, not just the steps — enough that the executor
  understands what "done and correct" means without reading the spec. Link the spec
  / ADRs / knowledge docs it came from, but do not *depend* on them being read.
- **Carry the decisions already made** (and the rejected alternatives, briefly), so
  the executor doesn't relitigate settled choices or guess differently than we did.
- **Name concrete paths, commands, and file names** — repo, branch/worktree, files to
  create or change, exact commands to run and expected output. No "as we discussed",
  "the usual setup", "the file from earlier", or other back-references to chat.
- **Spell out setup and prerequisites** — env vars, installs, services to start —
  since a fresh session starts cold.
- **Include the verification criteria** we agreed on, so the executor can check the
  work against them without asking me.
- **Keep steps ordered and independently checkable**, with review checkpoints.

Sanity check before handing a plan over: *could a competent stranger execute this
with only the repo and this file?* If not, the plan isn't finished.

## Environment

We are working on **Windows**. Use Windows-appropriate commands and paths
(PowerShell is the primary shell; the Bash tool is available for POSIX scripts).

## Open files and folders for me

- Whenever you create a spec / knowledge / design **HTML** doc, open it for me
  after generating it (e.g. `Invoke-Item <path-to.html>` in PowerShell, or
  `start <path-to.html>`).
- Whenever you want me to update a file or look at a specific folder structure,
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
without asking me first.**
