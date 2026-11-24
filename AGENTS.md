# Workspace conventions (Desktop/Github)

This file plays two roles: the workspace rules for every repo,
kept in `plugin/rules.md` so they ship with the plugin and imported below, and
project memory for the kit itself (last section).

@plugin/rules.md

## Developing the kit (this repo)

```
pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"   # once per machine
pytest                                                   # full suite
pytest tests/test_render_spec.py::test_title_from_h1     # one test
ruff check plugin tests; ruff format --check plugin tests
```

Hook edits (`plugin/hooks/`) need a new session or `/reload-plugins`; `SKILL.md`
and command edits are live (the plugin is loaded in place through a junction or
symlink, ADR 0005). Never run `plugin/install.py` (or its wrapper
`plugin/install.ps1`) from a test without a temporary `--skills-dir`
(`-SkillsDir`).

Vibe runs a copy of the plugin, so to try an edit in Vibe rerun
`python plugin/install.py --agent vibe` (then /reload-plugins or a new session).

- This repo is public. Never write the names of private repos or a machine's
  username into tracked files; refer to them generically ("a project repo") and
  use `%USERPROFILE%` or `<repo-root>` in paths. Grep the diff for them before
  committing.
- When a new behaviour should recur (say, at the end of each session), first
  fold it into an existing flow step, such as `/ship`'s clean-up; propose
  session-end automation only as an alternative.

Known gotchas (pytest output, worktree guard, line endings, gates):
[knowledge/kit-dev-gotchas.md](knowledge/kit-dev-gotchas.md).
