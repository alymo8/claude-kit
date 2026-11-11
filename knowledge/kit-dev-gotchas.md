# Gotchas when developing the kit

Things that cost time in past runs and are not obvious from the code.

## Tests and lint

- `pyproject.toml` already sets `addopts = "-q"`, so `pytest -q` runs at
  `-qq` and prints no summary line. Run plain `pytest` (or
  `pytest -o addopts=""`) when you need the pass count.
- Test code written in a plan is copied verbatim into `tests/`, so it must
  fit ruff's 88-character line limit; a longer line fails
  `ruff format --check plugin tests`. `ruff format` never splits a long
  string literal (E501 stays), so split it by hand in the plan.
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
  `${CLAUDE_PLUGIN_ROOT}/references/<file>.md`. The same file must give the
  `~/.claude/skills/claude-kit/references/<file>.md` fallback, or state it
  once with the `FALLBACK_RULE` line from `tests/test_skill_size.py`, or the
  pointer test fails.
- Writing test code through a bash heredoc into a Python script turns
  `\n` escapes inside string literals into real line breaks, so the
  test file no longer parses. Edit test files with the Edit tool.
- Before promising how much a command can shrink, read its tests:
  `tests/test_ship_command.py` and `tests/test_ship_fast_command.py` pin
  about 60 exact phrases, and one pins a line break
  (`"one\n   copy, the only one the run starts"` in step 5 of
  `ship-fast.md`), so rewrapping that sentence fails the test.
- Measure a tracked file's size with `git show HEAD:<path> | wc -c`, not
  `wc -c <path>`: the working copy is checked out with CRLF and reads a
  few hundred bytes larger than the stored LF file.
- Appending to a CRLF file with a bash heredoc mixes line endings, and
  `ruff format --check` then flags the file. Run `ruff format <file>`.

## Worktree-isolated sessions (`/ship`, `parallel-tasks`)

- The isolation guard refuses Bash commands it cannot prove stay inside the
  session's worktree: shell variables in paths (`rm "$M/$f"`), heredocs
  feeding `python` that mention git, `$(...)` around a script, and chained
  git commands aimed at another worktree. Use literal absolute paths, one
  plain command per call, the Edit tool for file edits, and
  `git -C <worktree>` from subagents working in task worktrees.
- A heredoc fed to `python` inside a longer command line is refused even
  when it does not mention git. Write the script to the scratchpad with
  the Write tool and run `python <scratchpad>/script.py <args>`.
- A feature worktree made with `git worktree add -b feat/<slug> <path>
  origin/main` tracks `origin/main`, so `handoff.py state` reports
  "upstream: origin/main". The first push must be
  `git push -u origin feat/<slug>`.

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
  command text, so each long command states once that
  `~/.claude/skills/claude-kit` stands in for it (`tests/test_skill_size.py`
  accepts that line or a per-pointer fallback).

## Scripts on Windows

- Python's stdout is cp1252 when piped on Windows, so printing a path
  with characters outside cp1252 raises `UnicodeEncodeError`. A script
  that prints filesystem paths calls `sys.stdout.reconfigure(encoding="utf-8")`
  first, as `docker-disk.py` does. Do not use `errors="replace"`: it turns
  non-ASCII into `?`, which hides it from callers that check for it.
- Docker Desktop's resource saver stops the `docker-desktop` distro when
  idle, so `docker-disk.py` prints `used ?` (it never starts the distro).
  To compare its numbers by hand, run `docker info` first to wake it.

## Hooks

- Claude Code injects at most 10,000 characters of a hook's
  `additionalContext`. Above that, only a preview reaches the session.
  Keep a size test with a margin (`workspace_rules_inject.py` is capped at
  9,500 and injects about 9,000 today).

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
- Take a new ADR's number from `origin/main`
  (`git ls-tree --name-only origin/main knowledge/decisions/`), not local
  `main`. Renumbering after the spec gate changes the spec hash and forces
  a full re-gate.
