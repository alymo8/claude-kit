# Gotchas when developing the kit

Things that cost time in past runs and are not obvious from the code.

## Tests and lint

- `pyproject.toml` already sets `addopts = "-q"`, so `pytest -q` runs at
  `-qq` and prints no summary line. Run plain `pytest` (or
  `pytest -o addopts=""`) when you need the pass count.
- Test code written in a plan is copied verbatim into `tests/`, so it must
  fit ruff's 88-character line limit; a longer line fails
  `ruff format --check plugin tests`.

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

## Gates

- Answering a spec gate's `## Plan questions` in the plan makes each answer
  a plan-introduced decision, so the plan gate returns
  `pass-with-decisions` and `/ship` stops for a one-line OK. Expect that
  stop whenever the spec gate record lists plan questions.
