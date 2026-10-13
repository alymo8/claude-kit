# Team setup: a teammate on any OS works the way the kit's owner does

- **Status:** approved
- **Date:** 2026-10-13

## Purpose

The kit's owner now develops with a teammate, who should follow the same
process: the same skills, hooks, workspace rules and `/ship` flow, in any
repo, on any OS, and who may also send PRs to the kit itself. Today four gaps
stop that:

1. **Windows-only install.** `plugin/install.ps1` creates a junction; there is
   no installer for macOS or Linux.
2. **Undocumented dependencies.** The kit's flow relies on the `superpowers`
   plugin (brainstorming, writing-plans, worktrees, TDD, verification), on
   `git`, `gh`, and on a `python` command of 3.11 or later that every hook in
   `hooks.json` runs. None of this is written down or checked. On macOS and
   many Linux machines only `python3` exists, so every hook would fail.
3. **Rules tied to the folder layout.** Claude Code loads the workspace
   `CLAUDE.md` only for repos inside the kit checkout. A teammate who clones
   project repos elsewhere gets the plugin and the kit map (ADR 0032) but
   none of the workspace rules.
4. **Rules that live only in the owner's memory.** Three process rules exist
   only, or only partly, in the owner's auto-memory, which a teammate never
   sees.

This change adds a cross-platform Python installer with prerequisite checks,
a SessionStart hook that injects the workspace rules in repos outside the
kit folder, a setup guide, and moves the three rules into `CLAUDE.md`.

## Scope

**In:**
- `plugin/install.py` (new): the cross-platform installer (see Installer).
- `plugin/install.ps1`: becomes a thin wrapper that runs `install.py` with
  the same parameters.
- `tests/test_install.py`: rewritten to test `install.py` on every OS, plus
  a Windows-only wrapper smoke test (see Testing).
- `plugin/hooks/workspace_rules_inject.py` (new): the SessionStart hook
  (see Workspace rules hook).
- `plugin/hooks/hooks.json`: register it under `SessionStart`.
- `tests/test_workspace_rules_inject.py` (new): tests in Testing.
- `docs/setup.md` (new): the setup guide (see Setup guide).
- `tests/test_docs.py`: setup-guide tests (see Testing).
- `README.md`: the install sentence points to `docs/setup.md` and names
  `plugin/install.py` for every OS, and the execution-policy note moves to
  `docs/setup.md`; the hook count goes from nine to ten and
  the hook list gains "inject the workspace rules in repos outside the kit
  folder unless `CLAUDE_KIT_WORKSPACE_RULES=0`".
- `CLAUDE.md`: three rules (see Rules moved from memory) and the
  "Developing the kit" section's mention of `plugin/install.ps1` also names
  `plugin/install.py`.
- `knowledge/decisions/0033-cross-platform-installer.md` (new): amends
  ADR 0005.
- `knowledge/decisions/0034-workspace-rules-inject.md` (new).
- `knowledge/decisions/0035-process-rules-in-claude-md.md` (new).
- `knowledge/decisions/README.md`: index rows for 0033, 0034 and 0035; 0005's row
  status becomes "accepted; amended by 0033" (its title is unchanged).
- `knowledge/decisions/0005-kit-is-a-skills-dir-plugin.md`: Status becomes
  "accepted; amended by 0033".
- `plugin/.claude-plugin/plugin.json`: version 0.23.0 becomes 0.24.0; the
  description gains "a cross-platform installer" and "workspace rules
  injected in repos outside the kit folder".
- `tests/test_plugin_manifest.py`: the version test follows the bump, and a
  description test is added.

**Out:**
- Publishing the kit as a plugin marketplace (ADR 0005 stands: a linked
  checkout, updated with `git pull`).
- Installing `superpowers` automatically: the installer only checks and
  tells the user the command.
- Changing the `python` command in `hooks.json` (for example a `python3`
  fallback): the installer checks for `python` and explains the fix instead.
- Syncing anyone's personal settings, env switches or auto-memory.
- Branch protection or required PR approval: `/ship` keeps its autonomous
  squash-merge (the owner's choice, 2026-10-13).
- A macOS CI job: the Ubuntu job covers the symlink path.
- The owner's personal memories about other projects: they stay in
  memory.

## Design

### Installer

`plugin/install.py`, standard library only, run as
`python plugin/install.py` (or `python3`, whatever runs Python 3.11+):

1. **Arguments.** `--skills-dir` (default `~/.claude/skills`),
   `--settings` (default `~/.claude/settings.json`), and `--python`
   (default `python`: the command the hooks run, overridable so tests can
   name a missing one).
2. **Prerequisites first, before any change on disk.**
   - **Hard requirement:** the `--python` command is found on PATH
     (`shutil.which`) and running it with `-c` reports version 3.11 or
     later. Otherwise print `ERROR: hooks run "<python>", which <is not on
     PATH | is <version>>.`, where `<python>` is the `--python` value
     (default `python`) and a non-zero exit of `<python> -c` counts as not
     on PATH, followed by the fix for the current OS
     (Windows: install Python 3.11+ from python.org with "Add to PATH";
     macOS: Homebrew `python@3` and add its `libexec/bin` to PATH, or a
     `python` alias to `python3`; Linux: the `python-is-python3` package or
     a `python` symlink to `python3`), and exit 1 with nothing changed.
   - **Warnings:** `git` or `gh` missing from PATH prints
     `WARNING: <tool> not found on PATH; /ship and the worktree flow need it.`
     The run continues.
3. **Link.** `<skills-dir>/claude-kit` points at the real `plugin/` folder
   (the installer's own folder, resolved). On Windows a junction
   (`cmd /c mklink /J`), elsewhere a symlink (`os.symlink`, directory
   target). The skills dir is created if missing. Behaviour matches today's
   `install.ps1`, except that the error says "link" instead of "junction":
   - The link exists and resolves to `plugin/`: print
     `claude-kit already installed: <link> -> <target>`, leave the link
     unchanged and continue to step 4.
   - Anything else at that path (a folder, a file, a link elsewhere, a
     dangling link): print `ERROR: <link> already exists and is not a link
     to <target>. Remove it first.` and exit 1.
   - Otherwise create it and print `Installed: <link> -> <target>`.
4. **Status line.** Run `scripts/install-statusline.py --settings
   <settings> --skills-dir <skills-dir>` with `sys.executable` (today
   `install.ps1` uses `python`); a failure there prints a WARNING and does not
   change the exit code.
5. **Superpowers check.** Read the settings file; if `enabledPlugins` does
   not map `superpowers@claude-plugins-official` to `true` (or the file is
   missing or malformed), print:
   `WARNING: the superpowers plugin is not enabled. The kit's flow uses its
   skills. In Claude Code run: /plugin install superpowers@claude-plugins-official`.
   Exit code unchanged.
6. **End.** Print `Start a new Claude Code session (or run /reload-plugins)
   to load the kit.` after a fresh install; exit 0.

`plugin/install.ps1` keeps its `-SkillsDir` and `-Settings` parameters and
its comment-based help, and runs
`python "$PSScriptRoot\install.py" --skills-dir $SkillsDir --settings $Settings`,
exiting with that process's exit code. If `python` cannot be started it
prints `ERROR: python not found on PATH; install Python 3.11+.` and exits 1.

### Workspace rules hook

`plugin/hooks/workspace_rules_inject.py`, shaped like `kit_map_inject.py`:

1. **Switch.** On by default; `CLAUDE_KIT_WORKSPACE_RULES=0` turns it off
   and nothing is printed.
2. **Kit root.** `Path(__file__).resolve().parents[2]`, valid only if
   `<root>/CLAUDE.md` exists; otherwise print nothing.
3. **Project dir.** `CLAUDE_PROJECT_DIR` if set, else the `cwd` field of the
   hook's stdin JSON, else `os.getcwd()`; resolved. Print nothing when
   either holds, because the session then loads a kit `CLAUDE.md` natively:
   - the project dir is the kit root or inside it;
   - the project dir is in a git worktree of the kit placed elsewhere:
     `git -C <project dir> rev-parse --git-common-dir`, resolved against the
     project dir, is `<root>/.git`. If git is missing or the command fails,
     this check is false.
   Paths are compared with `os.path.normcase` after `resolve()`.
4. **Content.** The text of `<root>/CLAUDE.md` up to, not including, the
   first line starting with `## Developing the kit` (all of it if there is
   no such line), stripped.
5. **Output.** One JSON object with `hookSpecificOutput.hookEventName`
   `SessionStart` and `additionalContext`:

   ```
   Workspace rules (claude-kit, from <root>/CLAUDE.md). This repo is outside
   the kit folder, so Claude Code did not load them; follow them as you would
   a CLAUDE.md. Relative links resolve against <root>.

   <content>
   ```

   with `<root>` as posix.
6. **Registration.** A new `SessionStart` group with no matcher, placed
   directly after the `kit_map_inject.py` group.
7. **Never fails.** Any exception goes to stderr as
   `[claude-kit] workspace-rules inject error: ...`; exit 0 (ADR 0007).

### Rules moved from memory

In `CLAUDE.md`:
- Under "Building a new feature", the paragraph that starts **A feature is
  not finished until its workspace is gone**, gains: "Clean-up never deletes
  a repository and never suggests deleting one; the repo's owner does that."
- Under "Developing the kit", two bullets:
  - "This repo is public. Never write the names of private repos or a
    machine's username into tracked files; refer to them generically ('a
    project repo') and use `%USERPROFILE%` or `<repo-root>` in paths. Grep
    the diff for them before committing."
  - "When a new behaviour should recur (say, at the end of each session),
    first fold it into an existing flow step, such as `/ship`'s clean-up;
    propose session-end automation only as an alternative."

**After merge (outside the repo):** delete the owner's memory files
`no-suggest-repo-deletion.md`, `claude-kit-public-no-private-names.md` and
`fold-into-existing-flow-steps.md` and their `MEMORY.md` lines, and update
`kit-map-and-team-setup.md` to record this spec as shipped.

### Setup guide

`docs/setup.md`, sections in this order:
1. **Prerequisites:** Claude Code; the `superpowers` plugin (with its
   install command); `git`; `gh`, signed in; Python 3.11+ reachable as
   `python`, with the per-OS fix from the installer.
2. **Install:** clone the kit (`git clone` with this repository's public
   GitHub URL, which may name its owner/name slug), then `python plugin/install.py` (Windows can
   also run `plugin\install.ps1`, with the execution-policy note, moved
   from the README); what it does; start a new session. Update with `git pull`;
   hook edits need a new session or `/reload-plugins`.
3. **Where project repos live:** inside the kit checkout (the workspace
   `CLAUDE.md` loads natively) or anywhere else (the workspace-rules hook
   injects it).
4. **Switches:** a table of every `CLAUDE_KIT_*` environment variable read
   under `plugin/`, its default and effect, set under `env` in
   `~/.claude/settings.json`.
5. **How changes ship:** a pointer to the README's flow and to `/ship`,
   `/ship-fast`; a plain statement that `/ship` squash-merges its PR
   without waiting for a human approval.
6. **Contributing to the kit:** dev dependencies and commands (as in
   `CLAUDE.md`'s "Developing the kit"), feature branches and PRs (ADR 0006),
   and the public-repo naming rule.

### ADRs

- **0033 Cross-platform Python installer.** Context: the junction installer
  is Windows-only and checks nothing. Decision: `install.py` (junction on
  Windows, symlink elsewhere) with a hard `python` 3.11+ check and warnings
  for `git`, `gh` and superpowers; `install.ps1` wraps it. Alternatives: a
  parallel `install.sh` (two implementations), marketplace install (rejected
  in 0005), a `python3` fallback in `hooks.json`, installing superpowers
  automatically. Amends 0005's "created by `plugin/install.ps1`".
- **0034 Workspace rules injected outside the kit folder.** Context: repos
  outside the checkout never load the workspace `CLAUDE.md`. Decision: a
  SessionStart hook injects it, minus "Developing the kit", only outside the
  kit root; on by default, `CLAUDE_KIT_WORKSPACE_RULES=0` to switch off.
  Alternatives: an `@` import in `~/.claude/CLAUDE.md` (loads twice inside
  the tree, includes kit-dev rules, edits a personal file); requiring the
  kit-folder layout. Consequence: about 2k to 2.5k tokens (under 12,000
  characters) per session in those repos only; the rules arrive as hook context rather than as a
  CLAUDE.md.
- **0035 Process rules move from personal memory into `CLAUDE.md`.**
  Context: three rules (no repo deletion at clean-up, the public-repo
  naming rule with a grep before commit, folding recurring behaviour into an
  existing flow step) lived only, or only partly, in the owner's auto-memory,
  which a teammate never sees. Decision: they become workspace rules in
  `CLAUDE.md` (the last two under "Developing the kit"). Alternative: leave
  them personal. Consequence: every contributor follows them; the owner's
  memory copies are removed after merge.

## Decisions

All confirmed by the owner on 2026-10-13:
- **One spec, one PR, for all four gaps.** The gate asked whether to split
  the installer from the workspace-rules hook; the owner answered by
  shipping this spec whole with `/ship` (2026-10-13). The teammate's setup
  ships complete in one release (0.24.0), though the pieces are separable.
- **The teammate uses and contributes,** so contributor rules are in scope.
- **One Python installer, `install.ps1` as a wrapper.**
- **Superpowers: check and instruct,** never install.
- **Workspace rules: a SessionStart hook,** active only outside the kit root.
- **Move three memory rules** (no repo deletion, public-repo naming, fold
  into flow steps) into `CLAUDE.md`.
- **`python` is a hard installer check;** `hooks.json` is unchanged.
- **`/ship` keeps auto-merge** without PR approval.

## Testing

`tests/test_install.py` (runs on every OS; calls `install.py` with
`sys.executable`, `--skills-dir` and `--settings` under `tmp_path`, and
`--python` set to `sys.executable` unless a test says otherwise):
- **Fresh install:** exit 0; `<skills>/claude-kit/.claude-plugin/plugin.json`
  exists; `Path(link).resolve()` is the real `plugin/` folder.
- **Idempotent:** a second run exits 0 and prints `already installed`.
- **Conflicting folder:** a plain folder at the link path gives exit 1 and
  `ERROR`, and the folder is untouched.
- **Dangling link:** a link to a deleted temp folder gives exit 1 cleanly.
- **Status line:** the settings file gains a `statusLine` entry;
  malformed settings JSON still gives exit 0.
- **Superpowers:** settings without it print the `/plugin install` warning
  and exit 0; settings with
  `"enabledPlugins": {"superpowers@claude-plugins-official": true}` print no
  such warning.
- **Missing python:** `--python` naming a command that does not exist gives
  exit 1, an `ERROR` naming it, and no link created.
- **Wrapper (Windows only):** `install.ps1 -SkillsDir ... -Settings ...`
  exits 0 and creates the link.
- Teardown removes links only with `os.rmdir`/`os.unlink`, never a recursive
  delete through a link.

`tests/test_workspace_rules_inject.py` (`helpers.run_script`, `clean_env`):
- **Outside the kit:** `CLAUDE_PROJECT_DIR=<tmp_path>` gives exit 0 and
  `additionalContext` containing `Workspace rules` and the `## How we work`
  heading, and not `## Developing the kit`.
- **Inside the kit:** `CLAUDE_PROJECT_DIR` set to the kit root, and to a
  folder under it, gives empty stdout.
- **Kit worktree elsewhere:** in a temp kit (`<tmp>/kit` with a
  `CLAUDE.md`, the hook copied to `<tmp>/kit/plugin/hooks/`, `git init` and
  one commit), `git worktree add <tmp>/wt` and run the copied hook with
  `CLAUDE_PROJECT_DIR=<tmp>/wt`: empty stdout. The same hook with
  `CLAUDE_PROJECT_DIR` set to an unrelated temp folder injects.
- **From stdin:** with `CLAUDE_PROJECT_DIR` unset, stdin
  `{"cwd": "<tmp_path>"}` injects.
- **Off:** `CLAUDE_KIT_WORKSPACE_RULES=0` gives empty stdout.
- **No CLAUDE.md:** the hook copied into `<tmp>/kit/plugin/hooks/` with no
  `<tmp>/kit/CLAUDE.md` gives exit 0, empty stdout.
- **Size:** `additionalContext` is at most 12,000 characters.
- **Registered:** `hooks.json` has a `SessionStart` command containing
  `hooks/workspace_rules_inject.py`, after the kit-map one.

`tests/test_docs.py`:
- `docs/setup.md` exists and `README.md` links to it.
- Every `CLAUDE_KIT_[A-Z_]+` name found in files under `plugin/` appears in
  `docs/setup.md`.
- `docs/setup.md` mentions `superpowers@claude-plugins-official` and
  `install.py`.
- `CLAUDE.md` contains the three moved rules (by a key phrase each:
  `never suggests deleting`, `Never write the names of private repos`,
  `fold it into an existing flow step`).

`tests/test_plugin_manifest.py`: `test_version_is_0_24_0` asserts
`"0.24.0"`; a new test asserts the description contains
`cross-platform installer`.

## Success criteria

1. All the tests above pass, and `pytest`, `ruff check plugin tests` and
   `ruff format --check plugin tests` pass on CI for Ubuntu and Windows.
2. The public-repo rule holds: each private repo name from
   `gh repo list --visibility private --limit 500 --json name -q '.[].name'`,
   and the machine's username (`$env:USERNAME` or `$USER`), is grepped as a
   fixed, case-insensitive string against the added lines of
   `git diff origin/main...HEAD`, with zero hits. Before grepping, every
   occurrence of the kit's own public `owner/name` slug (from
   `gh repo view --json nameWithOwner -q .nameWithOwner`) is removed from
   those lines, because the public repo may name itself. The names are read
   at run time and never written into a tracked file.
3. **Manual live check on the owner's machine:** re-running
   `python plugin/install.py` prints `already installed` and exits 0 with no
   superpowers warning; after `/reload-plugins`, a session in a repo outside
   the kit folder has the workspace rules in context, and a session in a
   repo under the kit folder does not get them twice.
