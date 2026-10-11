# Pre-push lint hook in scaffolded repos

- **Status:** approved
- **Date:** 2026-10-10

## Purpose

In a scaffolded repo, a lint error is found only by CI, after the push. In
`/ship` each such round costs a CI run and one of its three fix attempts.
This change ships a git `pre-push` hook that runs the same lint CI runs and
blocks the push locally. New repos have it enabled; other clones and adopted
repos enable it with one command.

This spec is built **after** `2026-10-10-template-ci-hardening-design.md`,
because it adds a line to
`plugin/templates/project/.github/workflows/README.md`, which that spec adds (new).

## Scope

**In:**
- `plugin/templates/stacks/python/pre-push` and
  `plugin/templates/stacks/node/pre-push` (new).
- `plugin/scripts/scaffold.py`:
  - `render_files` adds `.githooks/pre-push` from the stack's file;
  - new mode marks it executable and sets `core.hooksPath`;
  - adopt mode stages it executable and prints how to enable it.
- `plugin/templates/project/.gitattributes` (new): `.githooks/* text eol=lf`.
- `plugin/scripts/scaffold.py` module docstring: new mode also sets
  `core.hooksPath`; adopt mode stages the hook.
- `plugin/templates/project/CLAUDE.md`: one line under `## Setup /
  prerequisites`.
- `plugin/templates/project/.github/workflows/README.md`: one paragraph
  under the table.
- `tests/test_templates.py`: `test_each_stack_has_its_three_files` checks
  four files, `pre-push` included (and is renamed to match).
- `tests/test_scaffold.py`: new-mode and adopt-mode assertions, plus hook
  behaviour tests (see Testing).
- `knowledge/decisions/0029-pre-push-lint-hook.md` (new) and its row in
  `knowledge/decisions/README.md`. Use the next free number if 0029 is taken.
- `plugin/.claude-plugin/plugin.json` (minor version bump from `main`),
  `tests/test_plugin_manifest.py`, `README.md` (one line where the README
  describes the scaffolded files: "scaffolded repos ship a pre-push lint
  hook (`.githooks/pre-push`)").

**Out:**
- A pre-commit hook. Auto-fixing and re-staging changes the content of a
  commit an agent made without it seeing the change.
- Running tests or typecheck in the hook. It runs lint only, to keep pushes
  fast.
- A PowerShell variant and setup/unset scripts. Git for Windows runs hooks
  through its bundled `sh`, so one POSIX script covers Windows, and setup is
  one `git config` command.
- A hook in the kit repo itself.
- Changing `core.hooksPath` in adopt mode (see Decisions).

## Design

### The hook files

`plugin/templates/stacks/python/pre-push`:

```sh
#!/bin/sh
# Pre-push lint: runs the lint CI runs, before the push leaves this machine.
# Enable once per clone: git config core.hooksPath .githooks
# Skip once: git push --no-verify
# Lints the working tree: commit or stash edits first for an exact match
# with what CI sees.
if [ ! -f pyproject.toml ]; then
  echo "pre-push: no pyproject.toml yet, lint skipped"
  exit 0
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "pre-push: uv not found on PATH; install it, or push with --no-verify" >&2
  exit 1
fi
uv run ruff check . || exit 1
uv run ruff format --check . || exit 1
```

`plugin/templates/stacks/node/pre-push`: the same, but:
- it checks for `package.json` instead of `pyproject.toml`;
- it checks for `pnpm` instead of `uv`;
- its one lint line is `pnpm lint || exit 1`.

Git runs a non-bare repo's hooks from the root of the working tree, so the
hook does not `cd`. Files are written with LF line endings, which
`write_file` already does. Other clones on Windows usually have
`core.autocrlf=true` (Git for Windows' installer sets it), which would check
the hook out with CRLF and break `sh`. So the template ships
`.gitattributes` with one line, `.githooks/* text eol=lf`, and clones always
get LF.

### Scaffolder

- **`render_files`:** after the project files, it adds
  `files[Path(".githooks/pre-push")]` from
  `TEMPLATES / "stacks" / stack / "pre-push"`, with the same placeholder
  substitution and leftover check as the other files.
- **New mode, `commit_all`:** the git sequence becomes:
  1. `init -q -b main`
  2. `add -A`
  3. `update-index --chmod=+x .githooks/pre-push`
  4. `commit`
  5. `config core.hooksPath .githooks`

  Before step 2, the working-tree file gets its executable bits set
  (`os.chmod(path, path.stat().st_mode | 0o111)`; on Windows this has no
  effect). This makes git run the hook in this clone and keeps
  `git status` clean on Linux and macOS.

  Any failure is handled as today (error, and the created directory is
  removed). Recording the mode in the index makes the hook executable on
  Linux and macOS clones even when it was scaffolded on Windows.
- **Adopt mode:** if `.githooks/pre-push` was created, set the same
  executable bits on the working-tree file, run
  `git add --chmod=+x .githooks/pre-push` (which stages that one file), and
  print:

  ```
  hooks: .githooks/pre-push is staged; enable it with `git config core.hooksPath .githooks` (this replaces the current hooks setup: .git/hooks or an existing core.hooksPath).
  ```

  The line is printed after the `skipped (already present):` list and
  before `review with git status, then commit.` If `.gitattributes` was
  skipped (already present), also print
  `check .gitattributes contains: .githooks/* text eol=lf`.

  If it was skipped (already present), print nothing about hooks.
- **New mode output:** new mode prints one more line after the `then:`
  lines:

  ```
  hooks: pre-push lint is enabled for this clone (core.hooksPath=.githooks).
  ```

### Template CLAUDE.md

Under `## Setup / prerequisites`, above the existing HTML comment:

```markdown
- Once per clone: `git config core.hooksPath .githooks`. The pre-push hook
  runs the same lint as CI; `git push --no-verify` skips it once.
```

### Workflows README

After the table in `plugin/templates/project/.github/workflows/README.md`:

```markdown
Locally, `.githooks/pre-push` runs the same lint before every push. Enable
it once per clone with `git config core.hooksPath .githooks`.
```

### ADR 0029

`knowledge/decisions/0029-pre-push-lint-hook.md`, status `accepted`:
- scaffolded repos ship a lint-only pre-push hook, enabled in new repos;
- adopt mode never sets git config;
- there is no pre-commit hook, and why.

## Decisions

- **Pre-push lint only.** The user approved this. No pre-commit auto-fix.
- **One POSIX script, no PowerShell branch.** Git for Windows runs hooks in
  its `sh`.
- **The hook lints the working tree, not the pushed commits.** Uncommitted
  edits can differ from what CI sees; the hook comment says so.
- **Missing manifest skips; missing tool fails.** A fresh scaffold must
  push before `uv init`. A missing tool after that is a real setup problem.
- **Adopt mode does not set `core.hooksPath`.** It would silently override
  an existing hooks setup (husky, pre-commit, `.git/hooks`).
- **The executable bit lives in the index.** Without it, a hook committed
  from Windows is ignored on other OSes.

## Testing

In `tests/test_scaffold.py`:
- **New mode:** `git config core.hooksPath` in the new repo prints
  `.githooks`, `git ls-files -s .githooks/pre-push` starts with `100755`,
  and the output contains `pre-push lint is enabled for this clone`.
  Update the existing created-files count to include the hook. On
  non-Windows, `os.access(<repo>/.githooks/pre-push, os.X_OK)` is true and
  `git status --porcelain` is empty after new mode.
- **Line endings:** after new mode, `git clone -c core.autocrlf=true` of
  the scaffolded repo into a temp dir checks out `.githooks/pre-push`
  without any carriage return
  (`b"\r" not in path.read_bytes()`).
- **Adopt mode:** in a repo without the hook, the output contains
  `git config core.hooksPath .githooks`, `git diff --cached --name-only`
  lists `.githooks/pre-push`, `git ls-files -s .githooks/pre-push` starts
  with `100755`, and `git config core.hooksPath` is unset.
- **Hook behaviour.** Run the rendered python hook with the `sh` from
  `shutil.which("sh")`, by absolute path; skip the tests if there is none.
  The cwd is a temp dir, and `PATH` contains only a temp `bin` dir.
  1. With no `pyproject.toml`: exit 0, stdout contains `lint skipped`.
  2. With `pyproject.toml` and no `uv`: exit 1, stderr contains
     `uv not found`.
  3. With `pyproject.toml` and a fake `bin/uv` (an executable `#!/bin/sh`
     script that exits 1): exit 1.
  4. The same with a fake `uv` that exits 0: exit 0.
  5. For the node hook, case 3 with `package.json` and a fake `pnpm`.

In `tests/test_templates.py`: each stack has `ci.yml`, `commands.part`,
`gitignore.part` and `pre-push`.

## Success criteria

1. `pytest`, `ruff check plugin tests` and `ruff format --check plugin tests`
   pass, on the kit's CI for both `ubuntu-latest` and `windows-latest`.
2. `pytest tests/test_scaffold.py tests/test_templates.py` passes, including the tests above.
3. **Live check on this Windows machine.** Scaffold a throwaway private
   python repo, create it on GitHub and push.
   1. The first `git push` (no manifest yet) succeeds and prints
      `lint skipped`.
   2. After `uv init` and `uv add --dev pytest ruff`, commit a file with a
      lint error (an unused import). `git push` is refused, with ruff's
      error shown.
   3. After fixing it, `git push` succeeds.

   The repo may be the same one the CI-hardening live check used.
4. The throwaway repo is left for the user to delete. `git grep <name>` in
   the kit repo returns nothing, and `gh pr view --json body` of the kit PR
   does not contain `<name>` (`<name>` is the throwaway repo's name).
