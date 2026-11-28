# ADR 0055: The kit targets Anthropic's plugin directory, and /new-project defaults to a sibling folder

- **Status:** accepted
- **Date:** 2026-11-24
- **See:** [ADR 0058](0058-directory-lite-plugin.md) (the directory is submitted the generated lite plugin; this ADR still holds for plugin/)

## Context
[ADR 0052](0052-published-plugin.md) published the kit as the `agent-kit`
plugin through this repo's own marketplace, so only people who already know
the repo can install it. Anthropic's plugin directory is the one official
listing: one entry reaches claude.ai, Cowork and Claude Code. Submission
happens in a portal and needs the owner's paid plan, contact email and
compliance acknowledgements, so the agent cannot submit. Each submitted
version is scanned and may be held for review on anything the repo could
have fixed (an unclear hook, a missing README, a manifest gap).

Marketplace users have no kit checkout. With none, `scaffold.py` fell back
to the current folder, so `/new-project` run inside some other git repo
nested the new project in it. The Stop hook passed
`${CLAUDE_PROJECT_DIR}/docs/superpowers` to `spec-index.py`, the only hook
command that used a second variable.

## Decision
- **Checklist-clean repo, owner submits (D1).** The repo is made to pass the
  directory's pre-submission checklist, and `tests/test_directory_ready.py`
  runs that checklist on the tracked `plugin/` tree in CI: manifest fields,
  a valid name, file limits, no links or LFS pointers, a `plugin/README.md`
  that names every hook script, and a fixed pattern for hook commands.
  `docs/directory-submission.md` holds the portal steps; the owner submits.
  Rejected: a guide with no repo changes, which leaves the checklist to be
  re-checked by hand on every version.
- **Sibling default for `/new-project` (D2).** Inside a git repo that is not
  the kit, `/new-project` defaults to the folder holding that repo's main
  checkout, so the project lands beside it. A repo at a filesystem root has
  no such folder: the command exits 2 and asks for `--parent`. Rejected:
  stopping to ask for `--parent` every time, which fails the common case.
- **The Stop hook reads the project folder itself (D8).** The Stop command
  drops its `${CLAUDE_PROJECT_DIR}` argument; `spec-index.py` reads the
  variable and falls back to the current folder. Every hook command now has
  the same shape.

## Consequences
- Every version bump on `main` is scanned and reviewed again after listing.
- Once the kit is listed, the README Install section gains the directory
  route, as a separate change.
- `docs/directory-submission.md` holds the steps and the drafted listing and
  data-handling answers.
- The spec's sentence "hooks open no network connection" was not true: the
  SessionEnd hook runs `gh pr view` when the branch has an upstream and `gh`
  is installed. `plugin/README.md` discloses that call instead.
