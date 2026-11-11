# ADR 0040: A personal vault scaffolded and served by the kit

- **Status:** accepted
- **Date:** 2026-11-10

## Context
The user wants a personal knowledge base (people, topics, sources, tasks)
filled from web pages, documents and call transcripts, readable by Claude in
any session. A personal vault on one machine and a work vault on another must
both work, and the public kit must hold no personal data.

## Decision
- The tooling lives in the kit, the content in each vault.
- One vault per machine; profiles (`personal`, `work`) change only defaults.
- A generic `topics/` registry, not `clients/`, with a free-text `kind`.
- Obsidian is the viewer; the kit builds no UI.
- Transcripts are saved by hand into `raw/transcripts/` in v1.
- The session pointer is on when `CLAUDE_KIT_VAULT` is set, in every repo.
- No Graphify in v1: index, wiki-links and grep first.
- `vault.toml`, not YAML, read with `tomllib`.
- `.docx` is read with the standard library.
- Change detection is by sha256 in source-page frontmatter.
- Ingest does not commit; the user reviews the diff.
- The work profile keeps `raw/` out of git.
- A new hook carries the pointer rather than extending the kit map, which
  prints nothing on a plugin-only install.

## Consequences
- Teammates and a work vault reuse the same skills.
- The user reviews every ingest before it is committed.
- Raw work content stays out of git history; the employer's LLM policy is the
  user's to check.
- Automatic transcript capture and graph tooling are later work.
