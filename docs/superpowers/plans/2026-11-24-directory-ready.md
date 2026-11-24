# Directory-ready plugin Implementation Plan

- **Status:** approved
- **Date:** 2026-11-24
- **Frozen:** none (the spec has no Frozen bullet; spec D7 freezes nothing, and this plan gives test names and assertions, not a test file's full content)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `plugin/` pass Anthropic's plugin-directory pre-submission checklist (with the portal steps written down), default `/new-project` to a sibling folder inside a foreign git repo, and add plan check `P11-git-mv-add` to `spec-lint.py`.

**Architecture:** Four independent code changes plus an ADR. The Stop hook drops its `${CLAUDE_PROJECT_DIR}` argument and `spec-index.py` reads that variable itself. `scaffold.py`'s `default_parent` gains a third rule (the folder holding the enclosing repo's main checkout). `spec-lint.py` gains one plan rule. The directory checklist becomes `tests/test_directory_ready.py`, run on `git ls-files plugin`; `plugin/README.md`, `plugin.json` (1.2.0) and `docs/directory-submission.md` complete it.

**Tech Stack:** Python 3.11 (stdlib only in plugin scripts), pytest, ruff, Markdown, `claude plugin validate`.

**Spec:** `docs/superpowers/specs/2026-11-24-directory-ready-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-24-directory-ready-design.md`

## Context for the executor

This repo is the kit; the Claude Code plugin lives in `plugin/`. Work in the
worktree `<repo-root>/.worktrees/directory-ready` on branch
`feat/directory-ready`; never switch branches. Setup once:
`pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks: `pytest`,
`ruff check plugin tests`, `ruff format --check plugin tests`.
`tests/helpers.py` exports `PLUGIN`, `REPO`, `load_module(path, name)`,
`clean_env(**extra)` (os.environ minus `CLAUDE_KIT_*`, which does NOT drop
`CLAUDE_PROJECT_DIR`) and `run_script(script, *args, cwd=, env=)`. The repo is
public: never write a machine username or a private repo name into a tracked
file. Lines fit ruff's 88 characters. Edit test files with the Edit or Write
tool, never through a bash heredoc. Commit after each task with a message
ending in `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never run
`plugin/install.py` from a test without a temporary `--home`/`--skills-dir`.

## Global Constraints

- Plugin `name` stays `agent-kit`; `author`, `license` and `description` in `plugin.json` are unchanged.
- `plugin.json` gains `"homepage": "https://github.com/alymo8/claude-kit"`, `"repository": "https://github.com/alymo8/claude-kit"`, `"keywords": ["spec-driven", "workflow", "specs", "code-review", "git-worktrees", "conventions"]`; `"version": "1.2.0"`; no `hooks` key.
- Reserved words a plugin name must not contain: `claude`, `anthropic`, `official`, `plugin`, `mcp`, `test`.
- Every hook command matches `^python3? "\$\{CLAUDE_PLUGIN_ROOT\}/(hooks|scripts)/[a-z_-]+\.py"( --[a-z-]+( [A-Za-z]+)?)*$`. A current command that does not fit is a build stop: report it, never widen the pattern.
- The new Stop command is exactly `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py"`.
- File limits under `plugin/` (tracked files only): each under 5 MiB (`5 * 1024 * 1024` bytes), at most 512 files, no mode `120000`/`160000`, no `.DS_Store`/`Thumbs.db`, no file starting with `version https://git-lfs.github.com/spec/v1`.
- `plugin/README.md`: at least 40 words; links stay inside `plugin/` or are absolute `https://` URLs (`tests/test_publish.py::test_plugin_links_stay_inside_plugin`), so the licence link is `https://github.com/alymo8/claude-kit/blob/main/LICENSE`.
- Root-repo error text: `cannot pick a folder next to <repo>; pass --parent <dir>`, exit code 2.
- P11 rule id `P11-git-mv-add`; message `` `git add` names `<src>`, which `git mv` moved; add the new path with `git add -A <dst> ...` `` with `<src>`/`<dst>` filled in.
- ADR number 0055 (free on `origin/main`); file `knowledge/decisions/0055-directory-listing.md`.
- `docs/directory-submission.md` holds no personal data (no email, no username beyond the public `alymo8/claude-kit` repo name).

## Decisions this plan adds

- **Hooks and the network (Task 4).** The spec's README line "hooks open no network connection" is not true as written: the SessionEnd hook `handoff_snapshot.py` calls `handoff.snapshot`, whose `pr_url` runs `gh pr view` (a GitHub API call) when the branch has an upstream and `gh` is installed. The README and the data-handling answers disclose that one exception instead of the blanket sentence, because the spec's own rule is that rows are written from the scripts and undisclosed behaviour is flagged. Rejected: changing the hook (out of scope).
- **P11 matching (Task 2, plan question 6).** Bare forms only: a command counts when, after splitting the line or span on `&&` and `;`, its `shlex` tokens start with `git` then `mv` or `add`. `git -C x add` is not matched. Spans are read from every non-fence line of the task (prose included); fence lines are read whole, in every fence language. A `git add` argument is compared to a source by equality after stripping one trailing `/`, so `git add <src>/file` is not flagged (the spec says "equals").
- **Root-repo exit (Task 3, plan question 1).** `default_parent` prints the error to stderr and raises `SystemExit(2)` itself; no sentinel.
- **Rule 3 inputs (Task 3, plan questions 2–4).** Rule 3 passes the resolved `--show-toplevel` path to the existing `main_checkout`, and accepts its fallback (a common dir not named `.git` returns the path given). Submodules (their parent folder lies inside the superproject) and a repo at the home folder are accepted as they are, with no guard: the spec's rule names the enclosing repo, and a guard is new scope. A subfolder case is tested.
- **Stop-hook manifest test (Task 1, plan question 5).** `test_stop_hook_regenerates_spec_index` asserts the Stop hooks hold exactly the command `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py"` and that no Stop command contains `CLAUDE_PROJECT_DIR`.

## Review Focus

- `CLAUDE_PROJECT_DIR` is already set in the shell that runs pytest (a Claude Code session or CI): the existing cwd-default test of `spec-index.py` must still test the cwd. Pinned by removing the variable in `test_cli_defaults_to_cwd_docs_superpowers_and_exits_zero` (Task 1).
- The Stop hook fires while the agent's cwd is a subfolder of the project: the index lands in the project's top level, not the subfolder. Pinned by `test_stop_hook_writes_index_in_project_folder` (Task 1).
- `/new-project` runs from a subfolder of a foreign repo, or from a freshly `git init`ed repo with no commit: the project lands beside the repo, never inside it. Pinned by `test_default_parent_in_foreign_repo_subfolder_is_sibling` (Task 3).
- A plan quotes git commands inside code (a Python string, a function call) rather than running them: P11 must not flag it. Pinned by the `quoted` case of `test_p11_cases` (Task 2).
- `plugin/` gains an untracked `__pycache__/` or editor file locally: the checklist must ignore it, as the directory only sees the pushed tree. Pinned by `test_checklist_reads_tracked_files_only` (Task 4).

---

### Task 1: The Stop hook reads the project folder from the environment

**Files:**
- Modify: `plugin/scripts/spec-index.py`
- Modify: `plugin/hooks/hooks.json`
- Test: `tests/test_spec_index.py`
- Test: `tests/test_run_hooks.py`
- Test: `tests/test_plugin_manifest.py`

**Depends on:** none

**Interfaces:**
- Produces: `default_docs_dir() -> Path` in `spec-index.py`; `main(argv: list[str]) -> int` keeps its signature. The Stop command in `hooks.json` becomes `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py"` (Task 4's regex test relies on it).

- [ ] **Step 1: Write the failing tests**

In `tests/test_spec_index.py` add a helper and three tests; also make the existing cwd test drop the variable:

```python
def env_without_project(**extra):
    env = clean_env(**extra)
    if "CLAUDE_PROJECT_DIR" not in extra:
        env.pop("CLAUDE_PROJECT_DIR", None)
    return env


# existing test: pass env=env_without_project() to run_script(SCRIPT, cwd=tmp_path)

def test_cli_uses_claude_project_dir_when_set(tmp_path):
    project, other = tmp_path / "proj", tmp_path / "other"
    make(project / "docs" / "superpowers", "specs", "2026-01-01-a.md", "# A\n")
    other.mkdir()
    env = env_without_project(CLAUDE_PROJECT_DIR=str(project))
    assert run_script(SCRIPT, cwd=other, env=env).returncode == 0
    assert (project / "docs" / "superpowers" / "README.md").exists()
    assert not (other / "docs").exists()


def test_cli_empty_claude_project_dir_falls_back_to_cwd(tmp_path):
    make(tmp_path / "docs" / "superpowers", "specs", "2026-01-01-a.md", "# A\n")
    env = env_without_project(CLAUDE_PROJECT_DIR="")
    assert run_script(SCRIPT, cwd=tmp_path, env=env).returncode == 0
    assert (tmp_path / "docs" / "superpowers" / "README.md").exists()


def test_cli_argument_wins_over_claude_project_dir(tmp_path):
    arg_docs = tmp_path / "arg" / "docs" / "superpowers"
    make(arg_docs, "specs", "2026-01-01-a.md", "# A\n")
    project = tmp_path / "proj"
    make(project / "docs" / "superpowers", "specs", "2026-01-01-b.md", "# B\n")
    env = env_without_project(CLAUDE_PROJECT_DIR=str(project))
    assert run_script(SCRIPT, str(arg_docs), cwd=tmp_path, env=env).returncode == 0
    assert (arg_docs / "README.md").exists()
    assert not (project / "docs" / "superpowers" / "README.md").exists()
```

Import `clean_env` from `helpers`. In `tests/test_plugin_manifest.py` replace the body of `test_stop_hook_regenerates_spec_index`:

```python
    commands = [h["command"] for g in hooks["hooks"]["Stop"] for h in g["hooks"]]
    assert commands == ['python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py"']
    assert not any("CLAUDE_PROJECT_DIR" in c for c in commands)
```

In `tests/test_run_hooks.py`, change the last assertion of `test_real_hooks_json_commands` to `assert stop == [sys.executable, f"{PLUGIN.as_posix()}/scripts/spec-index.py"]`, and add `test_stop_hook_writes_index_in_project_folder(tmp_path, project)`: build a kit with `make_kit(tmp_path)`, run `(plugin / "scripts").mkdir()`, then copy `PLUGIN / "scripts" / "spec-index.py"` into `<plugin>/scripts/`, rewrite `<plugin>/hooks/hooks.json` so `Stop` holds one group with the command `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py"`, `git init -q` the project, create `project/docs/superpowers/specs/2026-01-01-a.md` (`# A`) and a folder `project/sub`, then `run(plugin, "codex", project / "sub", event="Stop", stdin=json.dumps({"cwd": str(project / "sub")}))`. Assert `returncode == 0`, `(project / "docs" / "superpowers" / "README.md").exists()` and `not (project / "sub" / "docs").exists()`.

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/test_spec_index.py tests/test_run_hooks.py tests/test_plugin_manifest.py -q`
Expected: FAIL in `test_cli_uses_claude_project_dir_when_set`, `test_stop_hook_regenerates_spec_index`, `test_real_hooks_json_commands` and `test_stop_hook_writes_index_in_project_folder`; the argument-wins and empty-variable tests already pass (they pin today's behaviour).

- [ ] **Step 3: Implement**

In `spec-index.py` add `default_docs_dir() -> Path`: `Path(os.environ["CLAUDE_PROJECT_DIR"]) / "docs" / "superpowers"` when that variable is set and not empty, else `Path.cwd() / "docs" / "superpowers"`. `main` uses `Path(argv[0]) if argv else default_docs_dir()`. Update the module docstring usage line: DOCS_DIR defaults to `$CLAUDE_PROJECT_DIR/docs/superpowers` when set, else `./docs/superpowers`. In `hooks.json` set the Stop command to `python \"${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py\"` (JSON-escaped quotes).

- [ ] **Step 4: Run the tests to see them pass**

Run: `pytest tests/test_spec_index.py tests/test_run_hooks.py tests/test_plugin_manifest.py tests/test_vibe_plugin.py -q`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add plugin/scripts/spec-index.py plugin/hooks/hooks.json tests/test_spec_index.py tests/test_run_hooks.py tests/test_plugin_manifest.py
git commit -m "Stop hook: spec-index reads CLAUDE_PROJECT_DIR instead of an argument"
```

### Task 2: Plan check P11-git-mv-add

**Files:**
- Modify: `plugin/scripts/spec-lint.py`
- Modify: `knowledge/kit-dev-gotchas.md`
- Test: `tests/test_spec_lint.py`

**Depends on:** none

**Interfaces:**
- Consumes: existing `Line`, `task_spans`, `SPAN_RE` in `spec-lint.py`.
- Produces: `git_commands(text: str) -> list[tuple[str, list[str]]]` (each `(subcommand, args)` for a `git mv`/`git add` found in one line or span, in order; args exclude `git` and the subcommand); `git_mv_add_problems(tasks: list[tuple[int, int, list[Line]]]) -> list[tuple[int, str]]` (line, message). `lint_plan` adds `(n, "P11-git-mv-add", m)`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_spec_lint.py` (after the P10 tests) add:

```python
def task2_fence(*commands):
    """PLAN with Task 2's last line (49) replaced by a bash fence (lines 50+)."""
    return PLAN.replace("Done.", "```bash\n" + "\n".join(commands) + "\n```")


def p11(text, root):
    return [n for n, r in plan_rules(text, root) if r == "P11-git-mv-add"]


@pytest.mark.parametrize(
    ("commands", "lines"),
    [
        (["git mv old new", "git add old"], [51]),  # flagged
        (["git mv old new", "git add -A new"], []),  # new path: fine
        (["git mv dir/ new", "git add dir"], [51]),  # trailing slash
        (["git mv -f a b", "git add a"], [51]),  # flag before the source
        (["git mv a b && git add a"], [50]),  # joined with &&
        (["git add a", "git mv a b"], []),  # add before mv: not checked
        (["git mv a b", 'git add "a'], []),  # shlex cannot split: skipped
        (['run("git mv a b")', "git add a"], []),  # quoted: no command
    ],
    ids=["flag", "new", "slash", "force", "and", "before", "unsplit", "quoted"],
)
def test_p11_cases(root, commands, lines):
    plan_root(root)
    assert p11(task2_fence(*commands), root) == lines
```

Also add `test_p11_other_task_not_flagged` (put the move in Task 1 with `PLAN.replace('git commit -m "x"', 'git mv a b\ngit commit -m "x"')`, then the add in Task 2 via the same replacement of `Done.`; assert `p11(...) == []`), `test_p11_inline_spans_count` (replace `Done.` with a prose line holding two backticked spans, the move of `a` to `b` first and the add of `a` second; assert `[49]`), `test_p11_message_names_src_and_dst` (the `flag` case; the message from `sl.lint_plan` contains `` `git add` names `old` `` and `` `git add -A new ...` ``), and add `("Done.", "```bash\ngit mv a b\ngit add a\n```", True, 51, "P11-git-mv-add")` to the `test_each_plan_rule_alone` parameters.

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/test_spec_lint.py -q -k "p11 or each_plan_rule"`
Expected: FAIL on the `flag`, `slash`, `force`, `and` cases, the inline-span test, the message test and the new `P11-git-mv-add` row.

- [ ] **Step 3: Implement**

In `spec-lint.py`: `git_commands(text)` splits `text` with `re.split(r"&&|;", text)`, runs `shlex.split(segment)` (posix) on each, skips a segment that raises `ValueError`, and keeps one whose tokens are `git` then `mv` or `add`. `git_mv_add_problems(tasks)` walks each task's body in line order: a fence line (`code` true) is one text; a non-fence line yields each `SPAN_RE` span. For `mv`, non-flag args (not starting with `-`) give sources = all but the last, destination = the last; remember `source.rstrip("/") -> destination` for this task only. For `add`, report the first non-flag arg whose `rstrip("/")` is a remembered source, on that line, with the Global Constraints message. Add `P11-git-mv-add` to the module docstring after `P10-depends` (one sentence: a `git add` after a `git mv` in the same task naming a moved source; bare `git mv`/`git add` in fence lines and backtick spans, split on `&&` and `;`). In `knowledge/kit-dev-gotchas.md`, append "spec-lint P11 flags this." to the bullet that starts "A plan task that runs `git mv".

- [ ] **Step 4: Run the tests to see them pass**

Run: `pytest tests/test_spec_lint.py -q`
Expected: PASS (all).

- [ ] **Step 5: Check existing plans for false alarms (success criterion 3)**

Run: `for f in docs/superpowers/plans/*.md; do python plugin/scripts/spec-lint.py "$f" | grep P11-git-mv-add; done`
Expected: no output. For each line printed, open that plan line by hand: keep it only if a `git mv` source really is named in a later `git add` of the same task, note the plan path and line for the PR body, and do not edit the plan. Any other hit is a false alarm: fix `git_mv_add_problems` and add a test case for it.

- [ ] **Step 6: Commit**

```bash
git add plugin/scripts/spec-lint.py knowledge/kit-dev-gotchas.md tests/test_spec_lint.py
git commit -m "spec-lint: P11 flags a git add of a path git mv moved"
```

### Task 3: `/new-project` defaults to a sibling of a foreign repo

**Files:**
- Modify: `plugin/scripts/scaffold.py`
- Modify: `plugin/commands/new-project.md`
- Test: `tests/test_scaffold.py`

**Depends on:** none

**Interfaces:**
- Consumes: existing `main_checkout(kit: Path) -> Path`, `load_kit_hook()`, `PLUGIN_ROOT`.
- Produces: `enclosing_repo(cwd: Path) -> Path | None` (resolved `git -C cwd rev-parse --show-toplevel`, None on a non-zero exit or `OSError`); `default_parent(cwd: Path) -> Path` with rule 3 and the exit-2 case.

- [ ] **Step 1: Write the failing tests**

In `tests/test_scaffold.py`, reusing `copy_plugin`, `fake_kit`, `git` and `run_script`:

```python
def test_default_parent_in_foreign_repo_subfolder_is_sibling(tmp_path):
    script = copy_plugin(tmp_path)
    repo = tmp_path / "a" / "repo"
    (repo / "sub").mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=repo)  # no commit on purpose
    result = run_script(
        script, "--name", "demo", "--stack", "python", cwd=repo / "sub"
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "a" / "demo" / "CLAUDE.md").is_file()
    assert not (repo / "demo").exists() and not (repo / "sub" / "demo").exists()


def test_default_parent_in_foreign_worktree_is_main_checkouts_parent(tmp_path):
    script = copy_plugin(tmp_path)
    repo = tmp_path / "a" / "repo"
    repo.mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=repo)
    ident = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    git(*ident, "commit", "-q", "--allow-empty", "-m", "init", cwd=repo)
    wt = (repo / ".worktrees" / "w").resolve()
    git("worktree", "add", "-q", str(wt), cwd=repo)
    result = run_script(script, "--name", "demo", "--stack", "python", cwd=wt)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "a" / "demo").is_dir()
    assert not (wt / "demo").exists()


def test_default_parent_repo_at_root_exits_2(tmp_path, monkeypatch, capsys):
    mod = load_module(SCRIPT, "scaffold_root_repo")
    monkeypatch.setattr(mod, "PLUGIN_ROOT", tmp_path / "cache" / "plugin")
    monkeypatch.setattr(mod, "main_checkout", lambda path: Path(path.anchor))
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", "-b", "main", cwd=repo)
    with pytest.raises(SystemExit) as exc:
        mod.default_parent(repo)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "cannot pick a folder next to" in err and "pass --parent <dir>" in err
```

The outside-any-repo case (`test_default_parent_from_copy_outside_kit_is_cwd`) and the kit cases (`test_default_parent_in_child_repo_is_kit_root`, `test_default_parent_in_kit_worktree_is_main_checkout`, `test_default_parent_of_real_checkout`) already exist and must stay unchanged.

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/test_scaffold.py -q -k default_parent`
Expected: FAIL in the three new tests (the project lands inside the repo or worktree; no exit 2).

- [ ] **Step 3: Implement**

Add `enclosing_repo(cwd)`. In `default_parent`, after the two kit rules and before `return cwd`: when `enclosing_repo(cwd)` gives a top level, take `main = main_checkout(top)`; if `main.parent == main`, print `error: cannot pick a folder next to {main}; pass --parent <dir>` to stderr and `raise SystemExit(2)`; else return `main.parent`. Update the module docstring's PARENT sentence and the `--parent` help text to list the new rule ("else, inside another git repo, the folder that holds that repo's main checkout"). In `plugin/commands/new-project.md` change the sentence to: "The project is created in the kit's main checkout when the current folder is inside a kit checkout or one of its worktrees, else in the kit checkout the plugin runs from (a contributor link), else, inside another git repo, in the folder that holds that repo (never inside it), else in the current folder; never in the plugin cache or a worktree."

- [ ] **Step 4: Run the tests to see them pass**

Run: `pytest tests/test_scaffold.py -q`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add plugin/scripts/scaffold.py plugin/commands/new-project.md tests/test_scaffold.py
git commit -m "new-project: default to a sibling folder inside a foreign git repo"
```

### Task 4: Directory checklist, plugin README, manifest 1.2.0 and the submission guide

**Files:**
- Create: `plugin/README.md`
- Create: `docs/directory-submission.md`
- Create: `tests/test_directory_ready.py`
- Modify: `plugin/.claude-plugin/plugin.json`
- Test: `tests/test_plugin_manifest.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: Task 1's Stop command (the only command that used a second variable).
- Produces: in `tests/test_directory_ready.py`, pure checkers each returning a list of problem strings (empty means clean): `entry_problems(entries: list[tuple[str, str]]) -> list[str]` (mode, path), `size_problems(sizes: dict[str, int]) -> list[str]`, `lfs_problems(heads: dict[str, bytes]) -> list[str]`, `readme_problems(text: str, scripts: list[str]) -> list[str]`, `manifest_problems(data: dict) -> list[str]`, plus `COMMAND_RE` (the Global Constraints pattern) and `tracked(root: Path) -> list[tuple[str, str]]` (mode, path from `git -C root ls-files -s plugin`, files missing on disk skipped).

- [ ] **Step 1: Write the failing tests**

`tests/test_directory_ready.py` holds the checkers above and these tests:

- `test_real_tree_is_clean`: on `tracked(REPO)`, each checker returns `[]` (sizes from `stat().st_size`, heads from the first 64 bytes, `readme_problems` on `plugin/README.md` with the script names `re.findall(r"[\w-]+\.py", ...)` from every `hooks.json` command, `manifest_problems` on `plugin.json`), and every `hooks.json` command `COMMAND_RE.fullmatch`es.
- `test_entry_problems_fail` parametrized: `("120000", "plugin/x")`, `("160000", "plugin/sub")`, `("100644", "plugin/a/.DS_Store")`, `("100644", "plugin/Thumbs.db")` each give one problem; `("100644", "plugin/ok.py")` gives none.
- `test_size_problems_fail`: `{"plugin/big": 5 * 1024 * 1024}` gives a problem, `{"plugin/ok": 5 * 1024 * 1024 - 1}` none, and 513 one-byte files give a problem.
- `test_lfs_problems_fail`: `b"version https://git-lfs.github.com/spec/v1\noid sha256:..."` gives a problem, `b"print(1)\n"` none.
- `test_readme_problems_fail`: 39 words naming every script gives a problem; 40 words missing one script name gives a problem; 40 words naming all gives none.
- `test_manifest_problems_fail` parametrized on a copy of the real manifest: each of `license`, `description`, `author`, `version` removed; `homepage` set to `"not a url"` and to `"http://"`; `name` set to `"Agent_Kit"`, `"agent-plugin"` and `"claude-kit"`; a `hooks` key added: each gives at least one problem.
- `test_command_pattern_rejects` parametrized: the old Stop command `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py" "${CLAUDE_PROJECT_DIR}/docs/superpowers"`, `python3 -c "print(1)"`, `python "${CLAUDE_PLUGIN_ROOT}/hooks/*.py"`, `python "$HOME/hooks/x.py"` each fail `COMMAND_RE.fullmatch`.
- `test_checklist_reads_tracked_files_only`: in a temporary git repo with a committed `plugin/ok.py` and an untracked `plugin/.DS_Store`, `entry_problems(tracked(repo)) == []`.

`manifest_problems` parses `homepage` with `urllib.parse.urlparse` and needs scheme `https` and a non-empty `netloc`; the name must match `^[a-z0-9]+(-[a-z0-9]+)*$` and contain none of the reserved words as substrings. In `tests/test_plugin_manifest.py`, rename `test_version_is_1_1_0` to `test_version_is_1_2_0` asserting `"1.2.0"`, and add `test_homepage_and_repository` asserting both equal `https://github.com/alymo8/claude-kit` and `keywords` equals the Global Constraints list.

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/test_directory_ready.py tests/test_plugin_manifest.py -q`
Expected: FAIL in `test_real_tree_is_clean` (no `plugin/README.md`, no `homepage`), `test_version_is_1_2_0` and `test_homepage_and_repository`; the fixture tests pass once the checkers exist.

- [ ] **Step 3: Write `plugin/README.md` and update `plugin.json`**

`plugin.json`: add `homepage`, `repository`, `keywords` and set `version` to `1.2.0` per Global Constraints. `plugin/README.md` follows spec Design 1 in order: what the kit is and who it is for; **Install** (the three `/plugin` lines from the repo `README.md` Install section, and the contributor note from `docs/setup.md`: a contributor who also installs from the marketplace reruns `python plugin/install.py` so only one copy loads); **What runs automatically**, a table with one row per hook in `plugin/hooks/hooks.json` (event, script file name, what it reads, writes and prints), written after reading each script, and one line saying `hooks/run.py` runs the same hooks for Vibe, Codex and Cursor; **Commands and scripts** (`/ship`, `/ship-many`, `/ship-fast` and the gates run `git`, `gh`, `python` and subagents, push branches, open pull requests, and `/ship` merges them); **Network**: no hook opens a connection except the SessionEnd `handoff_snapshot.py`, which runs `gh pr view` when the branch has an upstream and `gh` is installed (see "Decisions this plan adds"); then each script under `plugin/scripts/` that reaches the network, found by reading each one (start from `grep -ln "gh\|urlopen\|fetch\|push\|clone" plugin/scripts/*.py plugin/install.py` and confirm by reading), and each command or skill that calls `gh`; no telemetry, nothing sent elsewhere; **Licence**: MIT, linking `https://github.com/alymo8/claude-kit/blob/main/LICENSE`.

- [ ] **Step 4: Write `docs/directory-submission.md`**

Sections in spec Design 4 order: Before you start (a paid claude.ai plan; run `claude plugin validate ./plugin --strict` and `pytest tests/test_directory_ready.py`); Source (repo `alymo8/claude-kit`, plugin path `plugin`, tracked branch `main`); Validate (fix a warning in the repo and push, then revalidate; a hold means a reviewer reads it: answer in the portal); Listing details (a drafted one-line summary, a short description of two or three sentences, the six keywords); Data handling (drafted answers taken from `plugin/README.md`'s Network section, including the `gh pr view` exception); Compliance (the contact email and acknowledgements are the owner's; this guide does not fill them in); After publishing (every version bump on `main` is scanned and reviewed again; add the directory route to the README Install section as a separate change). Start it with a `# ` title.

- [ ] **Step 5: Run the tests to see them pass**

Run: `pytest tests/test_directory_ready.py tests/test_plugin_manifest.py tests/test_publish.py tests/test_docs.py tests/test_vibe_plugin.py -q`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add plugin/README.md plugin/.claude-plugin/plugin.json docs/directory-submission.md tests/test_directory_ready.py tests/test_plugin_manifest.py
git commit -m "Directory readiness: plugin README, manifest 1.2.0, checklist test, submission guide"
```

### Task 5: ADR 0055 and the final checks

**Files:**
- Create: `knowledge/decisions/0055-directory-listing.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `knowledge/decisions/0052-published-plugin.md`

**Depends on:** Task 1, Task 2, Task 3, Task 4

**Interfaces:**
- Consumes: the finished branch from Tasks 1 to 4 (the final checks run over all of it).

- [ ] **Step 1: Write ADR 0055**

MADR format like `0054-vibe-native-plugin.md`: title `# ADR 0055: The kit targets Anthropic's plugin directory, and /new-project defaults to a sibling folder`; `- **Status:** accepted`; `- **Date:** 2026-11-24`; Context, Decision (D1: the repo is made checklist-clean, `tests/test_directory_ready.py` runs the checklist in CI, the owner submits in the portal; rejected: a guide with no repo changes. D2: inside a foreign git repo `/new-project` defaults to the folder holding that repo's main checkout, a repo at a filesystem root exits 2; rejected: stopping to ask for `--parent`. D8: the Stop hook drops `${CLAUDE_PROJECT_DIR}` and `spec-index.py` reads it), Consequences (each version on `main` is rescanned; README Install line once listed; `docs/directory-submission.md` holds the steps; the spec's sentence "hooks open no network connection" was corrected in `plugin/README.md`, which discloses the SessionEnd `gh pr view` call). Link `[ADR 0052](0052-published-plugin.md)`.

- [ ] **Step 2: Update the index and ADR 0052**

In `knowledge/decisions/README.md`: the 0052 row's status becomes `accepted; extended by 0054, 0055`, and a new last row `| [0055](0055-directory-listing.md) | The kit targets Anthropic's plugin directory; /new-project defaults to a sibling folder | accepted | 2026-11-24 |`. In `0052-published-plugin.md`, append to the Status line, after the 0054 parenthetical: `, 0055 ([ADR 0055](0055-directory-listing.md): directory listing and the /new-project sibling default)`.

- [ ] **Step 3: Check the ADR links**

Run: `pytest tests/test_docs.py -q && grep -c "0055" knowledge/decisions/README.md knowledge/decisions/0052-published-plugin.md`
Expected: PASS, and a count of at least 1 for each file (`README.md:2`, `0052-published-plugin.md:1` or more).

- [ ] **Step 4: Run every success-criterion check**

Run: `pytest && ruff check plugin tests && ruff format --check plugin tests && claude plugin validate ./plugin --strict && claude plugin validate .`
Expected: every command exits 0 (pytest all pass, ruff clean, both validations report no error). A validation warning or error is fixed in the repo, never suppressed.

- [ ] **Step 5: Commit**

```bash
git add knowledge/decisions/0055-directory-listing.md knowledge/decisions/README.md knowledge/decisions/0052-published-plugin.md
git commit -m "ADR 0055: directory listing and the /new-project sibling default"
```
