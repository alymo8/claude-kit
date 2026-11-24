# Gotchas when developing the kit

Things that cost time in past runs and are not obvious from the code.

## Tests and lint

- `pyproject.toml` already sets `addopts = "-q"`, so `pytest -q` runs at
  `-qq` and prints no summary line. Run plain `pytest` (or
  `pytest -o addopts=""`) when you need the pass count.
- Test code written in a plan is copied verbatim into `tests/`, so it must
  fit ruff's 88-character line limit; a longer line fails
  `ruff format --check plugin tests`. `ruff format` never splits a long
  string literal (E501 stays), so split it by hand in the plan, but it
  joins a split string or wrapped signature back onto one line when that
  fits in 88 characters, so split only what would not fit.
- `test_relative_markdown_links_resolve` checks every tracked `.md`, specs
  included, and does not skip code spans: a link-shaped example such as a
  bracketed name followed by a parenthesised `file.md` fails it. Describe
  the shape in prose instead.
- In `tests/test_ship_command.py`, `_step(n)` collapses whitespace but
  `_stops()` returns the raw section, so a phrase that wraps across lines
  in `ship.md` fails an `in _stops()` assertion. Normalise first:
  `" ".join(_stops().split())`.
- `_step(n)` in `tests/test_ship_command.py` splits `ship.md` on every
  line that starts at column 0 with `<digits>. `. Prose added inside a step
  (sub-items included) stays indented 3 spaces (4 for steps 10–12), or
  every later step's tests break. Plans that edit `ship.md` should say so.
  Steps 8–12 live in `plugin/references/ship-finish.md`; the tests read
  `helpers.command_text("ship")`, which inlines each reference file after
  the paragraph that points to it.
- A skill or command at 20,000 bytes or more fails `tests/test_skill_size.py`
  (Claude Code cuts it there after a compaction). Move late sections to
  `plugin/references/`, never into `commands/` (every `.md` there becomes a
  slash command), and point to them as
  `${CLAUDE_PLUGIN_ROOT}/references/<file>.md`. The same file must state
  the fallback once with the `FALLBACK_RULE` line from
  `tests/test_skill_size.py`, or give the per-pointer
  `<plugin root>/references/<file>.md` fallback together with the exact
  `ROOT_NOTE` sentence from that test, or the pointer test fails.
- Writing test code through a bash heredoc into a Python script turns
  `\n` escapes inside string literals into real line breaks, so the
  test file no longer parses. Edit test files with the Edit tool. The
  same goes for `\x00` in a patch run through `python -c` or a heredoc:
  it lands as a real NUL byte and Python fails with `source code string
  cannot contain null bytes`. Put patch scripts in a file first. A regex
  `\b` patched in the same way (or through a `sed` replacement) lands as a
  backspace byte (0x08) or a bare `b`, the tests still parse, and the
  pattern silently stops matching; check with `grep -c $'\x08' <file>`.
- Before promising how much a command can shrink, read its tests:
  `tests/test_ship_command.py` and `tests/test_ship_fast_command.py` pin
  about 60 exact phrases, and one pins a line break
  (`"one\n   copy, the only one the run starts"` in step 5 of
  `ship-fast.md`), so rewrapping that sentence fails the test.
- The kit version lives in `plugin/.claude-plugin/plugin.json` and is
  pinned in `tests/test_plugin_manifest.py`; bump both in the same commit,
  and rename the test (`test_version_is_0_32_0`) to the new version.
- Measure a tracked file's size with `git show HEAD:<path> | wc -c`, not
  `wc -c <path>`: the working copy is checked out with CRLF and reads a
  few hundred bytes larger than the stored LF file.
- Appending to a CRLF file with a bash heredoc mixes line endings, and
  `ruff format --check` then flags the file. Run `ruff format <file>`.
- Git before 2.32 ignores `GIT_CONFIG_GLOBAL`, so a test that hides the
  user's git identity with it still sees the real one on such a machine.
  Also point `HOME`, `USERPROFILE` and `XDG_CONFIG_HOME` at `tmp_path`.
- CI runners have no git identity; this machine has one. Code that adds
  `-c user.name=...` when none is set takes a different path on CI, so a
  fake `git` that matches `args[0] == "commit"` passes here and fails there.
  Match `"commit" in args`, and run identity-sensitive tests once with
  `GIT_CONFIG_GLOBAL`, `HOME` and `USERPROFILE` pointed at an empty folder.
- A hook must exit 0, but argparse errors raise `SystemExit`, which
  `except Exception` does not catch: a hook with argparse catches
  `(Exception, SystemExit)` around `parse_args`.
- `ruff format --check plugin tests` (ruff 0.16) includes `.md` files and
  formats the Python fences inside them, so a code block in a skill must be
  ruff-clean and its reformatting can push a line-capped skill over its cap.

## Worktree-isolated sessions (`/ship`, `parallel-tasks`)

- Under `/ship`, a background full-suite run in the feature worktree while
  the next task's implementer edits it reports that implementer's
  half-done files as failures or format diffs. To check a finished task's
  commit alone, run the suite in a detached copy:
  `git worktree add --detach <scratchpad>/tN <sha>`, then remove it.

- The isolation guard refuses Bash commands it cannot prove stay inside the
  session's worktree: shell variables in paths (`rm "$M/$f"`), heredocs
  feeding `python` that mention git, `$(...)` around a script, and chained
  git commands aimed at another worktree. Use literal absolute paths, one
  plain command per call, the Edit tool for file edits, and
  `git -C <worktree>` from subagents working in task worktrees.
- A heredoc fed to `python` inside a longer command line is refused even
  when it does not mention git. Write the script to the scratchpad with
  the Write tool and run `python <scratchpad>/script.py <args>`.
- When `/ship` runs from a session worktree and makes a separate feature
  worktree, an SDD implementer told to edit that feature worktree is refused
  ("Do not write to other worktrees' files") and may fall back to checking
  out its own branch in the session worktree. Give each implementer its own
  `git worktree add <tmp>/claude-tasks/<branch-slug>/task-N
  -b feat/<slug>-task-N HEAD`, as `parallel-tasks` does, then
  `git merge --ff-only` it into the feature branch and remove it.
- A frozen test that pins old behaviour blocks a review fix to that
  behaviour; check `**Frozen:**` tests before fixing, and report the fix as
  a follow-up if the spec keeps the old behaviour.
- A feature worktree made with `git worktree add -b feat/<slug> <path>
  origin/main` tracks `origin/main`, so `handoff.py state` reports
  "upstream: origin/main". The first push must be
  `git push -u origin feat/<slug>`.
- Resuming `/ship` on a feature branch that `main` has moved past: rebase
  it onto `origin/main` first. The gate records still verify (they hash
  only the spec and plan), so settle the plan's stale values (version, ADR
  number, moved paths) with `Ruling:` lines in the SDD ledger, and point
  each task subagent's prompt at those lines.
- A plan task that changes no repo file but dispatches its own subagent
  or writes auto-memory (a scenario check) runs in the main session, not
  as a `parallel-tasks` task subagent.

## Why `/ship` and `/ship-fast` say what they say

The commands keep the rules and leave out the reasons; the reasons are here.

- **Git lock retry:** every worktree shares one `.git` directory, so
  concurrent worktrees (`parallel-tasks`, `/ship-many`) collide on its
  lock files.
- **PR title through the Bash tool, in single quotes:** PowerShell's
  native-argument quoting drops `"` and mangles non-ASCII; single quotes
  keep backticks and `$` literal; a literal command passes the worktree
  isolation guard, which refuses command substitution.
- **Red first `main` CI on a new `/ship-fast` repo:** pytest exits 5 on an
  empty suite. `uv init --no-workspace` stops a parent `pyproject.toml`
  from adopting the new project.
- **Plugin path fallback:** `${CLAUDE_PLUGIN_ROOT}` is not always expanded in
  command text, so each long command states once that the plugin root from
  the kit map (else `~/.claude/skills/agent-kit`) stands in for it
  (`tests/test_skill_size.py` accepts that line or a per-pointer fallback).
  A marketplace install has no skills-dir link, so the kit map's
  `Plugin root:` line is the only path that always works.
- **Print-mode wait ceiling:** `claude -p` ends a `run_in_background`
  command after 10 minutes (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`), so
  `ship-child.py` sets it to `0` for `/ship-many` children.
- **Background Bash timeout is not enforced:** a `run_in_background`
  command ignores its timeout (one child ran about 7 hours), so the 2-hour
  limit lives in `ship-child.py`, which kills the whole process tree.
- **Why a resume skips a child that wrote a handoff:** `/ship` writes a
  `Written ... by /handoff` line only when a stop rule fires, which needs
  the user; the SessionEnd snapshot also writes the file but marks its
  lines `by session-end snapshot`, so only the `Written` line's author,
  not the file's existence or time, tells a stop rule apart.

## Scripts on Windows

- Python's stdout is cp1252 when piped on Windows, so printing a path
  with characters outside cp1252 raises `UnicodeEncodeError`. A script
  that prints filesystem paths calls `sys.stdout.reconfigure(encoding="utf-8")`
  first, as `docker-disk.py` does. Do not use `errors="replace"`: it turns
  non-ASCII into `?`, which hides it from callers that check for it.
- Docker Desktop's resource saver stops the `docker-desktop` distro when
  idle, so `docker-disk.py` prints `used ?` (it never starts the distro).
  To compare its numbers by hand, run `docker info` first to wake it.
- Git paths with `"`, `\`, a tab or a newline: git C-quotes them in
  newline-separated output even with `core.quotepath=off`, so parse
  `ls-tree`/`log --name-only` with `-z`. Windows cannot create such files,
  so their tests are `skipif win32` and run only in CI. To check one
  locally, build the commit with plumbing in a scratch repo:
  `git config core.protectNTFS false`, then
  `git update-index --add --cacheinfo 100644,<blob>,'t/q"x.py'` and commit.
- Claude Code transcripts write one `assistant` record per content block,
  each repeating the same `message.id` and `usage`. `token-report.py`'s
  turn count, token totals and token restart simulation count every record
  (about twice the real calls); `--dollars` and `--ship` count each
  `message.id` once. Compare like with like.

## Hooks

- Claude Code injects at most 10,000 characters of a hook's
  `additionalContext`. Above that, only a preview reaches the session.
  Keep a size test with a margin (`workspace_rules_inject.py` is capped at
  9,500 and injects about 9,000 today).
- The README's "N hooks" sentence and its assertion in `tests/test_docs.py`
  are not derived from `plugin/hooks/hooks.json`, so a PR adding a hook can
  leave them stale (#52 did). Count the `python` commands in `hooks.json`
  and update both; do not trust the number in a spec or the README.
  `test_real_hooks_json_commands` in `tests/test_run_hooks.py` also pins
  the SessionStart command count; adding or removing a SessionStart hook
  changes it too.
- To run a hook by hand on Windows, pipe its stdin from Bash
  (`echo '{}' | python plugin/hooks/<hook>.py`). PowerShell 5.1's
  `'{}' | python ...` sends a UTF-8 BOM, and hooks that parse stdin as JSON
  (`handoff_inject.py`) print `Unexpected UTF-8 BOM`; Claude Code itself
  sends none.
- Check a marketplace install without touching your own config: set
  `CLAUDE_CONFIG_DIR` to a scratch folder, then
  `claude plugin marketplace add <worktree>` and
  `claude plugin install agent-kit@agent-kit`. The install path is under
  `agent-kit@agent-kit` in `<config>/plugins/installed_plugins.json`; run
  the SessionStart commands from `<installPath>/hooks/hooks.json` with
  `CLAUDE_PLUGIN_ROOT=<installPath>`. Delete the folder afterwards.
- Removing (or renaming) a command also means deleting its generated
  wrapper `plugin/agent-skills/<name>/`; `python plugin/scripts/agent-skills.py
  --check` fails until the two match.
- Check the Vibe plugins headless from a child repo:
  `vibe -p "<ask it to quote the Kit map and Plugin root lines>" --max-turns 2`.
  Headless Vibe denies every tool call that needs approval ("a headless run
  cannot give"), `--add-dir` included, so a kit command that reads
  `<plugin>/commands/*.md` needs an interactive session to verify.
- `python plugin/install.py --agent vibe` run from a worktree keeps the old
  `~/.agents/skills/` links (they point into the main checkout); run it from
  the main checkout to remove them.

## Main checkout

- The spec-index hook rewrites `docs/superpowers/README.md` in the main
  checkout with LF endings, which shows as modified and makes
  `git pull --ff-only` abort. If `git diff --ignore-cr-at-eol --stat
  docs/superpowers/README.md` is empty, the change is line endings only:
  `git checkout -- docs/superpowers/README.md`, then pull.
- The installed plugin is a junction to the main checkout's `plugin/`, so
  skills and commands load from local `main`. If local `main` is behind
  (`git log --oneline main..origin/main -- plugin/`), a `/ship` run follows
  the older text; read the newer command or skill from the feature
  worktree and follow that.

## Gates

- Answering a spec gate's `## Plan questions` in the plan can make an
  answer a plan-introduced decision, so the plan gate returns
  `pass-with-decisions`, and `/ship` approves the decision itself and lists
  it in the PR's `Plan decisions (auto-approved)` section. Answers that
  stay inside the spec's Scope In files pass; an answer that touches a
  file outside Scope In (a new test in another test file) is flagged, and
  so is an answer that settles behaviour the spec left open, even inside
  Scope In (which PR heading a user-approved list gets). Keep answers
  inside Scope In, and resolve behaviour questions in the spec before
  gating it, to keep that list short.
- Grep a spec for private repo names before gating it, not only before
  pushing. Scope Out lines about personal memory or other projects are
  where names slip in. Rewording a spec afterwards changes its hash and
  forces a re-gate, and then a plan re-gate.
- Start a hand-written spec or plan from the newest one's skeleton:
  `spec-lint.py` wants a spec's `## Decisions` and `## Success criteria`
  (each criterion naming its check), and a plan's `### Task N:` headings,
  `- [ ] **Step N:**` bullets, a `**Files:**` line, a step with
  ``Run `cmd` `` then `Expected:`, and a commit step in every task
  (`**Files:** none` waives the commit).
- A plan task that runs `git mv <dir> <new>` must not list `<dir>` in its
  `git add` step: git stops on the missing pathspec and adds nothing more,
  so the commit holds only the renames. Use `git add -A <new> <other files>`.
  spec-lint P11 flags this.
- Take a new ADR's number from `origin/main`
  (`git ls-tree --name-only origin/main knowledge/decisions/`), not local
  `main`. Renumbering after the spec gate changes the spec hash and forces
  a full re-gate.
