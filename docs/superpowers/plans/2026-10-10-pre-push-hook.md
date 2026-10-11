# Pre-push Lint Hook Implementation Plan

- **Status:** draft
- **Date:** 2026-10-10

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffolded repos ship `.githooks/pre-push`, a POSIX hook that runs
the stack's CI lint before a push. New mode enables it (`core.hooksPath`) and
records it executable in the index; adopt mode stages it executable and
prints how to enable it. A template `.gitattributes` keeps the hook LF on
Windows clones. ADR 0029 records the choice; the plugin goes to 0.20.0.

**Architecture:** Two new stack template files rendered by
`plugin/scripts/scaffold.py` into `.githooks/pre-push`; small changes to
`commit_all` (new mode) and `scaffold_adopt` (adopt mode); doc lines in the
project template; tests in `tests/test_templates.py` and
`tests/test_scaffold.py`; a live check on a throwaway GitHub repo.

**Tech Stack:** POSIX `sh`, git, Python 3.11+, pytest, ruff, `gh` CLI.

**Spec:** `docs/superpowers/specs/2026-10-10-pre-push-hook-design.md`

## Context for a cold start

- Repo root: the worktree you are in (branch `feat/pre-push-hook`). Run
  commands from the repo root in Git Bash.
- Test and lint (from `CLAUDE.md`): `pytest`, `ruff check plugin tests`,
  `ruff format --check plugin tests`. Run all three before every commit.
- `tests/helpers.py` exports `PLUGIN` (the `plugin/` dir), `load_module`
  (import a script by path under a unique module name), `run_script`.
- `tests/test_scaffold.py` has its own `EXPECTED` list (the files a new
  project gets), a `git(*args, cwd)` helper that returns stripped stdout and
  raises on failure, `files_under(root)`, and a `repo` fixture (a committed
  git repo with `CLAUDE.md`, `.gitignore` and one spec).
- `tests/test_templates.py` has `EXPECTED` (files under
  `plugin/templates/project/`) and `test_each_stack_has_its_three_files`.
- `plugin/scripts/scaffold.py`: `render_files(name, stack, today)` returns
  `{Path: text}`; `write_file` writes LF; `commit_all(dest, message)` runs
  the git sequence for new mode; `scaffold_new` removes a freshly created
  directory when `commit_all` raises `SystemExit` or `OSError`;
  `scaffold_adopt` writes missing files and prints the report.
- This checkout uses `core.autocrlf=true`, so stack template files may be
  checked out with CRLF. `render_files` reads with `read_text`, which turns
  CRLF into LF, and `write_file` writes LF, so rendered hooks are LF.
- `plugin/.claude-plugin/plugin.json` is at `0.19.0` on `main`; ADR numbers
  up to 0028 are taken, so this ADR is 0029.

## Global Constraints

- The hook files' text is exactly the spec's (Design > The hook files); the
  node hook differs only in the manifest (`package.json`), the tool
  (`pnpm`) and its single lint line `pnpm lint || exit 1`.
- Adopt mode never runs `git config` and never commits.
- Output lines are the spec's, verbatim.

## Answers to the gate's plan questions

- **EXPECTED entries:** `tests/test_templates.py` adds `.gitattributes`;
  `tests/test_scaffold.py` adds `.gitattributes` and `.githooks/pre-push`
  (the list already holds the CI-hardening files). Task 1, Task 2.
- **Failing `git add --chmod=+x` in adopt mode:** handled like every other
  failed git command in `scaffold.py` (`commit_all`): `SystemExit` with
  `error: git add failed: <stderr>` (exit 1). It runs after the
  created/skipped report is printed; the written files stay, as adopt mode
  never rolls back. This keeps the spec's `hooks:` line verbatim
  (it is printed only after staging succeeded). Task 2.
- **Adopt output order:** the existing lines keep their places; the two new
  lines go immediately before `review with git status, then commit.`, which
  is where the spec puts them (after the `skipped` list and its existing
  checks): `hooks:` line, then the `.gitattributes` check. Task 2.
- **Fake tools under MSYS and Linux `sh`:** each fake is a file with no
  extension, LF endings, content `#!/bin/sh\nexit <code>\n`, `chmod 0o755`.
  MSYS (Git for Windows, `noacl` mounts) treats files that start with `#!`
  as executable, and `/bin/sh` resolves inside MSYS and on Linux. The hook
  runs as `[<abs sh>, <abs hook path>]` with the full environment except
  `PATH`, which is set to only the temp `bin` dir (Windows keeps
  `SYSTEMROOT` etc.). Task 2.
- **Failing `git config core.hooksPath`:** it is a step of `commit_all`, so
  it raises `SystemExit` like the others and the new directory is removed.
  Task 2.
- **Where the chmod goes:** in `commit_all`, before the git sequence, via a
  `make_executable(path)` helper that adopt mode reuses. Task 2.

---

### Task 1: Hook templates and `.gitattributes`

**Files:**
- Create: `plugin/templates/stacks/python/pre-push`
- Create: `plugin/templates/stacks/node/pre-push`
- Create: `plugin/templates/project/.gitattributes`
- Modify: `tests/test_templates.py`
- Modify: `tests/test_scaffold.py` (`EXPECTED` only)

**Depends on:** none

- [ ] **Step 1: Failing tests.** In `tests/test_templates.py`, add
  `".gitattributes",` to `EXPECTED`, and replace
  `test_each_stack_has_its_three_files` with:

  ```python
  def test_each_stack_has_its_four_files():
      for stack in ("node", "python"):
          for name in ("ci.yml", "commands.part", "gitignore.part", "pre-push"):
              assert (TEMPLATES / "stacks" / stack / name).exists(), f"{stack}/{name}"
  ```

  Run: `pytest tests/test_templates.py`
  Expected: `test_project_template_has_exactly_the_expected_files` and
  `test_each_stack_has_its_four_files` fail.

- [ ] **Step 2: Create the files.** `plugin/templates/project/.gitattributes`
  is one line: `.githooks/* text eol=lf`.
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

  `plugin/templates/stacks/node/pre-push`:

  ```sh
  #!/bin/sh
  # Pre-push lint: runs the lint CI runs, before the push leaves this machine.
  # Enable once per clone: git config core.hooksPath .githooks
  # Skip once: git push --no-verify
  # Lints the working tree: commit or stash edits first for an exact match
  # with what CI sees.
  if [ ! -f package.json ]; then
    echo "pre-push: no package.json yet, lint skipped"
    exit 0
  fi
  if ! command -v pnpm >/dev/null 2>&1; then
    echo "pre-push: pnpm not found on PATH; install it, or push with --no-verify" >&2
    exit 1
  fi
  pnpm lint || exit 1
  ```

- [ ] **Step 3: Keep `test_scaffold.py` green.** New projects now get
  `.gitattributes`: add `".gitattributes",` to `EXPECTED` in
  `tests/test_scaffold.py`. In `test_render_files_rejects_unresolved_placeholder`
  change the tuple of fake stack files to
  `("ci.yml", "commands.part", "gitignore.part", "pre-push")` (Task 2 makes
  `render_files` read it).

- [ ] **Step 4: Full suite and lint.**
  Run: `pytest; ruff check plugin tests; ruff format --check plugin tests`
  Expected: all tests pass, ruff prints no violations and no files to reformat.

- [ ] **Step 5: Commit.** `git add plugin/templates tests && git commit -m "Pre-push hook templates and .gitattributes"`

### Task 2: Scaffolder renders, enables and stages the hook

**Files:**
- Modify: `plugin/scripts/scaffold.py`
- Modify: `tests/test_scaffold.py`

**Depends on:** Task 1

- [ ] **Step 1: Failing tests.** In `tests/test_scaffold.py`: add
  `".githooks/pre-push",` to `EXPECTED`; add `import os`, `import shutil`,
  `import sys` at the top; then add:

  ```python
  HOOK = ".githooks/pre-push"
  ENABLED = "hooks: pre-push lint is enabled for this clone (core.hooksPath=.githooks)."
  ADOPT_HOOKS = (
      "hooks: .githooks/pre-push is staged; enable it with "
      "`git config core.hooksPath .githooks` (this replaces the current hooks "
      "setup: .git/hooks or an existing core.hooksPath)."
  )


  @pytest.mark.parametrize("stack", ["node", "python"])
  def test_new_project_enables_executable_hook(tmp_path, stack):
      result = run_script(
          SCRIPT, "--name", "demo", "--stack", stack, "--parent", str(tmp_path)
      )
      assert result.returncode == 0, result.stderr
      dest = tmp_path / "demo"
      assert git("config", "core.hooksPath", cwd=dest) == ".githooks"
      assert git("ls-files", "-s", HOOK, cwd=dest).startswith("100755")
      assert ENABLED in result.stdout
      assert result.stdout.index("then: mark build-test") < result.stdout.index(ENABLED)
      assert git("status", "--porcelain", cwd=dest) == ""
      if sys.platform != "win32":
          assert os.access(dest / HOOK, os.X_OK)


  def test_hook_checks_out_lf_with_autocrlf(tmp_path):
      run_script(SCRIPT, "--name", "demo", "--stack", "python", "--parent", str(tmp_path))
      clone = tmp_path / "clone"
      subprocess.run(
          ["git", "clone", "-q", "-c", "core.autocrlf=true",
           str(tmp_path / "demo"), str(clone)],
          check=True, capture_output=True,
      )
      assert b"\r" not in (clone / HOOK).read_bytes()


  def test_adopt_stages_executable_hook_without_config(repo):
      result = run_script(SCRIPT, "--adopt", "--stack", "python", "--dest", str(repo))
      assert result.returncode == 0, result.stderr
      assert ADOPT_HOOKS in result.stdout
      out = result.stdout
      assert out.index("skipped (already present):") < out.index(ADOPT_HOOKS)
      assert out.index(ADOPT_HOOKS) < out.index("review with `git status`")
      assert git("diff", "--cached", "--name-only", cwd=repo).splitlines() == [HOOK]
      assert git("ls-files", "-s", HOOK, cwd=repo).startswith("100755")
      unset = subprocess.run(
          ["git", "config", "--local", "core.hooksPath"], cwd=repo, capture_output=True
      )
      assert unset.returncode == 1
      assert "check .gitattributes" not in out


  def test_adopt_with_own_gitattributes_asks_for_eol_line(repo):
      (repo / ".gitattributes").write_text("* text=auto\n", encoding="utf-8")
      result = run_script(SCRIPT, "--adopt", "--stack", "python", "--dest", str(repo))
      assert result.returncode == 0, result.stderr
      out = result.stdout
      check = "check .gitattributes contains: .githooks/* text eol=lf"
      assert out.index(ADOPT_HOOKS) < out.index(check) < out.index("review with")


  def test_adopt_with_existing_hook_says_nothing_about_hooks(repo):
      hook = repo / ".githooks" / "pre-push"
      hook.parent.mkdir()
      hook.write_text("#!/bin/sh\n", encoding="utf-8")
      result = run_script(SCRIPT, "--adopt", "--stack", "python", "--dest", str(repo))
      assert result.returncode == 0, result.stderr
      assert "hooks:" not in result.stdout
      assert hook.read_text("utf-8") == "#!/bin/sh\n"


  SH = shutil.which("sh")
  needs_sh = pytest.mark.skipif(SH is None, reason="no sh on PATH")


  def run_hook(tmp_path, stack, manifest=None, tools=None):
      """Render the stack's hook and run it with sh in a temp dir whose PATH
      holds only fake tools: {name: exit code}."""
      mod = load_module(SCRIPT, f"scaffold_hook_{stack}")
      hook = tmp_path / "pre-push"
      mod.write_file(hook, mod.render_files("demo", stack, "2026-01-01")[Path(HOOK)])
      work = tmp_path / "work"
      bin_dir = work / "bin"
      bin_dir.mkdir(parents=True)
      if manifest:
          (work / manifest).write_text("{}\n", encoding="utf-8")
      for name, code in (tools or {}).items():
          mod.write_file(bin_dir / name, f"#!/bin/sh\nexit {code}\n")
          (bin_dir / name).chmod(0o755)
      env = {k: v for k, v in os.environ.items() if k.upper() != "PATH"}
      env["PATH"] = str(bin_dir)
      return subprocess.run(
          [SH, str(hook)], cwd=work, env=env, capture_output=True, text=True
      )


  @needs_sh
  def test_hook_skips_without_manifest(tmp_path):
      result = run_hook(tmp_path, "python")
      assert result.returncode == 0, result.stderr
      assert "lint skipped" in result.stdout


  @needs_sh
  def test_hook_fails_without_tool(tmp_path):
      result = run_hook(tmp_path, "python", "pyproject.toml")
      assert result.returncode == 1
      assert "uv not found" in result.stderr


  @needs_sh
  @pytest.mark.parametrize("code,expected", [(1, 1), (0, 0)])
  def test_hook_follows_lint_result(tmp_path, code, expected):
      result = run_hook(tmp_path, "python", "pyproject.toml", {"uv": code})
      assert result.returncode == expected, result.stdout + result.stderr


  @needs_sh
  def test_node_hook_fails_on_lint_error(tmp_path):
      result = run_hook(tmp_path, "node", "package.json", {"pnpm": 1})
      assert result.returncode == 1
  ```

  Format with `ruff format tests` afterwards.
  Run: `pytest tests/test_scaffold.py`
  Expected: every new test fails except
  `test_adopt_with_existing_hook_says_nothing_about_hooks` (it already
  passes), and `test_new_project_has_every_file_and_one_commit` fails too
  (no hook rendered yet). The `@needs_sh` tests skip instead if no `sh` is
  on PATH.

- [ ] **Step 2: Implement in `plugin/scripts/scaffold.py`.**
  - Add constants after `CI_PATH` (no new imports are needed):
    `HOOK_PATH = Path(".githooks/pre-push")` and
    `GITATTRIBUTES = Path(".gitattributes")`.
  - In `render_files`, move the substitution and leftover check into a
    nested helper and use it for the hook too:

    ```python
    def render(text: str, rel: Path) -> str:
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        leftover = PLACEHOLDER_RE.search(text)
        if leftover:
            raise ValueError(f"unresolved placeholder {leftover.group(0)} in {rel}")
        return text
    ```

    The loop body becomes
    `files[rel] = render(source.read_text(encoding="utf-8"), rel)`, and
    after the loop:

    ```python
    hook = (stack_dir / "pre-push").read_text(encoding="utf-8")
    files[HOOK_PATH] = render(hook, HOOK_PATH)
    ```
  - Add after `write_files`:

    ```python
    def make_executable(path: Path) -> None:
        """Set the executable bits (no effect on Windows)."""
        path.chmod(path.stat().st_mode | 0o111)
    ```

  - In `commit_all`, call `make_executable(dest / HOOK_PATH)` before the
    loop, and make the sequence:

    ```python
    for args in (
        ["init", "-q", "-b", "main"],
        ["add", "-A"],
        ["update-index", "--chmod=+x", HOOK_PATH.as_posix()],
        [*identity, "commit", "-q", "-m", message],
        ["config", "core.hooksPath", ".githooks"],
    ):
    ```

  - In `scaffold_new`, after the `then: mark build-test ...` print, add:

    ```python
    print(
        "hooks: pre-push lint is enabled for this clone "
        "(core.hooksPath=.githooks)."
    )
    ```
  - In `scaffold_adopt`, after the workflows README check and before
    `review with ...` (so the created/skipped report is already printed if
    staging fails):

    ```python
    if HOOK_PATH in created:
        make_executable(dest / HOOK_PATH)
        staged = git("add", "--chmod=+x", HOOK_PATH.as_posix(), cwd=dest)
        if staged.returncode != 0:
            raise SystemExit(f"error: git add failed: {staged.stderr.strip()}")
        print(
            "hooks: .githooks/pre-push is staged; enable it with "
            "`git config core.hooksPath .githooks` (this replaces the current "
            "hooks setup: .git/hooks or an existing core.hooksPath)."
        )
        if GITATTRIBUTES in skipped:
            print("check .gitattributes contains: .githooks/* text eol=lf")
    ```

  - Module docstring: after "runs `git init -b main` and one commit." add
    "It records `.githooks/pre-push` as executable and sets
    `core.hooksPath=.githooks`, which enables the pre-push lint hook." and
    after "never commits." add "It stages `.githooks/pre-push` as
    executable when it creates it, and never sets git config."

  Then run `ruff format plugin tests`.

- [ ] **Step 3: Full suite and lint.** The `sh` tests run (not skip) in
  Git Bash on Windows and on Linux.
  Run: `pytest; ruff check plugin tests; ruff format --check plugin tests`
  Expected: all tests pass, ruff prints no violations and no files to reformat.

- [ ] **Step 4: Commit.** `git add plugin/scripts/scaffold.py tests/test_scaffold.py && git commit -m "Scaffolder renders, enables and stages the pre-push hook"`

### Task 3: Docs, ADR 0029, version 0.20.0

**Files:**
- Modify: `plugin/templates/project/CLAUDE.md`
- Modify: `plugin/templates/project/.github/workflows/README.md`
- Create: `knowledge/decisions/0029-pre-push-lint-hook.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `tests/test_plugin_manifest.py`

**Depends on:** none

- [ ] **Step 1: Version test first.** In `tests/test_plugin_manifest.py`
  rename `test_version_is_0_19_0` to `test_version_is_0_20_0` and assert
  `"0.20.0"`.
  Run: `pytest tests/test_plugin_manifest.py::test_version_is_0_20_0`
  Expected: FAIL (`0.19.0 != 0.20.0`). Then set `"version": "0.20.0"` in
  `plugin/.claude-plugin/plugin.json`.

- [ ] **Step 2: Template CLAUDE.md.** Under `## Setup / prerequisites` in
  `plugin/templates/project/CLAUDE.md`, above the existing HTML comment,
  insert (followed by a blank line):

  ```markdown
  - Once per clone: `git config core.hooksPath .githooks`. The pre-push hook
    runs the same lint as CI; `git push --no-verify` skips it once.
  ```

- [ ] **Step 3: Workflows README.** In
  `plugin/templates/project/.github/workflows/README.md`, after the
  paragraph about `../dependabot.yml` (which follows the table) and before
  `## Making checks required`, insert:

  ```markdown
  Locally, `.githooks/pre-push` runs the same lint before every push. Enable
  it once per clone with `git config core.hooksPath .githooks`.
  ```

- [ ] **Step 4: ADR.** Create `knowledge/decisions/0029-pre-push-lint-hook.md`
  in the shape of `0028-pinned-actions-and-workflows-readme.md`:
  title `# ADR 0029: Pre-push lint hook in scaffolded repos`, Status
  `accepted`, Date `2026-10-10`; Context (a lint error was found only by CI
  after the push, costing a CI run and a `/ship` fix attempt); Decision
  (scaffolded repos ship `.githooks/pre-push`, lint only, one POSIX script
  that Git for Windows runs in its `sh`; new mode records it `100755` and
  sets `core.hooksPath`; adopt mode stages it executable and never sets git
  config, because that would silently replace husky, pre-commit or
  `.git/hooks`; `.gitattributes` keeps it LF; no pre-commit hook, because
  auto-fixing and re-staging changes a commit an agent made without it
  seeing the change; no tests or typecheck in the hook, to keep pushes
  fast); Consequences (other clones enable it with one command; the hook
  lints the working tree, not the pushed commits; `--no-verify` skips it;
  already-scaffolded repos are not patched). Add the row to
  `knowledge/decisions/README.md` after 0028:
  `| [0029](0029-pre-push-lint-hook.md) | Pre-push lint hook in scaffolded repos | accepted | 2026-10-10 |`.

- [ ] **Step 5: Kit README.** In `README.md`, after the sentence ending
  "`.github/workflows/README.md` names the checks to require.", add:
  "Scaffolded repos ship a pre-push lint hook (`.githooks/pre-push`)."
  Rewrap the paragraph to its existing width.

- [ ] **Step 6: Full suite and lint.**
  Run: `pytest; ruff check plugin tests; ruff format --check plugin tests`
  Expected: all tests pass, ruff prints no violations and no files to reformat.

- [ ] **Step 7: Commit.** `git add plugin knowledge README.md tests && git commit -m "ADR 0029, docs and version 0.20.0 for the pre-push hook"`

### Task 4: Live check on a throwaway repo

**Files:** none in the kit repo.

**Depends on:** Task 2

- [ ] **Step 1:** Pick a name `<name>` (for example `prepush-check-<4 random
  hex>`). In a new temp directory outside the kit repo, run
  `python <worktree>/plugin/scripts/scaffold.py --name <name> --stack python --parent <tmp>`.
- [ ] **Step 2: First push.** `cd <tmp>/<name>`.
  Run: `gh repo create <name> --private --source . --push`
  Expected: the push succeeds and prints
  `pre-push: no pyproject.toml yet, lint skipped`.
- [ ] **Step 3: Lint error is refused.** `uv init` then
  `uv add --dev pytest ruff`; write `bad.py` containing the single line
  `import os`; commit everything.
  Run: `git push`
  Expected: the push is refused, with ruff's `F401` error shown.
- [ ] **Step 4:** Remove the import (empty file or `print("ok")`), commit,
  `git push`; expect success.
- [ ] **Step 5:** Record the three outcomes for the PR body without the
  repo's name. Write `<name>` to `$TEMP/prepush-live-name.txt` (outside the
  repo; Task 5 reads and deletes it). Leave the GitHub repo for the user to
  delete; delete the local temp directory `<tmp>`.
  Run: `git grep <name>` in the kit worktree.
  Expected: no output (exit 1).

### Task 5: CI on both OSes and the PR body

**Files:** none in the kit repo.

**Depends on:** Task 3, Task 4

This task runs after the branch is pushed and its PR is opened. Under
`/ship`, that is its PR step. Otherwise, first run
`git push -u origin feat/pre-push-hook` and
`gh pr create --title 'Pre-push lint hook in scaffolded repos' --body-file <file>`
(the body summarises the change and the Task 4 outcomes, without `<name>`);
`<pr>` is the number it prints.

- [ ] **Step 1: CI on both legs.**
  Run: `gh pr checks <pr> --watch`
  Expected: every check passes, including the `test` job on
  `ubuntu-latest` and on `windows-latest`. Get the run id with
  `gh run list --branch feat/pre-push-hook --workflow ci --limit 1 --json databaseId`.
  Before this change `main` reported `451 passed, 6 skipped` on ubuntu (the
  6 are `tests/test_install.py`, Windows-only) and `457 passed` on windows.
  Run: `gh run view <run-id> --log | grep -E "[0-9]+ passed"`
  Expected: ubuntu still shows exactly `6 skipped` and windows shows no
  `skipped`, so the new `sh` hook tests ran on both OSes.
- [ ] **Step 2: PR body has no throwaway name.**
  Run: `gh pr view <pr> --json body | grep -c "$(cat $TEMP/prepush-live-name.txt)"`
  Expected: `0`. Then delete `$TEMP/prepush-live-name.txt`.
