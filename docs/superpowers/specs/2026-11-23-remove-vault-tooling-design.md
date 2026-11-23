# Remove the vault tooling that moved to second-brain-kit

- **Status:** approved
- **Date:** 2026-11-23

## Purpose

The personal-vault tooling (the `/vault-init` command, `vault-init.py`,
`vault-pending.py`, the `vault_inject.py` SessionStart hook, the `ingest` and
`task-prompt` skills and the vault template) now lives in a separate public
repo, second-brain-kit, installed as its own plugin. claude-kit still ships a
copy, so both plugins inject a vault pointer at session start and both offer
`ingest` and `task-prompt`. This change removes claude-kit's copy and every
live mention of it. The decision history stays in claude-kit, marked as moved.

second-brain-kit has no GitHub remote yet, so no file links to it by URL; text
names it as "the second-brain-kit plugin".

## Scope

**In (delete):**
- `plugin/commands/vault-init.md`
- `plugin/agent-skills/vault-init/` (the generated wrapper for that command;
  `plugin/scripts/agent-skills.py --check` must pass after the delete)
- `plugin/hooks/vault_inject.py` and its entry in `plugin/hooks/hooks.json`
- `plugin/scripts/vault-init.py`, `plugin/scripts/vault-pending.py`
- `plugin/skills/ingest/`, `plugin/skills/task-prompt/`
- `plugin/templates/vault/`
- `tests/test_vault_init.py`, `tests/test_vault_inject.py`,
  `tests/test_vault_pending.py`, `tests/test_vault_skills.py`
- `tests/fixtures/vault/`, `tests/fixtures/vault_scan/`

**In (edit):**
- `plugin/.claude-plugin/plugin.json`: drop the clause "and a personal vault
  (/vault-init, ingest and task-prompt skills, and a session-start pointer
  when CLAUDE_KIT_VAULT is set)" from `description`; bump `version` to
  `0.36.0`.
- `tests/test_plugin_manifest.py`: replace `test_description_mentions_vault`
  with `test_description_omits_vault`, asserting that `vault`, `ingest` and
  `task-prompt` are absent from the description; rename
  `test_version_is_0_35_0` to `test_version_is_0_36_0` and assert `0.36.0`.
- `tests/test_docs.py` (`test_setup_guide_names_prerequisites_and_installer`):
  `"twelve hooks"` becomes `"eleven hooks"`; the `CLAUDE_KIT_VAULT` assertion
  becomes `"CLAUDE_KIT_VAULT" not in readme`. A new test asserts the moved
  ADRs and the split ADR (below).
- `tests/test_run_hooks.py` (`test_real_hooks_json_commands`): the
  SessionStart count `7` becomes `6`.
- `README.md`: remove `ingest` and `task-prompt` from the skill list (line
  ~88), "twelve hooks" becomes "eleven hooks", remove the "point every session
  at the vault when `CLAUDE_KIT_VAULT` is set" clause (line ~101), and remove
  the two vault sentences on line ~140 (the `/vault-init` sentence and the
  "Raw files are treated as data" sentence).
- `docs/setup.md`: "handoff and vault pointer" becomes "and handoff" (line
  ~69); delete the `CLAUDE_KIT_VAULT` row of the Switches table; replace the
  whole "Personal vault" section (with its two subsections) by a two-line
  section: the vault tooling moved to the second-brain-kit plugin, see
  ADR 0051.
- `conventions/knowledge-layer.md`: the "Personal vault" section keeps its
  first two sentences (the principles apply to a person's knowledge) and the
  sentence "Repos link to vault pages only by name and never copy them." (a
  rule for repos, not tooling); the sentences on where the vault lives, how
  it is scaffolded and the `docs/setup.md`/ADR 0040 pointer become "The
  tooling for a personal vault is the second-brain-kit plugin (ADR 0051)."
- `plugin/skills/audit/user-mode.md:71`: "(web, inbox, vault ingest)" becomes
  "(web, inbox, notes ingest)". The check stays: it is about any scheduled
  task that reads untrusted content, and second-brain-kit's daily ingest is
  one.
- `knowledge/decisions/0040-personal-vault.md` and
  `0047-untrusted-vault-content.md`: status becomes `moved`, the date line
  gains "(moved 2026-11-23)", and a note under the header says the tooling
  moved to the second-brain-kit plugin per ADR 0051 and the record below is
  kept as history. The bodies stay unchanged. (Precedent: ADR 0012.)
- `knowledge/decisions/0051-vault-tooling-split.md` (new) and its row in
  `knowledge/decisions/README.md`; the 0040 and 0047 rows show `moved`.

**Out:**
- Historical specs, plans and gate records under `docs/superpowers/` and
  their index rows: they record what was built and stay as they are.
- `docs/audit/ideas-10-14.md`: a dated audit note whose "personal vault
  planning" mentions a transcript topic, not kit tooling.
- `plugin/hooks/kit_map_inject.py`: checked, it has no vault lines, so
  nothing to change or decide.
- second-brain-kit itself, and the user's scheduled tasks (already repointed).
- The user's auto-memory: updated by capture-learnings, outside this diff.

## Decisions

- **D1 (history stays, marked moved):** ADRs 0040 and 0047 keep their full
  bodies and get status `moved` plus a note. Decided by the user. Unlike
  ADR 0012, the body is not replaced, because second-brain-kit holds the
  code but the decision record is wanted here too. `moved` rather than
  `superseded by 0051`, as in ADR 0012, because the decision lives on in
  second-brain-kit rather than being reversed. `moved` is outside the
  decision-log template's status list; ADR 0012 already uses it, and this
  change does not edit the convention.
- **D2 (pointer text, no URL):** docs name "the second-brain-kit plugin" and
  ADR 0051; no URL until it has a remote.
- **D3 (historical docs untouched):** specs, plans and gate records are not
  edited or deleted (see Out).
- **D4 (version):** removing a command, two skills and a hook is a
  user-visible change; bump the minor version to `0.36.0`.
- **D5 (`CLAUDE_KIT_VAULT`):** claude-kit stops reading it. Whether
  second-brain-kit reads the same variable is that repo's business; claude-kit
  docs no longer mention it.
- **D6 (nothing frozen):** no evaluator is frozen. The change only deletes
  code and edits docs; the tests it touches are edited by this change itself
  to match the removal, so freezing them would block the work.

## Design: ADR 0051, the vault tooling lives in second-brain-kit

Template fields: Status `accepted`, Date 2026-11-23. Context: the vault
tooling is personal-knowledge tooling, not a workspace convention, and
grew (triage, connectors) beyond the kit's scope. Decision: it lives in the
separate public second-brain-kit plugin; claude-kit ships none of it; ADRs
0040 and 0047 stay in claude-kit marked `moved`; the knowledge-layer
convention keeps only the principle. Consequences: one vault pointer at
session start instead of two; installing claude-kit alone no longer gives a
vault; second-brain-kit must be installed separately.

## Success criteria

1. Every path under "In (delete)" is gone from the branch (verified:
   `git ls-files <path>` prints nothing for each).
2. `plugin/hooks/hooks.json` has eleven hook commands and none names
   `vault_inject`; `python plugin/scripts/agent-skills.py --check` exits 0.
3. `pytest` passes and `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean.
4. `git grep -n -i -E "vault|task-prompt|claude-kit:ingest"` over the branch,
   excluding `docs/superpowers/` and `docs/audit/`, lists only: the moved
   notes and bodies of ADRs 0040 and 0047, ADR 0051, their
   `knowledge/decisions/README.md` rows, the `## Personal vault` headings and
   pointer lines in `docs/setup.md` and `conventions/knowledge-layer.md`, the
   new `tests/test_docs.py` test on the moved and split ADRs, and the test
   assertions that vault text is absent.
5. Privacy: the diff contains no private repo name and no machine username
   (verified: `git diff main` grepped, case-insensitively, for the machine
   username, the last part of `%USERPROFILE%`, and for every repo name in the
   user's auto-memory index `MEMORY.md` that is not public, prints nothing).
6. A PR is open against `main` for the user to merge (verified: `gh pr view`
   shows it open).

## Verification

Run the commands in criteria 2 to 5 and paste their output into the PR's
test plan; check criterion 1 with `git ls-files` on each deleted path.
