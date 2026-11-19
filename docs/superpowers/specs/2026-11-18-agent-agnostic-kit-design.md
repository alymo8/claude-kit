# Agent-agnostic kit: run the kit in Mistral Vibe, Codex and Cursor

- **Status:** approved
- **Date:** 2026-11-18

## Purpose

The kit only works in Claude Code. The rules, kit map, vault pointer and
handoff reach the model through Claude hooks, the skills load from a Claude
skills-dir link, and the flow assumes the superpowers Claude plugin. The user
is adding Mistral Vibe (definitely) and possibly Cursor and Codex. Opening any
project repo in one of those agents should give the same workspace rules, kit
map, vault access, skills and gates. Claude's behaviour must not change, and
the kit must stay publishable as a Claude plugin.

All three agents now share the same building blocks (checked against their
docs on 2026-11-18):

| | Mistral Vibe | Codex | Cursor |
|---|---|---|---|
| Instruction file | `AGENTS.md`: `~/.vibe/AGENTS.md`, then every `AGENTS.md` from the working directory up to the trusted folder root | `AGENTS.md`: `~/.codex/AGENTS.md`, then from the git root down to the working directory | `AGENTS.md` at the project root and in subfolders; no user-level file |
| Skills (`SKILL.md`, frontmatter `name` + `description`) | `~/.vibe/skills/`, `~/.agents/skills/`, `.vibe/skills/`, `.agents/skills/`, `skill_paths` | `~/.agents/skills/`, `.agents/skills/` from the working directory up to the repo root; follows symlinks | `~/.agents/skills/`, `~/.cursor/skills/`, `.agents/skills/`, `.cursor/skills/`; `name` must equal the folder name |
| Hooks | `~/.vibe/hooks.toml` and `.vibe/hooks.toml`: `[[hooks]]` with `name`, `type`, `command`, `match`; types include `session_start`, `post_agent`; JSON event on stdin; context returned as `hook_specific_output.additional_context` | `~/.codex/hooks.json` and `.codex/hooks.json`: Claude-shaped (`SessionStart`, `Stop`, matcher groups); context as `hookSpecificOutput.additionalContext` or plain stdout; on by default; user must trust hooks once with `/hooks` | `~/.cursor/hooks.json` and `.cursor/hooks.json`: `{"version": 1, "hooks": {"sessionStart": [...], "stop": [...]}}`; context as `additional_context`; `sessionStart` is fire-and-forget |

`~/.agents/skills/` is read by all three, so it is the one skills target for
non-Claude agents.

## Scope

**In:**
- `AGENTS.md` (new): the workspace rules, moved verbatim from `CLAUDE.md`
  (Design: Instructions).
- `CLAUDE.md`: becomes the one line `@AGENTS.md`.
- `plugin/hooks/workspace_rules_inject.py`: reads the rules from `AGENTS.md`
  when the kit root has one, else `CLAUDE.md`; header names the file read.
- `plugin/hooks/run.py` (new): the cross-agent hook runner (Design: Hook
  runner).
- `plugin/references/agent-tools.md` (new): how Claude-specific wording maps
  onto other agents (Design: Tool mapping).
- `plugin/install.py`: `--agent {claude,vibe,codex,cursor}` (Design:
  Installer).
- `plugin/install.ps1`: gains `-Agent` (default `claude`), passed through as
  `--agent`. When `-Agent` is not `claude`, it passes `--skills-dir` and
  `--settings` only if the user gave `-SkillsDir` or `-Settings`
  explicitly, so `install.py`'s per-agent default (`~/.agents/skills/`)
  applies and nothing lands in `~/.claude/skills`. It also gains `-Home`,
  forwarded as `--home`. `test_install.py` runs the wrapper with
  `-Agent vibe -Home <tmp_path>`, with `HOME` and `USERPROFILE` also set to
  `tmp_path` in the subprocess environment, when PowerShell is on `PATH`
  (skipped otherwise), and asserts that every file it writes is under
  `tmp_path` and that `<tmp_path>/.claude/skills` is untouched. This keeps
  the rule that tests never run the installer against the real home.
- `plugin/agent-skills/<name>/SKILL.md` (new, generated, committed): one
  wrapper skill per portable command (Design: Command wrappers).
- `plugin/scripts/agent-skills.py` (new): generates the wrappers; `--check`
  fails when a committed wrapper is out of date.
- `vendor/superpowers/` (new): pinned copy of the superpowers skills the kit
  uses, with `LICENSE` and `VERSION` (Design: Superpowers bundle).
- `plugin/scripts/vendor-superpowers.py` (new): refreshes that copy from a
  local superpowers checkout or plugin cache.
- `tests/test_run_hooks.py` (new), `tests/test_agent_skills.py` (new),
  `tests/test_vendor_superpowers.py` (new), `tests/test_install.py`,
  `tests/test_workspace_rules_inject.py`: cover the above.
- `tests/test_docs.py`, `tests/test_ship_many_command.py`,
  `tests/test_spec_gate_skill.py` and any other test that reads the kit's
  `CLAUDE.md` text: those assertions read `AGENTS.md` instead, and
  `test_docs.py` adds one assertion that `CLAUDE.md` is exactly
  `@AGENTS.md`.
- `plugin/skills/capture-learnings/SKILL.md` (body only, frontmatter
  unchanged): where it writes to the repo's root `CLAUDE.md`, it writes to
  `AGENTS.md` instead when `CLAUDE.md` is only `@AGENTS.md` (D11);
  `tests/test_capture_learnings_skill.py` asserts the rule.
- `knowledge/decisions/0034-workspace-rules-inject.md` and
  `knowledge/decisions/0035-process-rules-in-claude-md.md` and
  their index rows: marked "amended by" the new ADR.
- `knowledge/decisions/<NNNN>-agent-agnostic-kit.md` (new): the ADR, numbered
  one above the highest number in `knowledge/decisions/` on `origin/main` at
  implementation time, with its index row in `knowledge/decisions/README.md`.
- `docs/setup.md`: a "Using the kit with Vibe, Codex or Cursor" section.
- `README.md`: one paragraph naming the supported agents and pointing at
  `docs/setup.md`.
- `plugin/.claude-plugin/plugin.json`: minor version bump, one above the
  version on `origin/main` at implementation time;
  `tests/test_plugin_manifest.py` follows it.
- `docs/superpowers/README.md`: index rows for this spec and its plan
  (regenerated by `spec-index.py`).

**Out:**
- `/ship-many`, the statusline, `token-report.py`, `audit --user`,
  `context_nudge.py`, `handoff_snapshot.py`, `precompact_keep.py` and
  `on_spec_edit.py`. They read Claude transcripts, Claude config or start
  `claude` processes; they stay Claude-only (D6).
- Editing kit skill or command text for other agents. The tool mapping does
  that job, so Claude reads exactly the text it reads today (D3).
- Project repos' instruction files. Existing repos keep `CLAUDE.md` and the
  hook runner bridges them (D5). Defining "the instruction file" for project
  repos, moving the project template and `scaffold.py` to `AGENTS.md`, and
  teaching `adopt-conventions` and the audit rules about it is a later spec
  (D8); `capture-learnings` gets only the stub rule here (D11).
- Claude auto-memory (`~/.claude/projects/.../memory`). It stays Claude-only.
- Project-level agent config (`.vibe/`, `.codex/`, `.cursor/` inside repos).
  Everything installs at user level, like the Claude install.
- MCP server config for other agents.

## Design

### Instructions

The kit root's `CLAUDE.md` content moves verbatim to `AGENTS.md`, and
`CLAUDE.md` becomes the single line `@AGENTS.md`. Claude Code expands the
import, so Claude sees the same text. Vibe loads `AGENTS.md` natively for
repos under a trusted kit folder; Codex and Cursor do not walk above a child
repo's git root, so child repos get the rules from the hook runner, the same
way Claude gets them today.

`workspace_rules_inject.py` keeps its behaviour; only its source changes:
`rules()` reads `AGENTS.md` when it exists at the kit root, else `CLAUDE.md`,
and the header says which file. `kit_root()` still recognises the root by
`CLAUDE.md`, which stays as the stub.

### Hook runner

`plugin/hooks/run.py --agent {vibe,codex,cursor} --event {SessionStart,Stop}`.
Standard library only, Python 3.11, `sys.stdout.reconfigure(encoding="utf-8")`,
always exits 0 and prints errors to stderr with the `[claude-kit]` prefix
(ADR 0007).

1. Reads `plugin/hooks/hooks.json`, the one list of hooks. It runs every
   command registered for the event, in file order, except those in the
   Claude-only set `{context_nudge.py, handoff_snapshot.py,
   precompact_keep.py, on_spec_edit.py}`. A command's `${CLAUDE_PLUGIN_ROOT}`
   expands to the real `plugin/` folder and `${CLAUDE_PROJECT_DIR}` to the
   project directory.
2. Normalises the agent's stdin event into the Claude shape the scripts
   already read: `cwd` (from the event's `cwd`, else the current directory),
   `source` (Vibe and Codex pass theirs through; Cursor, which sends none,
   gets `startup`), `hook_event_name`. A group's `matcher` (such as
   `startup|clear` on `handoff_inject.py`) is applied to `source` as a regex.
   Each script runs with that JSON on stdin, `CLAUDE_PROJECT_DIR` set to the
   project directory, `CLAUDE_KIT_AGENT` set to the agent name, and a
   10-second timeout.
3. Collects each script's stdout. A JSON object with
   `hookSpecificOutput.additionalContext` contributes that string; any other
   non-empty stdout contributes its text.
4. For non-Claude agents, two extra pieces come first: the text of
   `plugin/references/agent-tools.md`, and the project's own `CLAUDE.md`
   when the project has no `AGENTS.md` (one level of `@path` import lines
   expanded) (D5). When `CLAUDE_KIT_AGENT` is set (any non-Claude agent),
   `workspace_rules_inject.py` also injects the rules for child repos inside
   the kit folder. Codex and Cursor never load an instruction file above a
   repo's git root, and Vibe loads the kit's `AGENTS.md` only when the user
   trusted the kit folder rather than just the child repo, which nothing
   ensures; a duplicate copy in a trusted-kit Vibe session is the accepted
   cost (D9). Unset, it behaves as today. The kit repo itself and kit
   worktrees stay silent for every agent, since they carry `AGENTS.md`.
5. Joins the pieces with blank lines and prints the agent's format:
   Vibe `{"hook_specific_output": {"additional_context": T}}`, Codex
   `{"hookSpecificOutput": {"hookEventName": E, "additionalContext": T}}`,
   Cursor `{"additional_context": T}`. Nothing collected prints nothing.

Claude keeps its own `hooks.json` unchanged and never calls `run.py`.

### Tool mapping

`plugin/references/agent-tools.md` tells a non-Claude agent how to read the
kit's Claude wording, in the style of superpowers' own per-agent reference
files:

- `superpowers:<name>` and `claude-kit:<name>` mean the skill `<name>`.
- "Dispatch a subagent" / the Agent tool: use the agent's subagent feature
  when it has one (Vibe documents subagents); with none,
  do the step inline as a separate pass that rereads its inputs from disk
  and does not rely on the conversation.
- AskUserQuestion and the app's wrap-up box: ask in chat.
- TodoWrite / the task list: the agent's own plan or todo feature, or a
  short checklist in chat.
- Slash commands such as `/ship`: the wrapper skill of the same name.
- `${CLAUDE_PLUGIN_ROOT}`: the absolute `plugin/` path. The committed file
  writes it as `<plugin>`; `run.py` replaces `<plugin>` with the real
  absolute path when it injects the file. The mapping also says that every
  `~/.claude/skills/claude-kit` path in any kit command, skill or reference
  (for example spec-gate's linter fallback) means that same `plugin/` path.
- The Claude Code built-in `code-review` skill (named by `ship-fast.md`):
  run the bundled `requesting-code-review` skill on the branch diff, then
  fix the findings it reports. It is the only Claude built-in skill a kit
  command names today.
- Claude-only features (D6) are named, with "not available in this agent".

### Superpowers bundle

`vendor/superpowers/skills/<name>/` holds the skills the kit references:
systematic-debugging, subagent-driven-development,
finishing-a-development-branch, executing-plans, brainstorming,
writing-plans, using-git-worktrees, test-driven-development,
receiving-code-review, requesting-code-review,
verification-before-completion, plus every skill those reference as
`superpowers:<name>`. `vendor/superpowers/LICENSE` is the upstream MIT
licence; `vendor/superpowers/VERSION` holds the upstream version and source.

`vendor-superpowers.py --from <dir>` computes that set from the
`superpowers:<name>` references in `plugin/**/*.md`, `AGENTS.md` and
`conventions/*.md` (nothing under `docs/`) and their closure inside the
upstream skills, copies those skill folders whole (files unchanged) and
rewrites `VERSION`. `test_vendor_superpowers.py` scans the same files and
checks that the bundle holds the computed set, without writing to the repo. The folder
sits outside `plugin/skills/`, so Claude plugin users never get duplicates.

### Command wrappers

`agent-skills.py` writes one `plugin/agent-skills/<name>/SKILL.md` per
command in `plugin/commands/` except `ship-many`. Frontmatter: `name` equals
the folder name (the command name), `description` comes from the command's
frontmatter description, `disable-model-invocation: true`. Body: follow
`<plugin>/commands/<name>.md`, where `<plugin>` is the absolute `plugin/`
path stated in the injected tool mapping, passing the user's arguments and
reading the command through the tool mapping; steps that need a Claude-only
feature are reported as skipped. Wrappers hold no machine path, so the
committed files are what the installer links, unchanged. `--check` compares
the committed files with a fresh render and exits 1 on a difference.

### Installer

`install.py --agent claude` (the default) does exactly what it does today.
For `vibe`, `codex` and `cursor`:

1. **Skills.** In `~/.agents/skills/` (overridable with `--skills-dir`), one
   directory link per skill folder from `plugin/skills/`,
   `plugin/agent-skills/` and `vendor/superpowers/skills/`, using the
   existing `make_link` (junction on Windows, symlink elsewhere). An existing
   entry of the same name that is not a link into this kit is left alone and
   reported.
2. **Hooks.** Writes the kit's entries into the agent's user hook file,
   keeping every other entry and replacing earlier kit entries, so a rerun
   changes nothing:
   - Vibe `~/.vibe/hooks.toml`: `claude-kit-session-start`
     (`session_start`) and `claude-kit-stop` (`post_agent`, `match = "main"`).
   - Codex `~/.codex/hooks.json`: `SessionStart` and `Stop` groups.
   - Cursor `~/.cursor/hooks.json`: `sessionStart` and `stop`, `version: 1`.
   Each command is `<python> "<kit>/plugin/hooks/run.py" --agent <a> --event <E>`,
   with `<python>` from the existing `--python` option.
3. **Fallback line.** For Vibe and Codex, a marked block in the user
   `AGENTS.md` (`~/.vibe/AGENTS.md`, `~/.codex/AGENTS.md`): if the context
   has no "Kit map (claude-kit)" text, run
   `<python> "<kit>/plugin/hooks/run.py" --agent <a> --event SessionStart`
   and follow what it prints. Cursor has no user-level `AGENTS.md`, so the
   installer's report gives the same instruction for the user to paste into
   Cursor's user rules if the hook's context does not reach the model.
4. **Report.** Prints what was linked, written and skipped, then the agent's
   next step: Codex `/hooks` to trust the new hooks; Vibe and Cursor start a
   new session.

`--agent` paths come from `Path.home()`, so tests pass a temporary home with
`--home`.

## Decisions

- **D1. One source, adapted per agent** (approach B, chosen by the user).
  Rejected: a static `AGENTS.md` with no hooks outside Claude (loses the
  worktree audit, handoff and per-session context), and separate copies per
  agent (drift).
- **D2. `hooks.json` stays the one hook list.** The runner reads it, so a new
  hook reaches every agent without a second list. Rejected: a separate
  manifest that generates `hooks.json`, which would make a committed,
  generated file the thing Claude plugin users run.
- **D3. Map tools, don't rewrite skills.** One reference file explains
  Claude wording to other agents. Claude's skill text is untouched, so its
  behaviour cannot drift. Rejected: editing 19 skill and command files to
  add fallbacks.
- **D4. Bundle a pinned superpowers copy** (chosen by the user), only for
  non-Claude agents, outside `plugin/skills/`. Rejected: downloading at
  install time (network and outside code at install).
- **D5. Existing repos keep `CLAUDE.md`; the runner bridges them.**
  Rejected: migrating every project repo now (touches many repos for no
  Claude benefit).
- **D6. Claude-only features stay Claude-only** (`/ship-many`, statusline,
  token-report, `audit --user`, transcript and precompact hooks,
  `on_spec_edit`). In other agents `/ship` and `/ship-fast` run in one
  session with no headless child sessions, using subagents per the tool
  mapping (chosen by the user). The Stop-time `spec-index.py` keeps the
  specs index current without `on_spec_edit`.
- **D7. All three agents in this version** (chosen by the user). Codex is
  covered by tests now and checked live once installed.
- **D8. Project-repo instruction files are a separate spec.** The runner
  works for `CLAUDE.md`-only repos, so the cross-agent runtime does not
  depend on moving project repos to `AGENTS.md`; keeping them apart keeps
  this change reviewable and leaves the adopt-mode and writer rules to
  their own spec.
- **D9. Inject workspace rules for every non-Claude agent in child repos
  inside the kit folder.** Rejected: relying on Vibe's native load, which
  silently gives no rules when only the child repo is trusted.
- **D10. Nothing is frozen.** Every test this spec names is new or gains
  cases for new behaviour; the Claude-unchanged check (Success criteria 1)
  compares against `origin/main` itself, not a committed fixture.

- **D11. capture-learnings follows the stub.** A repo whose root `CLAUDE.md`
  is only `@AGENTS.md` gets its learnings in `AGENTS.md`, so the kit repo's
  own learnings reach every agent. The full project-repo rule (adopt mode,
  audit) stays in the D8 spec. Rejected: appending under the stub, which
  only Claude would see.

## Testing

- `test_run_hooks.py`: with a fake kit and project in `tmp_path`, each agent
  gets its output shape; Claude-only scripts never run; `handoff_inject`'s
  matcher honours `source`; Cursor's missing `source` becomes `startup`; a
  failing or slow script is skipped with a stderr line and exit 0; a project
  with only `CLAUDE.md` gets it injected, one with `AGENTS.md` does not;
  plain-text and JSON script outputs are both collected.
- `test_install.py`: for each agent, with `--home` and `--skills-dir` in
  `tmp_path`: links created; a foreign entry left alone; hook files written
  in the agent's format with other entries kept; a second run changes no
  byte; `--agent claude` output and files match today's.
- `test_agent_skills.py`: `agent-skills.py --check` passes on the committed
  wrappers; every wrapper's `name` equals its folder and matches
  `^[a-z0-9-]+$`; no wrapper for `ship-many`.
- `test_vendor_superpowers.py`: the bundle holds every skill the kit
  references and their closure; `LICENSE` and `VERSION` exist; no bundled
  skill folder shares a name with a kit skill or wrapper.
- `test_workspace_rules_inject.py`: rules come from `AGENTS.md` when present,
  and a fake kit with `AGENTS.md` plus a `@AGENTS.md` stub gives the same
  rules text as one whose `CLAUDE.md` holds that text; with
  `CLAUDE_KIT_AGENT` set to `vibe`, `codex` or `cursor` a child repo inside
  the kit folder gets the rules, unset it does not; the kit root and a kit
  worktree stay silent for every agent.
- `test_run_hooks.py` also asserts that the injected mapping has `<plugin>`
  replaced by the real path and states the `~/.claude/skills/claude-kit`
  and `code-review` rules.
- `test_agent_skills.py`: every folder the installer links (kit skills,
  wrappers, bundled superpowers) has a `SKILL.md` whose `name` equals the
  folder name and matches `^[a-z0-9-]+$` (Cursor's rule).

## Success criteria

1. **Claude context unchanged.** On this machine, with the same environment
   for both runs, capture the SessionStart output of every hook in
   `hooks.json` (run as Claude runs them, with `CLAUDE_KIT_AGENT` unset) plus
   the kit's `CLAUDE.md` with `@` imports expanded, once from an
   `origin/main` checkout and once from the feature branch, each for the kit
   repo and for a temporary git repo outside the kit folder. The captures go
   to a scratch directory outside the repo, never into tracked files. The two
   differ only in the workspace-rules header naming `AGENTS.md` and in the
   kit root path between the two checkouts. Check: the `diff` of the two
   captures, with the root path replaced by `<kit>`, summarised in the PR
   without machine paths; the permanent guard is the stub-equivalence case
   in `test_workspace_rules_inject.py`.
2. **Claude skills unchanged.** The skill list Claude loads from
   `plugin/skills/` has the same 15 names and descriptions. Check:
   `git diff origin/main -- plugin/skills/*/SKILL.md` shows no frontmatter
   change.
3. **Suite green.** `pytest` passes and `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean.
4. **Claude end to end.** One `/ship-fast` run in Claude on `ship-fast-toy`
   reaches its PR, and its parallel tasks or reviewers run as subagents
   (`/ship-fast` runs no gates; the spec gate on this spec exercises the
   gate skill). Check: the PR and the run's transcript.
5. **Vibe live.** After `python plugin/install.py --agent vibe`, a new Vibe
   session in a project repo outside the kit folder: the model can quote the
   kit map and a workspace rule, `/skills` (or Vibe's skill list) shows the
   kit skills, the bundled superpowers skills and the wrappers, and
   `spec-gate` runs on a sample spec to a gate record. Check: manual, with a
   transcript excerpt in the PR.
6. **Cursor live.** After `python plugin/install.py --agent cursor`, a new
   Cursor agent chat in the same repo: the model can quote the kit map, and
   `/` lists `spec-gate`. If Cursor's fire-and-forget `sessionStart` context
   does not reach the model, this criterion fails as stated and the PR
   records it, with the installer's paste-into-user-rules fallback tried and
   its result noted. Check: manual, excerpt in the PR.
7. **Codex.** `test_install.py` and `test_run_hooks.py` cover its files and
   output. A live check (kit map quoted, `/skills` lists the kit skills) runs
   once Codex is installed; the PR lists it as pending until then. Check:
   pytest now; manual later.
8. **Publishable plugin.** `plugin/` still contains `.claude-plugin/plugin.json`,
   `hooks/hooks.json`, `skills/` and `commands/`, and no file under
   `plugin/skills/` comes from `vendor/`. Check: `test_plugin_manifest.py`
   and `test_vendor_superpowers.py`.
