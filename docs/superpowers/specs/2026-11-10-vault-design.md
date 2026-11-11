# Vault: a personal knowledge vault the kit scaffolds, ingests into and points every session at

- **Status:** approved
- **Date:** 2026-11-10

## Purpose

The kit's knowledge layer (`conventions/knowledge-layer.md`) organizes what one
repository knows. Nothing organizes what the user knows across repositories and
outside code: the people they work with, the projects, organizations and
subjects they deal with, their calls, the pages and documents they read, and the
tasks that come out of all of it. Today that context is scattered over
auto-memory, remote docs and dozens of repo `knowledge/` folders.

This change adds a **vault**: a folder of plain Markdown (opened in Obsidian)
that follows the same principles as the knowledge layer, applied to a person
rather than a repo. Raw material is dropped into `raw/` and kept verbatim; an
`ingest` skill compiles it into one page per person, topic and source, linked
with `[[wiki-links]]` and reachable from one index (the "LLM wiki" pattern). A
`task-prompt` skill turns a task in the vault into a ready prompt with its
context. A SessionStart hook tells every session, in every repo, where the vault
is.

The kit ships the template and the tools, with no personal content. Each
machine has its own vault instance: the user will run one personal vault on this
machine and a separate work vault on a work laptop, so profiles adapt the
defaults and nothing is shared between instances.

## Scope

**In:**
- `plugin/templates/vault/` (new): the vault template (see Design, Template).
- `plugin/scripts/vault-init.py` (new): scaffolds a vault from the template.
- `plugin/scripts/vault-pending.py` (new): lists raw files not yet ingested,
  or changed since ingest.
- `plugin/commands/vault-init.md` (new): `/vault-init`, user-only.
- `plugin/skills/ingest/SKILL.md` (new): the ingest skill.
- `plugin/skills/task-prompt/SKILL.md` (new): the task-prompt skill.
- `plugin/hooks/vault_inject.py` (new): the SessionStart hook.
- `plugin/hooks/hooks.json`: register the hook under `SessionStart`, directly
  after the `workspace_rules_inject.py` group, with no matcher.
- `tests/test_vault_init.py` (new), `tests/test_vault_pending.py` (new),
  `tests/test_vault_inject.py` (new), `tests/test_vault_skills.py` (new):
  see Testing.
- `tests/fixtures/vault/` (new): three raw samples for the live check, all
  fictional. Every person and organization in them is invented and named in a
  header comment of each file. The people and topics each sample materially
  concerns (the pages ingest is expected to create) are listed in
  `tests/fixtures/vault/EXPECTED.md` (new), which is never copied into `raw/`:
  - `tests/fixtures/vault/web/atlas-launch-notes.md` (new): a clipped page.
  - `tests/fixtures/vault/transcripts/2026-11-03-atlas-sync.vtt` (new): a call
    with exactly three action items: one with an owner and a due date, one
    with an owner and no date, one with neither.
  - `tests/fixtures/vault/docs/atlas-brief.md` (new): a document.
- `tests/test_docs.py`: the `"ten hooks"` assertion becomes `"eleven hooks"`,
  and an assertion that the README names `CLAUDE_KIT_VAULT` is added.
- `conventions/knowledge-layer.md`: a `## Personal vault` section before
  `## Definition of done` (see Design, Docs).
- `docs/setup.md`: a `## Personal vault` section after `## Docker Desktop on
  Windows`, and a `CLAUDE_KIT_VAULT` row in the Switches table.
- `knowledge/decisions/0040-personal-vault.md` (new): the ADR.
- `knowledge/decisions/README.md`: an index row for 0040.
- `README.md`: the hook count goes from ten to eleven, the hook list gains
  "point every session at the vault when `CLAUDE_KIT_VAULT` is set", the
  skill list gains `ingest` and `task-prompt`, and the plugin paragraph that
  describes `/docker-compact` gains one sentence on `/vault-init`.
- `plugin/.claude-plugin/plugin.json`: version 0.27.1 becomes 0.28.0; the
  description gains "a personal vault (/vault-init, ingest and task-prompt
  skills, and a session-start pointer when CLAUDE_KIT_VAULT is set)".
- `tests/test_plugin_manifest.py`: `test_version_is_0_27_1` becomes
  `test_version_is_0_28_0`, and `test_description_mentions_vault` is added.

**Out:**
- Graphify or any knowledge graph: a later experiment inside a vault, kept
  only if it measurably beats index plus grep.
- A custom web clipper: the Obsidian Web Clipper, configured in setup docs.
- A Kanban web app: tasks are files; an Obsidian view over them is optional.
- Automatic call capture (Teams Graph API, bots, audio recording): v1 takes
  transcripts the user saves into `raw/transcripts/` by hand.
- Syncing remote documents (OneDrive, SharePoint, Claude Docs) into the vault.
- Changes to any other project repo.
- Global coding rules from the andrej-karpathy-skills CLAUDE.md: the kit's
  conventions already cover them.
- Creating the user's actual vaults: done after merge with `/vault-init`, not
  in this PR.
- Sharing one vault across machines, or personal and work sections in one
  vault: each machine has its own vault.

## Design

### Template

`plugin/templates/vault/` renders to:

```
<vault>/
  CLAUDE.md              # vault rules (below)
  README.md              # what the vault is, how to add material, how to ingest
  vault.toml             # profile, registries, folders git ignores
  .gitignore             # from vault.toml's git_ignore list
  raw/
    web/  transcripts/  docs/  notes/     # each with a .gitkeep
  wiki/
    index.md             # the front door
    people/  topics/  sources/            # each with a .gitkeep
    _templates/
      person.md  topic.md  source.md  call.md  task.md
  tasks/
    .gitkeep
  .obsidian/
    app.json             # useMarkdownLinks false, newLinkFormat shortest
    templates.json       # folder: wiki/_templates
```

Registries:

- **`people/`**: one page per person. Frontmatter `type: person`, `role`,
  `organization`, `topics: []`, `last_interaction`. Sections: Context, Open
  items, Interaction log (dated lines linking to `sources/` pages).
- **`topics/`**: one page per specific thing the user deals with: a project, an
  organization, a client, a subject, anything with its own identity.
  Frontmatter `type: topic`, `kind` (free text, for example `project`,
  `organization`, `subject`), `status`, `people: []`. Sections: Summary,
  Current state, Decisions, Open questions, Related sources.
- **`sources/`**: one page per ingested raw file, named
  `YYYY-MM-DD-<slug>.md`. Frontmatter `type: source`, `source_kind`
  (`web` | `call` | `doc` | `note`), `raw` (vault-relative path of the raw
  file), `sha256` (of the raw file's bytes at ingest), `date`, `people: []`,
  `topics: []`. Sections: Summary, Key facts, and for calls Decisions and
  Action items. Calls use `call.md`; other kinds use `source.md`.
- **`tasks/`** (a folder, not a registry in `vault.toml`): one file per task, `<YYYY-MM-DD>-<slug>.md`. Frontmatter
  `type: task`, `status` (`inbox` | `todo` | `doing` | `done`), `owner`,
  `topic`, `source` (a wiki-link to the source page), `due`. Sections:
  Description, Acceptance criteria, Notes.

`wiki/index.md` has one section per registry (People, Topics, Sources, Tasks)
listing pages as `- [[page]]: one-line summary`, plus a line saying it is the
first thing to read.

The vault `CLAUDE.md` says: read `wiki/index.md` first; each fact has one home
(a person or topic page), and source pages hold only what that source said;
every fact added to a person or topic page links to the source page it came
from; never invent people, owners, dates or facts, and leave a field empty
rather than guess; when sources conflict, a newer primary document beats a
recap, and the conflict is noted on the page under Open questions; `raw/` is
never edited; run the ingest skill to add material.

`vault.toml`:

```toml
profile = "personal"          # or "work"
registries = ["people", "topics", "sources"]
git_ignore = []               # work profile: ["raw/"]
```

Profiles differ only in defaults. `work` sets `git_ignore = ["raw/"]` so raw
call transcripts and documents stay out of git history; `personal` ignores
nothing. Both include `.obsidian/workspace*.json` in `.gitignore`. Extra
registries are added by listing a name in `registries` and creating
`wiki/<name>/`; ingest treats any listed registry like `topics/` and uses
`topic.md` for it. `vault-pending.py` reads `vault.toml` with `tomllib` and
fails with exit 2 if it does not parse. Page templates contain no `{{...}}`
placeholders (the kit's template tests forbid unknown ones); the title is the
file name.

### `/vault-init`

`plugin/scripts/vault-init.py PATH [--profile personal|work]` (default
`personal`):

1. Refuses (exit 1, message on stderr) if `PATH` exists and is not empty.
2. Copies the template, writes `vault.toml` with the profile's values, and
   writes `.gitignore` from `git_ignore` plus the Obsidian workspace lines.
3. Runs `git init -b main` and one commit, `Scaffold vault from claude-kit`.
4. Prints the vault path, and the next steps: set `CLAUDE_KIT_VAULT` to the
   path under `env` in `~/.claude/settings.json`, open the folder as a vault
   in Obsidian, and create the remote (`gh repo create --private`) as the
   user's own step.

Exit codes: 0 success, 1 refusal, 2 usage. Never creates a remote or pushes.

`plugin/commands/vault-init.md` (`disable-model-invocation: true`,
`argument-hint: <path> [personal|work]`): asks for the path if missing, runs
the script, shows its output verbatim, stops on a non-zero exit.

### `vault-pending.py`

`plugin/scripts/vault-pending.py VAULT [--json]` walks `VAULT/raw/`
(skipping `.gitkeep` and dotfiles), reads the `raw` and `sha256` frontmatter
of every `wiki/sources/*.md`, and prints one line per raw file that is
`new` (no source page names it) or `changed` (its sha256 differs), as
`<status>\t<vault-relative path>`, sorted by path. `--json` prints a list of
`{"path", "status", "source", "sha256"}` objects (`source` is the existing page's path
for `changed`, else null; `sha256` is the raw file's current hash, hex, of its
bytes). Exit 0, also when nothing is pending; exit 2 if
`VAULT` has no `vault.toml`.

`vault-pending.py --extract FILE` prints the plain text of a `.docx` file
(paragraphs from `word/document.xml`, one per line, standard library only:
`zipfile` and `xml.etree`), exit 1 with a message on a file that is not a
valid `.docx`. It is how the ingest skill reads Teams `.docx` transcripts and
Word documents. Frontmatter is read with a small parser for
`key: value` lines between `---` fences (no YAML dependency).

### The ingest skill

`plugin/skills/ingest/SKILL.md`. Invoked as `/claude-kit:ingest` or when the
user asks to ingest or file material into the vault. Steps:

1. **Find the vault**: the current directory if it holds `vault.toml`, else
   `CLAUDE_KIT_VAULT`; stop and say so if neither.
2. **List work**: run `vault-pending.py <vault> --json`. If nothing is
   pending, say so and stop. If the user named specific files, limit to those.
3. **Per file**, read it and decide its kind from its folder (`web`,
   `transcripts` → `call`, `docs`, `notes`; a file elsewhere under `raw/` is a
   `doc`). Supported formats: `.md`, `.txt`, `.vtt`, `.html` and `.pdf` are
   read directly; `.docx` through `vault-pending.py --extract`. Any other
   format is skipped and listed in the report as unsupported. Then:
   - write or update its `sources/` page from the matching template, with
     `raw` and the `sha256` value from `vault-pending.py --json` (the skill
     never hashes by itself);
   - for each person and topic it materially concerns, update the existing
     page (search `wiki/` by name and aliases first, skipping `wiki/_templates/`) or create one from the
     template; add only facts the source states, each ending with a link to
     the source page; append a dated line to a person's Interaction log;
   - for a call, add each action item to the source page and create a
     `tasks/` file with `status: inbox`, the stated owner (empty if none was
     stated), `topic`, `source` and `due` (empty if none was stated);
   - add every new page to `wiki/index.md` under its registry, and every new
     task file under Tasks.
4. **Changed files** update their existing source page and the facts that came
   from it, rather than creating a second source page.
5. **Report**: one list of pages created and pages updated, tasks created,
   and conflicts noted. Do not commit; the user reviews the diff in git or
   Obsidian.

Rules in the skill: never edit `raw/`; never invent; one fact, one home;
prefer updating a page to creating a near-duplicate; keep page names
human-readable (`Jane Doe.md`, `Project Atlas.md`) so Obsidian links read
naturally.

### The task-prompt skill

`plugin/skills/task-prompt/SKILL.md`. Invoked as `/claude-kit:task-prompt
<task>` (a task file name, path or title fragment). It finds the vault as
ingest does, resolves the task (asks the user to pick if several match),
reads the task file and every page it links to one hop away (its topic, its
source page, people named as owner or in the source), and prints one prompt
in a fenced block:

```
# Task: <title>
<description>
## Acceptance criteria
<from the task file; "none written" if empty>
## Context
<topic summary and current state; source page summary and decisions;
 owner and people context: a few lines each, each citing its vault page>
## Verification
Agree the success criteria above before building, verify against them,
and report the evidence.
```

It does not change any file.

### The vault hook

`plugin/hooks/vault_inject.py`, shaped like `lean_context_inject.py`:

1. Reads `CLAUDE_KIT_VAULT`. Unset or empty: prints nothing.
2. If the path has no `vault.toml`: prints nothing to stdout, and one line on
   stderr, `[claude-kit] CLAUDE_KIT_VAULT has no vault.toml: <path>`.
3. Otherwise prints one SessionStart JSON object whose `additionalContext` is:
   `Vault (<profile from vault.toml>): <path as posix>. Before answering questions about the
   user's work, people, projects or topics, read <path>/wiki/index.md and the
   pages it points to. To add material, use the claude-kit:ingest skill; to
   turn a vault task into a prompt, claude-kit:task-prompt.`
4. Any exception goes to stderr as `[claude-kit] vault inject error: ...`;
   always exits 0 (ADR 0007).

### Docs

- `conventions/knowledge-layer.md` `## Personal vault`: the same principles
  applied to a person; registries are people, topics and sources under `wiki/`, plus a `tasks/`
  folder; the
  vault lives outside any project repo, one per machine, scaffolded with
  `/vault-init`; repos link to vault pages only by name, never copy them.
- `docs/setup.md` `## Personal vault`: run `/vault-init <path> [profile]`; set
  `CLAUDE_KIT_VAULT`; install Obsidian and open the folder as a vault; install
  the Obsidian Web Clipper and set its save folder to `raw/web/`; save call
  transcripts (`.vtt`, `.docx` or text) into `raw/transcripts/`; then run the
  ingest skill. The work profile keeps `raw/` out of git; check the employer's
  policy on sending call content to an LLM before ingesting work calls.
- ADR 0040 records the Decisions below.

## Decisions

- **The tooling lives in the kit, the content in each vault.** The user chose
  the kit over vault-local skills (2026-11-10), so the skills are reusable by
  teammates and by the user's work vault. The kit stays free of personal data.
- **One vault per machine.** The user will keep a personal vault here and a
  work vault on a work laptop; there is no cross-vault sharing or sectioning.
  Profiles change only defaults.
- **A generic `topics/` registry, not `clients/`.** The user wants one
  registry for any specific thing (project, person-adjacent work, client,
  subject), with a free-text `kind`.
- **Obsidian is the viewer.** The user chose it (2026-11-10); it supplies the
  graph view, the web clipper and optional task views, so the kit builds none.
- **Transcripts by hand in v1.** The user confirmed ingest handles transcripts
  saved into `raw/transcripts/`; automatic capture is out.
- **The session pointer is on when `CLAUDE_KIT_VAULT` is set,** in every repo.
  The user chose it over vault-only.
- **No Graphify in v1.** Index plus wiki-links plus grep first; a graph is a
  later, measured experiment.
- **`vault.toml`, not YAML** (builder's call): `vault-pending.py` reads it with
  Python 3.11's `tomllib`, so no new dependency.
- **`.docx` read with the standard library** (builder's call): Teams exports
  transcripts as `.docx` or `.vtt`; `vault-pending.py --extract` avoids a
  converter dependency.
- **Change detection by sha256 in source-page frontmatter** (builder's call):
  no separate log file to drift, and `vault-pending.py` makes it testable.
- **Ingest does not commit** (builder's call): the user reviews the diff.
- **The work profile keeps `raw/` out of git** (builder's call, privacy):
  raw call transcripts and documents stay out of git history; the user checks
  the employer's policy before ingesting work calls.
- **A new hook rather than extending the kit map** (builder's call): the kit
  map prints nothing on a plugin-only install, and the vault pointer must not
  depend on that.

## Success criteria

1. `pytest` passes, including the new tests in Testing.
2. `ruff check plugin tests` and `ruff format --check plugin tests` pass.
3. **Live ingest check** (run by the implementer, transcript of the run in the
   PR): `vault-init.py` a throwaway vault in a temp folder; copy
   `tests/fixtures/vault/` samples (not `EXPECTED.md`) into its `raw/`; run the ingest skill. Then
   `vault-pending.py` prints nothing; each sample has a `sources/` page with
   matching `raw` and `sha256`; the people and topics `EXPECTED.md` lists for each
   sample have pages linking to those source pages; `wiki/index.md` lists every new page;
   the transcript produced one `tasks/` file per action item in it, each with
   a `source` link and an owner only where the transcript states one. Commit the
   first run's result in the vault (as the user would after review); running
   ingest again then reports nothing pending, and `git status` in the vault
   shows a clean tree.
4. **Live task-prompt check**: the task-prompt skill on one created task
   prints the prompt block with the task, its acceptance criteria, and context
   from its topic, source and owner pages, each cited.
5. **Hook check**: with `CLAUDE_KIT_VAULT` set to the throwaway vault, a new
   session's context shows the vault line; unset, it does not
   (covered by tests, and observed once in a live session).
6. `git diff main` grepped for the machine's username and for the names of
   the private repos under the workspace folder (listed with `ls`) finds no
   match, and the fixtures use only the invented names their header comments
   list.
7. **Manual check by the user**: the throwaway vault opens in Obsidian and its
   wiki-links resolve.

## Testing

- `tests/test_vault_init.py`: personal and work profiles each produce the
  template tree, a `vault.toml` with the profile's values, the expected
  `.gitignore` lines, a `main` branch with one commit; a non-empty
  destination exits 1 and writes nothing; a bad profile exits 2; no `{{`
  placeholder remains in any rendered file.
- `tests/test_vault_pending.py`: new, changed and up-to-date raw files are
  classified correctly; `.gitkeep` and dotfiles are skipped; output is sorted;
  `--json` shape, including each `sha256` equal to the file's hash; a folder with no `vault.toml` exits 2; `--extract` on a
  `.docx` built in the test with `zipfile` prints its paragraphs in order, and
  on a non-docx file exits 1.
- `tests/test_vault_inject.py`: unset and empty print nothing; a path with no
  `vault.toml` prints nothing to stdout and the stderr line; a valid vault
  prints the JSON with the path and both skill names; the hook exits 0 in
  every case.
- `tests/test_vault_skills.py`: both skills have frontmatter with `name` and
  `description`; the ingest skill names `vault-pending.py`, says never edit
  `raw/`, never invent, and do not commit; the task-prompt skill says it
  changes no file; `vault-init.md` is user-only.
- `tests/test_plugin_manifest.py`: the hook command references an existing
  script (existing test), version 0.28.0, description mentions the vault.
