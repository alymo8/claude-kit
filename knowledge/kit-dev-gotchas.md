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
- Appending to a CRLF file with a bash heredoc mixes line endings, and
  `ruff format --check` then flags the file. Run `ruff format <file>`.

## Worktree-isolated sessions (`/ship`, `parallel-tasks`)

- The isolation guard refuses Bash commands it cannot prove stay inside the
  session's worktree: shell variables in paths (`rm "$M/$f"`), heredocs
  feeding `python` that mention git, `$(...)` around a script, and chained
  git commands aimed at another worktree. Use literal absolute paths, one
  plain command per call, the Edit tool for file edits, and
  `git -C <worktree>` from subagents working in task worktrees.

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
  `pass-with-decisions` and `/ship` stops for a one-line OK. Answers that
  stay inside the spec's Scope In files pass; an answer that touches a
  file outside Scope In (a new test in another test file) is flagged.
  Keep answers inside Scope In to avoid the stop.
- Take a new ADR's number from `origin/main`
  (`git ls-tree --name-only origin/main knowledge/decisions/`), not local
  `main`. Renumbering after the spec gate changes the spec hash and forces
  a full re-gate.
