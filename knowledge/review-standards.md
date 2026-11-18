---
title: Review standards
status: stable
last_updated: 2026-11-17
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
