# Vault

A personal knowledge vault, made by claude-kit's `/vault-init`. Raw material
goes in, Claude turns it into linked wiki pages, and every session can read
them. Open this folder as a vault in Obsidian to browse it.

## Folders

- `raw/`: the originals, never edited. `web/` for saved pages, `transcripts/`
  for call transcripts, `docs/` for documents (`.md`, `.txt`, `.docx`),
  `notes/` for your own notes.
- `wiki/index.md`: the front door, listing every page.
- `wiki/people/`: one page per person.
- `wiki/topics/`: one page per project, organization, client or subject.
- `wiki/sources/`: one page per ingested raw file.
- `wiki/_templates/`: the page templates (Obsidian's Templates folder).
- `tasks/`: one file per task, mostly action items from calls.
- `vault.toml`: the profile, the registries and the folders git ignores.

## Adding material

Drop a file into `raw/<kind>/`, for example `raw/transcripts/` for a call
transcript you saved by hand.

## Ingesting

Ask Claude to run the `claude-kit:ingest` skill. It finds new and changed raw
files, writes their source pages, updates the person and topic pages, creates
tasks from action items and updates `wiki/index.md`. It does not commit; review
the changes and commit them yourself.

## Turning a task into a prompt

Ask Claude to run the `claude-kit:task-prompt` skill with a task. It reads the
task, its topic, owner and source pages, and writes a ready-to-run prompt.
