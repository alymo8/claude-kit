---
title: Review standards
status: stable
last_updated: 2026-11-23
sources: []
---

Read by the standards reviewer of `claude-kit:review`, not by implementers.

## Rules

- When a change starts running an existing parser on every file in a batch
  path, check that its `except` covers every error the parser raises on
  damaged input (for `zipfile`: `zlib.error`, `NotImplementedError`,
  `RuntimeError`, `EOFError`); one bad file must not stop the batch.
- A scanner of untrusted text must decode what the model's reader decodes
  (UTF-16 and UTF-32 byte-order marks), or report the file as unscanned.
- Code that masks secrets in commands or URLs must cover more than
  `NAME=value`: `Authorization:`-style header values, PowerShell
  `$env:NAME = value` (with spaces), URL userinfo and query values. Any form
  it leaves clear (a bare `--token x`, a webhook URL path) is named as a
  limit in the spec or ADR.
- A POSIX process-tree kill must not treat the group leader's exit as the
  group's: after `SIGTERM` to the group, poll `os.killpg(pgid, 0)` (reaping
  the leader) until the grace ends, then `SIGKILL` the group. A child that
  starts its own session also needs `SIGTERM`/`SIGHUP` handlers in the
  parent, or it outlives a killed parent.
- A hook that joins several pieces of context guards each piece on its own
  (try/except per piece, an `[agent-kit]` note on stderr): one unreadable
  file must not silence every other piece through the outer catch-all.
- Code that rewrites a managed block inside a user's file refuses (exit 1,
  nothing written) when the begin/end markers are unpaired or repeated;
  cutting between mismatched markers deletes the user's own text.
- An early-exit check (an error path that returns before later steps) must
  not come before a step the spec says runs "in every case"; move the
  check after that step or into the step that needs it.
- A new skill step that reads or edits the root `CLAUDE.md` also handles a
  `CLAUDE.md` that is only `@AGENTS.md` (read and edit the `AGENTS.md`
  beside it); a fallback listed under another step does not cover it.
- A value written into a user's TOML file goes in as a basic string
  (`json.dumps(value)`), never a `'...'` literal: a path with `'` in it
  breaks the file.
