# Workspace conventions (Desktop/Github)

These apply to all projects under this directory.

## How we work: knowledge, decisions, specs, engineering

New projects follow four working conventions, documented in full under
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
  → spec → plan → build; specs and plans live dated under `docs/specs/` and
  `docs/plans/`.
- **[Engineering practices](conventions/engineering-practices.md)** — test-first
  development, language-agnostic coding standards, and a CI + AI + human code-review
  gate on every change to `main`.

See [`conventions/README.md`](conventions/README.md) for how the four fit together.

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

Whenever you write or update a spec / design document (Markdown, typically under
`docs/superpowers/specs/`), also produce a co-located, self-contained HTML rendering
of it. Keep the original `.md` as the source of truth; the `.html` is a generated
view for easy reading in a browser.

- The HTML must live next to the `.md` with the same basename
  (e.g. `foo-design.md` → `foo-design.html`).
- The HTML must be standalone (inline CSS, no external requests), mobile-first,
  and RTL-aware (spec content may contain Arabic).
- Regenerate the HTML every time the `.md` changes, so the two never drift.

Use the shared renderer at `Desktop/Github/scripts/render-spec.py`. Run it from
inside a repo (repos live one level under `Github/`, so `../scripts/` resolves):

```
python ../scripts/render-spec.py <path-to-spec.md>   # one file
python ../scripts/render-spec.py                      # all specs in ./docs/superpowers/specs
```

Requires `pip install markdown` (once per machine). Do not copy the script into
individual repos — keep the single shared copy so it never drifts.

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

## Building a new feature: use a worktree

When building a new feature, use the **superpowers worktree skill**
(`superpowers:using-git-worktrees`) to start a new worktree. Before creating the
worktree, make sure to **pull the latest `main`** so the worktree branches from
up-to-date code.
