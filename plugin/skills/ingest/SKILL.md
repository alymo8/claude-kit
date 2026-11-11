---
name: ingest
description: Use when the user asks to ingest or file material into the vault (a web page, call transcript, document or note dropped under raw/). Compiles each raw file into a source page and updates the person, topic and task pages it concerns, then reports what changed. Never commits.
---

# Ingest into the vault

Compile raw material into the vault's wiki. The vault's own `CLAUDE.md`
holds its rules; read it and `wiki/index.md` before writing.

The script is `vault-pending.py` in the plugin's scripts folder:
`python "${CLAUDE_PLUGIN_ROOT}/scripts/vault-pending.py" ...` (fallback
`~/.claude/skills/claude-kit/scripts/vault-pending.py`).

## 1. Find the vault

Use the current directory if it holds `vault.toml`, else the path in the
`CLAUDE_KIT_VAULT` environment variable. If neither, say so and stop.

## 2. List the work

Run `vault-pending.py <vault> --json`. It prints a list of `{path, status,
source, sha256}` entries, `status` being `new`, `changed` or `missing`, and
`sha256` the raw file's current hash (null for `missing`). If nothing is
pending, say so and stop. If the user named specific files, limit the work to
those.

`missing` entries (a source page whose raw file is gone) are listed in the
report and their pages left unchanged.

## 3. Per file

Read the file and decide its kind from its folder: `web` is `web`,
`transcripts` is `call`, `docs` is `doc`, `notes` is `note`; a file elsewhere
under `raw/` is a `doc`. Read `.md`, `.txt`, `.vtt`, `.html` and `.pdf`
directly; read `.docx` through
`vault-pending.py --extract <file>`. Any other format is skipped and listed
in the report as unsupported.

Then:

- **Source page.** Write or update `wiki/sources/<date>-<slug>.md` from
  `wiki/_templates/call.md` for a call, else `source.md`. Its `raw` is the
  vault-relative posix path and its `sha256` is copied from the `--json`
  entry; never hash a file yourself. Its `date`, and the file-name prefix, is
  the date the material states (call date, publication date, document date),
  else the ingest date.
- **People and topics.** For each person and topic the file materially
  concerns, update the existing page or create one from the template. Search
  page names and `aliases` in `wiki/people/`, `wiki/topics/` and any other
  registry listed in `vault.toml`, skipping `wiki/_templates/`, before
  creating. A listed extra registry is treated like `topics/` and uses
  `topic.md`. Add only facts the source states, each ending with a link to the
  source page; append a dated line to a person's Interaction log.
- **Tasks (calls).** Add each action item to the source page and create
  `tasks/<source page date>-<slug>.md` from `task.md` with `status: inbox`,
  `owner`, `topic`, `source` and `due`. `owner` and `topic` are quoted
  wiki-links (`owner: "[[Tobias Renn]]"`), empty when not stated. `topic` is
  the topic the action item is about, else the first of the call's `topics`,
  else empty. `due` is empty when not stated.
- **Frontmatter.** All wiki-links in frontmatter are quoted.
- **Index.** Add every new page to `wiki/index.md` under its registry, and
  every new task file under Tasks, as `- [[page]]: one-line summary`.

## 4. Changed files

A `changed` file updates its existing source page (the entry's `source`) and
the facts that came from it; do not create a second source page. Facts on
person and topic pages that link to that source page and that the new version
no longer states are removed, and each removal is listed in the report.

## 5. Report

One list of: pages created, pages updated, tasks created, facts removed,
conflicts noted (also under Open questions on the page), `missing` entries and
unsupported files. Do not commit; the user reviews the diff in git or
Obsidian.

## Rules

- Never edit `raw/`.
- Never invent people, owners, dates or facts; leave a field empty rather than guess.
- Do not commit; the user reviews the diff.
- One fact, one home: a person or topic page holds it; a source page holds only what that source said.
- Prefer updating a page to creating a near-duplicate.
- Keep page names human-readable (`Jane Doe.md`, `Project Atlas.md`) so
  Obsidian links read naturally.
- When sources conflict, a newer primary document beats a recap; note the
  conflict under Open questions.
