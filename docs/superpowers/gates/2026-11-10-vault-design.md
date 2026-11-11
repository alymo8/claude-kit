# Gate: Vault: a personal knowledge vault the kit scaffolds, ingests into and points every session at

- **Spec:** docs/superpowers/specs/2026-11-10-vault-design.md
- **Spec SHA-256:** a8296c8b29dc0d963b20e99e0c13a5d7e9d3e9c5650b7d9e1bab59d912b0f29a
- **Verdict:** pass
- **Date:** 2026-11-10
- **Rounds:** 1 discovery + 1 verification

## Key decisions

- The tooling (template, scripts, skills, hook) lives in the kit, and the content lives in each vault; the kit holds no personal data
- One vault per machine, with personal and work profiles that differ only in defaults; no sharing or sectioning across vaults
- The work profile keeps `raw/` out of git; the personal profile ignores nothing
- One generic `topics/` registry with a free-text `kind` instead of `clients/`; extra registries live at `wiki/<name>/` and use `topic.md`
- Obsidian is the viewer and the Obsidian Web Clipper the clipper; no custom clipper, Kanban app or graph tooling
- Transcripts are saved by hand in v1; automatic call capture and remote-doc sync are out
- Supported raw formats: .md, .txt, .vtt, .html, .pdf read directly; .docx through a stdlib `vault-pending.py --extract`; others skipped and reported
- A new SessionStart hook injects `Vault (<profile>): <path>` in every repo whenever `CLAUDE_KIT_VAULT` is set, rather than extending the kit map
- Change detection uses sha256 in source-page frontmatter, with no separate log
- Ingest never commits and never edits `raw/`; the task-prompt skill changes no file
- `vault-init` creates a local git repo with one commit, and never creates a remote or pushes
- Creating the user's real vaults happens after merge, not in this PR
- Version bump to 0.28.0 and ADR 0040 recording these decisions

## Findings fixed

- round 1 [blocking] Re-run criterion asks for a clean git status, but ingest never commits: criterion 3 commits the first run's result before checking the re-run against a clean tree
- round 1 [blocking] README "ten hooks" test not in Scope: `tests/test_docs.py` added to Scope In (eleven hooks, CLAUDE_KIT_VAULT assertion)
- round 1 [blocking] Supported raw formats undefined: format list and `vault-pending.py --extract` for .docx added, with a test and a decision; fixtures named with formats and contents
- round 1 [minor] Tasks counted as a registry: knowledge-layer text says people, topics, sources under `wiki/` plus a `tasks/` folder
- round 1 [minor] Two template folders: `task.md` moved into `wiki/_templates/`; ingest skips `wiki/_templates/` when searching
- round 1 [minor] Hook says "Personal vault" on a work vault: line is now `Vault (<profile>): <path>`
- round 1 [minor] Name grep not checkable: criterion 6 greps for the username and private repo names; fixtures list their invented names
- round 1 [minor] tomllib rationale had no reader: `vault-pending.py` reads `vault.toml` and exits 2 if it does not parse

## Plan questions

- What git identity does the scaffold commit use when none is configured (fallback in the script, or tests set one and the script fails clearly)? (Design, /vault-init)
- Is the `raw/` walk recursive, and is a source page whose raw file is gone reported (for example `missing`) or ignored? (Design, vault-pending.py)
- Which date names a task file (call date or ingest date), and how is `topic` chosen when a call concerns several topics? (Design, Template tasks/ and ingest step 3)

## Open

- none
