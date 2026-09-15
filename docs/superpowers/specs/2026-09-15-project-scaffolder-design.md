# Project scaffolder and spec lifecycle

- **Status:** implemented
- **Date:** 2026-09-15

## Purpose

The kit's conventions (knowledge layer, decision log, spec-driven development,
engineering practices, project memory) are adopted by 4 of ~30 project repos, and
even those four diverge in layout. Adoption is manual: every new project re-derives
the same fifteen files. A second gap: specs carry only `draft | approved`, so a repo
with a dozen specs has no way to tell which are live, and no index.

This spec adds a `/new-project` command (and an `/adopt-conventions` variant for
existing repos) backed by a deterministic template tree and script, plus a spec
lifecycle with a generated per-repo index. It builds on the plugin foundation from
`2026-09-14-kit-foundation-design.md`.

## Scope

**In:**

1. `plugin/templates/` — the file tree a new project receives, with stack variants
   for Node (pnpm) and Python (uv).
2. `plugin/scripts/scaffold.py` — renders the templates into a new project (with
   `git init` and a first commit) or adds missing files to an existing repo.
3. Two slash commands: `plugin/commands/new-project.md`,
   `plugin/commands/adopt-conventions.md`.
4. Spec lifecycle: status vocabulary `draft | approved | implemented | superseded`,
   `plugin/scripts/spec-index.py`, and the existing render hook calling it.
5. Tests for all of the above; convention docs updated.

**Out:**

- Creating the GitHub repository or pushing (`gh repo create`). The user does that.
- Creating stack manifests (`package.json`, `pyproject.toml`); the framework's own
  init does that (`pnpm create …`, `uv init`).
- Enabling the AI-review workflow. It ships disabled with instructions for both
  auth options; enabling is a per-repo decision.
- Merging `.gitignore` in adopt mode; the report says what to verify.
- Migrating existing repos' ADR locations (grandfathered, ADR 0004).

## Design

### 1. Template tree

```
plugin/templates/
  project/                               rendered verbatim into the new project
    CLAUDE.md
    README.md
    .gitignore
    .github/workflows/ci.yml             -> replaced by the stack's ci.yml
    .github/workflows/claude-review.yml
    .github/workflows/secret-scan.yml
    .github/PULL_REQUEST_TEMPLATE.md
    knowledge/README.md
    knowledge/decisions/README.md
    knowledge/decisions/0000-template.md
    knowledge/archive/.gitkeep
    docs/superpowers/README.md
    docs/superpowers/specs/.gitkeep
    docs/superpowers/plans/.gitkeep
  stacks/
    node/    ci.yml  gitignore.part  commands.part
    python/  ci.yml  gitignore.part  commands.part
```

Placeholders are literal `{{project_name}}`, `{{date}}` (ISO, the day of
scaffolding), `{{stack}}`, `{{stack_commands}}` (contents of the stack's
`commands.part`, inserted into `CLAUDE.md`), and `{{stack_gitignore}}` (contents of
`gitignore.part`, appended to `.gitignore`). Rendering is `str.replace`; after
rendering, any remaining `{{` is an error. The stack's `ci.yml` replaces
`project/.github/workflows/ci.yml` wholesale.

Template contents, by file:

- **`CLAUDE.md`** follows `conventions/project-memory.md`: Setup / prerequisites,
  Build & run, Test (full suite and single test), Architecture in brief,
  Conventions, Gotchas, Pointers. Commands come from `{{stack_commands}}`; the
  other sections hold one-line prompts ("<!-- describe the two flows that explain
  the shape of the codebase -->") the user fills in via `/init` and pruning. First
  line after the title: a note that the stack manifest must be created with the
  framework's init before CI is green.
- **`README.md`**: `# {{project_name}}`, a one-line placeholder, and a map to
  `knowledge/`, `knowledge/decisions/`, `docs/superpowers/`, `CLAUDE.md`.
- **`.gitignore`**: `.env`, `.env.*`, `*.local`, `docs/superpowers/**/*.html`,
  `.claude/worktrees/`, then `{{stack_gitignore}}`.
- **`ci.yml` (node)**: on push + pull_request; ubuntu-latest; `pnpm/action-setup@v4`,
  `actions/setup-node@v4` with Node 22 and pnpm cache; `pnpm install
  --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`.
- **`ci.yml` (python)**: on push + pull_request; ubuntu-latest;
  `astral-sh/setup-uv@v5`, `uv sync`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run pytest`.
- **`claude-review.yml`**: `on: workflow_dispatch` only; a header comment explains
  that to enable it you change `on:` to `pull_request` and add credentials either
  via `/install-github-app` (creates the app + `CLAUDE_CODE_OAUTH_TOKEN` secret) or
  an `ANTHROPIC_API_KEY` repo secret. Job uses `anthropics/claude-code-action@v1`.
- **`secret-scan.yml`**: `gitleaks/gitleaks-action@v2` on push + pull_request with
  `GITHUB_TOKEN`; header notes that organisation accounts need `GITLEAKS_LICENSE`.
- **`PULL_REQUEST_TEMPLATE.md`**: the Definition-of-Done checklist from
  `conventions/engineering-practices.md` (tests cover behaviour; formatter-clean;
  no dead code; spec/ADR updated if a decision changed; CLAUDE.md updated if a
  command changed).
- **`knowledge/README.md`**: title, a Map table with headers and no rows, a
  "Reading order" list with one placeholder, and a short note: add domain folders
  when research arrives; keep `archive/` verbatim.
- **`knowledge/decisions/README.md`** + **`0000-template.md`**: as in the kit's
  own `knowledge/decisions/`, with an empty index table.
- **`docs/superpowers/README.md`**: the generated index in its empty state (same
  generator output as §4, so the first regeneration is a no-op diff).

### 2. `scaffold.py`

```
scaffold.py --name NAME --stack {node,python} [--parent DIR]
scaffold.py --adopt --stack {node,python} [--dest DIR] [--name NAME]
```

Common: locate templates relative to the script (`../templates/`), build the
placeholder map, render every file in memory, validate no `{{` remains.

**New mode.** `dest = parent / NAME`; `--parent` defaults to the workspace
directory that contains the kit checkout's `plugin/` folder, i.e. the kit
checkout's own root — new projects land beside the other repos there. Refuse with
exit 1 if `dest` exists and is non-empty. Write all files; run `git init -q -b
main`, `git add -A`, `git commit -q -m "Scaffold project from claude-kit"`. Print
`created: <n> files at <dest>` followed by the list and a next-step hint (`pnpm
create …` / `uv init`).

**Adopt mode.** `dest` defaults to cwd and must be inside a git work tree (else
exit 1). `NAME` defaults to the directory name. For each rendered file: if it
exists, skip; else write. Never runs git commands beyond the work-tree check. Print
two lists, `created:` and `skipped (already present):`, then a reminder to verify
`.gitignore` contains `docs/superpowers/**/*.html` and `.env*` if it was skipped.

Exit codes: 0 success; 1 refusal (non-empty dest, not a git repo, unresolved
placeholder); 2 usage (argparse).

### 3. Commands

`plugin/commands/new-project.md` — frontmatter `description` and `argument-hint:
[name] [node|python]`. Body: if name or stack is missing, ask; then run
`python "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" --name <name> --stack <stack>`,
show the script's output, and end with the stack's init command and a pointer to
`/init` for filling in `CLAUDE.md`. Never runs `gh repo create`.

`plugin/commands/adopt-conventions.md` — `argument-hint: [node|python]`. Body: ask
for the stack if missing; run
`python "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" --adopt --stack <stack>` from
the current repo root; show created/skipped; remind the user to review `git status`
before committing.

If `${CLAUDE_PLUGIN_ROOT}` turns out not to be expanded inside command bodies, the
commands fall back to the junction path `~/.claude/skills/claude-kit/scripts/…`;
the plan verifies which works and records it.

### 4. Spec lifecycle and index

**Vocabulary.** Specs and plans carry `- **Status:** draft | approved |
implemented | superseded`. `conventions/spec-driven-development.md` documents it
and adds: when the work a plan describes merges, set its spec (and plan) to
`implemented` in the same PR; when a later spec replaces one, mark the old one
`superseded` and link the successor. Plans written by the `writing-plans` skill do
not carry a Status line by default; the index shows `—` for them until one is
added, and the convention asks executors to add `implemented` at merge.

**`plugin/scripts/spec-index.py [DOCS_DIR]`** (`DOCS_DIR` defaults to
`./docs/superpowers`). If neither `specs/` nor `plans/` exists, exit 0 with no
output. Otherwise, for every `*.md` in each: title = first `# ` heading (fallback:
file stem); status = first match of `\*\*Status:\*\*\s*([a-z]+)` (fallback `—`);
date = first match of `\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})`, else the filename's
`YYYY-MM-DD-` prefix, else `—`. Write `DOCS_DIR/README.md`:

```
# Specs and plans

<!-- generated by claude-kit spec-index.py; do not edit by hand -->

## Specs

| Date | Spec | Status |
|---|---|---|
| 2026-09-15 | [Project scaffolder and spec lifecycle](specs/2026-09-15-project-scaffolder-design.md) | approved |

## Plans

| Date | Plan | Status |
|---|---|---|
```

Rows sorted by date descending, then filename. If the generated text equals the
existing file, do not write (no mtime churn). Exit 0 always; errors to stderr.

**Hook.** `plugin/hooks/on_spec_edit.py`, after a successful render of a matched
file, runs `spec-index.py` with `target.parent.parent` (the `docs/superpowers`
directory). Failures are reported on stderr; exit stays 0.

**Kit's own docs.** `2026-09-14-kit-foundation-design.md` and its plan are set to
`implemented`; this spec's status tracks its lifecycle; `docs/superpowers/README.md`
is generated and committed.

### 5. Tests

- `tests/helpers.py` gains `broken_links(md_files) -> list[str]` (the link check
  from `test_docs.py`, so the same logic checks rendered projects).
- `tests/test_scaffold.py` (runs `scaffold.py` via `run_script`):
  - new mode, each stack: every expected path exists; no `{{` in any file;
    `git rev-parse --abbrev-ref HEAD` is `main`; exactly one commit; `git status
    --porcelain` empty; `ci.yml` contains `pnpm` (node) / `uv` (python);
    `CLAUDE.md` contains the stack's commands; no broken relative links.
  - new mode refuses a non-empty dest with exit 1 and writes nothing.
  - adopt mode in a temp git repo with a pre-existing `CLAUDE.md` and `.gitignore`:
    both skipped and listed, everything else created, commit count unchanged,
    output mentions the two gitignore patterns.
  - adopt mode outside a git repo: exit 1, nothing written.
  - unknown stack: exit 2.
- `tests/test_spec_index.py`: sample specs/plans in `tmp_path`; table rows, order,
  fallbacks (no Status line, date from filename), empty dirs produce header-only
  tables, missing dirs produce no file, second run leaves mtime unchanged.
- `tests/test_on_spec_edit.py`: after rendering a spec, `docs/superpowers/README.md`
  exists and lists it.
- `tests/test_plugin_manifest.py`: both command files exist, start with YAML
  frontmatter containing `description`.
- `tests/test_docs.py`: excludes `plugin/templates/` from the repo-wide link scan
  (template links resolve only after rendering; `test_scaffold` covers them).

### 6. Documentation changes in the kit

- `README.md`: the two commands, one line each; "Developing the kit" unchanged.
- `conventions/project-memory.md`: "Bootstrap it with `/new-project` (new repo) or
  `/adopt-conventions` (existing repo), then `/init` to fill in architecture and
  gotchas; prune hard."
- `conventions/engineering-practices.md`: CI gates list adds "secret scan
  (gitleaks)"; notes the scaffolder ships `ci.yml`, `secret-scan.yml`, a disabled
  `claude-review.yml`, and the PR template.
- `conventions/spec-driven-development.md`: status vocabulary, lifecycle rule,
  generated index.

## Decisions made during design

- **Template tree + Python script**, not a prompt-only command (non-deterministic,
  untestable) and not cookiecutter/copier (dependency and second config language
  for ~15 files).
- **`git init` + first commit, no `gh repo create`**: deterministic and testable
  offline; the remote is a deliberate, separate step.
- **Minimal knowledge layer** (index + decisions + archive), no pre-created domain
  folders: matches "scale to the project".
- **Index generated by the existing hook**, not on demand or by hand: the HTML
  drift showed that "remember to run it" fails.
- **Adopt mode never overwrites or merges**: reviewable via `git status`; the one
  file that would need merging (`.gitignore`) is reported instead.
- **CI templates are ubuntu-only**: the Windows matrix is the kit's own need.
- **AI review disabled by default** (`workflow_dispatch`): enabling needs
  credentials the user chose to defer.

## Success criteria

1. `ruff check`, `ruff format --check`, and `pytest` green locally and in CI on
   Ubuntu and Windows.
2. In a fresh session, `/new-project demo node` creates `<workspace>/demo` on
   `main` with one commit and a clean tree, containing every file in §1; the
   directory is deleted afterwards.
3. `/adopt-conventions` in a project repo lacking `CLAUDE.md` creates only the
   missing files and makes no commit.
4. Editing a spec in this repo regenerates `docs/superpowers/README.md` listing
   both kit specs with their statuses.
5. No private repo names or the Windows username in tracked files.
6. The work lands via a feature branch and PR; worktree and branch are removed.
