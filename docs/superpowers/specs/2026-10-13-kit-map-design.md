# Kit map: make the kit's playbooks and ADRs reachable from child repos

- **Status:** approved
- **Date:** 2026-10-13

## Purpose

The workspace `CLAUDE.md` links to `conventions/...` and `knowledge/decisions/...`
with paths relative to the kit root. Claude Code loads that file in a child repo
(a parent-folder `CLAUDE.md`), but in a child session those relative paths name
`<child>/conventions/`, which does not exist. The six playbooks that define how
we work are therefore not reliably reachable from the repos they govern.

Two places already patch this ad hoc: the spec-gate rubric falls back to
`../conventions/decision-log.md`, and the lean-context hook text names
`conventions/session-hygiene.md` with no root.

This change adds one SessionStart hook that injects a short "kit map": the kit
root's absolute path, a rule that the workspace `CLAUDE.md`'s relative links
resolve against it, and the absolute path of each playbook and of the kit's ADR
folder. Claude reads a playbook only when it needs one; nothing large is loaded
into every session. Because the plugin is installed per user, the map is present
in every repo, wherever the repo is cloned.

## Scope

**In:**
- `plugin/hooks/kit_map_inject.py` (new): the SessionStart hook.
- `plugin/hooks/hooks.json`: register it under `SessionStart`.
- `tests/test_kit_map_inject.py` (new): tests in Testing.
- `plugin/hooks/lean_context_inject.py`: the rule's "Details:" pointer names the
  playbook by name instead of the bare relative path.
- `plugin/skills/lean-context/SKILL.md`: the same pointer change.
- `plugin/skills/spec-gate/rubric.md`: check 8's third fallback
  (the workspace decision log one level up) becomes the decision-log path
  given in the reviewer's dispatch prompt.
- `plugin/skills/spec-gate/SKILL.md`: the discovery-round dispatch prompt
  carries that path (see Ad-hoc pointers).
- `tests/test_spec_gate_skill.py`: the check-8 assertion on the old fallback
  string is replaced, and the dispatch-prompt line is asserted (see Testing).
- `conventions/session-hygiene.md`: one sentence appended to principle 3
  ("Keep the main context for what the work needs") under `## Principles`,
  saying the kit map is injected and how to switch it off.
- `CLAUDE.md`: one sentence under "How we work" saying that in a child repo the
  kit map gives these files' absolute paths.
- `knowledge/decisions/0032-kit-map-inject.md` (new): the ADR.
- `knowledge/decisions/README.md`: an index row for 0032, and 0027's row
  status becomes "accepted; amended by 0032".
- `knowledge/decisions/0027-adr-triggers.md`: Status becomes
  "accepted; amended by 0032", because its decision names the
  one-level-up decision-log fallback this change replaces.
- `README.md`: the hook count goes from eight to nine, and the hook list gains
  "inject the kit map unless `CLAUDE_KIT_KIT_MAP=0`".
- `plugin/.claude-plugin/plugin.json`: version 0.22.0 becomes 0.23.0, and the
  description gains "a kit map injected at session start".
- `tests/test_plugin_manifest.py`: the version test follows the bump, and a
  description test is added (see Testing).

**Out:**
- Importing the playbooks into context (`@` imports): about 8k tokens per session.
- Copying the playbooks into child repos at scaffold time: drifts.
- Injecting the workspace `CLAUDE.md` rules themselves for repos cloned outside
  the kit folder, and the teammate setup (install docs, cross-platform installer,
  memory rules moved into versioned files): the separate "team setup" spec.
- Auto-memory being stored per project path: Claude Code behaviour.
- Adding a Read allow rule for the kit to user settings: the user declined it;
  an occasional permission prompt is accepted.

## Design

### The hook

`plugin/hooks/kit_map_inject.py`, shaped like `lean_context_inject.py`:

1. **Switch.** On by default. `CLAUDE_KIT_KIT_MAP=0` turns it off and nothing
   is printed; any other value, or none, counts as on.
2. **Kit root.** `Path(__file__).resolve().parents[2]`. `resolve()` follows the
   `~/.claude/skills/claude-kit` junction (or symlink) to the real `plugin/`
   folder, whose parent is the kit root. The root is valid only if
   `<root>/conventions/README.md` exists; otherwise the hook prints nothing.
3. **Playbooks.** Parse the table under `## The playbooks` in
   `conventions/README.md`; other rows are skipped silently. Each row whose
   first cell is a Markdown link to a `.md` file gives one playbook, named by
   the link text exactly as written. Only rows whose file
   exists under `conventions/` are listed. Zero rows still prints the map
   without a playbook list.
4. **Output.** One JSON object, as the other SessionStart hooks print, with
   `hookSpecificOutput.hookEventName` `SessionStart` and `additionalContext`:

   ```
   Kit map (claude-kit). Kit root: <root>. Relative links in the workspace
   CLAUDE.md (e.g. conventions/, knowledge/, plugin/) resolve against the kit root,
   not the current repo. Playbooks (read the one a task needs):
   - Knowledge layer: <root>/conventions/knowledge-layer.md
   - ... one line per playbook ...
   Kit ADRs: <root>/knowledge/decisions/
   ```

   Paths are written with forward slashes (`Path.as_posix()`). The ADR line is
   omitted if that folder does not exist.
5. **Registration.** A new `SessionStart` group with no matcher, so the map
   is injected on every source (startup, resume, clear, compact), placed
   directly after the `lean_context_inject.py` group.
6. **Never fails.** Any exception is reported on stderr as
   `[claude-kit] kit-map inject error: ...`; the hook always exits 0 (ADR 0007).

### Ad-hoc pointers

- `lean_context_inject.py` RULE ends `Details: the session-hygiene playbook (path in the kit map).`
- In `lean-context/SKILL.md`, the sentence that names
  `conventions/session-hygiene.md` "in the kit" says the same.
- `spec-gate/rubric.md` check 8 reads the section from the decisions README,
  else `conventions/decision-log.md` in the repository, else the decision-log
  path given in the dispatch prompt (skipped when that says `none`). The
  kit-repo note stays.
- The reviewer subagent gets no SessionStart output, so the main session
  passes the path. `spec-gate/SKILL.md` step 2's dispatch prompt gains one
  sentence: "The kit's decision-log playbook is at `<path>`." where `<path>` is
  the decision-log playbook's absolute path from the kit map in the main
  session's context, or `none` when no kit map is present. Verification
  rounds do not run check 8 and their prompt is unchanged.

### ADR 0032

Context: relative links in the workspace `CLAUDE.md` break in child repos.
Decision: a SessionStart hook injects a kit map of absolute paths; playbooks are
read on demand. Alternatives rejected: `@` imports (token cost every session,
still tied to folder layout), copying into children (drift, unadopted repos), a
Read allow rule (declined; prompts accepted). The spec-gate reviewer receives the decision-log path in its dispatch prompt in
place of the `../conventions/` fallback; this amends ADR 0027. With the map switched off, the
lean-context pointer names the playbook without a path; that is accepted.
Consequence: one more always-on
SessionStart injection of about 250 to 400 tokens, switchable with `CLAUDE_KIT_KIT_MAP=0`.

## Decisions

- **Inject a map, not the content.** The user chose the injected map over `@`
  imports and copying (2026-10-13).
- **No settings change for read access.** The user declined a Read allow rule;
  a permission prompt when Claude opens a kit file from a child is accepted.
- **On by default with an env switch,** matching the lean-context hook.
- **The playbook list comes from `conventions/README.md`,** so adding a playbook
  needs no hook change.
- **A missing kit root prints nothing,** so a plugin-only install stays silent
  instead of injecting broken paths.

## Testing

In `tests/test_kit_map_inject.py`, using `helpers.run_script` and `clean_env`:
- **On by default:** with no env, and with `CLAUDE_KIT_KIT_MAP=1`, exit 0 and the
  output's `additionalContext` contains the kit root (as posix) and, for every
  playbook row in the real `conventions/README.md`, its absolute path; each of
  those paths exists.
- **Off:** `CLAUDE_KIT_KIT_MAP=0` gives exit 0 and empty stdout.
- **Missing conventions:** copy the hook into a temp tree
  `<tmp>/kit/plugin/hooks/` with no `<tmp>/kit/conventions/`; running it gives
  exit 0 and empty stdout.
- **Through a link:** create `<tmp>/link` pointing at the real `plugin/` folder
  (on Windows a junction via `subprocess.run(["cmd", "/c", "mklink", "/J",
  link, target])`, elsewhere `os.symlink`; skip if the command exits non-zero
  or raises `OSError`) and run `<tmp>/link/hooks/kit_map_inject.py`; the
  injected kit root is the real kit root. Teardown removes only the link
  itself (`os.rmdir` for the junction, `os.unlink` for the symlink), never a
  recursive delete, which would follow the link into the real `plugin/`.
- **Size:** `additionalContext` is at most 1,500 characters.
- **Registered:** `hooks.json` has a `SessionStart` command containing
  `hooks/kit_map_inject.py`.

In `tests/test_spec_gate_skill.py`:
- `test_rubric_checks_adr_triggers`: the `"../conventions/decision-log.md"`
  entry is replaced by `"decision-log path given in the dispatch prompt"`.
- A new test asserts that `SKILL.md` step 2's prompt contains
  `The kit's decision-log playbook is at`.

In `tests/test_plugin_manifest.py`:
- `test_version_is_0_22_0` becomes `test_version_is_0_23_0`, asserting
  `"0.23.0"`.
- A new test asserts the description contains `kit map`.

Existing tests in `tests/test_lean_context_inject.py` keep passing (they check
for `claude-kit:lean-context`, which the RULE keeps).

## Success criteria

1. `pytest tests/test_kit_map_inject.py` passes with the tests above.
2. `pytest`, `ruff check plugin tests` and `ruff format --check plugin tests`
   pass on the kit's CI.
3. **Manual live check:** after `/reload-plugins` or a new session started in
   a child repo under the kit folder (any repo other than the kit), the session context contains the kit map, and asking
   Claude to read the decision-log playbook opens the absolute path from the
   map.
4. `git grep -n "\.\./conventions" plugin` returns no match.
