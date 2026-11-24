# Quote hook commands safely and harden the Vibe installer

- **Status:** approved
- **Date:** 2026-11-24

## Purpose

PR 73 (ADR 0054) made `python plugin/install.py --agent vibe` build native
Mistral Vibe plugins. Its final review found problems the approved spec
did not cover, and a frozen test kept the main one from being fixed there:

- The hook command quotes the python path only when it holds a space. A
  path with an apostrophe and no space (`C:/Users/O'Neil/.../python.exe`)
  gives a command no shell can split, so every kit hook fails, for Vibe,
  Codex and Cursor alike, and the `AGENTS.md` fallback line names a broken
  command.
- Five installer paths end in a traceback, a misleading message or a lost
  backup instead of a clear result.
- The `tests/test_publish.py` guards skip a new file until it is added
  (staged or committed), so a task's suite can pass before its commit and fail after
  the merge.

This change fixes all three without changing anything for the common setup:
a plain `python` command and paths without special characters produce
byte-identical hook commands.

Anti-goal: a fix that changes the hook commands people already run with
plain paths, or that leaves the installer printing "nothing changed" when
something did.

## Scope

**In:**

- `plugin/install.py`: `hook_command`, the python-path check, `install_vibe`, `remove_kit_links`.
- `plugin/vibe_plugin.py`: `runner_command`, `swap`, `build`.
- `plugin/.claude-plugin/plugin.json`: version 1.1.1.
- `docs/setup.md`: the link-messages sentence.
- `tests/test_install.py`, `tests/test_vibe_plugin.py`, `tests/test_plugin_manifest.py`, `tests/test_publish.py`.

**Out:**

- Which shell Vibe, Codex or Cursor use to run hooks on Windows (still
  undocumented; this change does not depend on it).
- A `--python` value with arguments (`py -3`): still quoted as one
  executable, as today.
- Non-BMP characters in the home path.
- A backslash python path (`C:\Python311\python.exe`) stays bare, as today;
  POSIX shells drop the backslashes, so use forward slashes.
- The runner path (checkout or home) is not checked for the characters
  design 2 refuses; it stays double-quoted as today.
- Claude Code's own `plugin/hooks/hooks.json` commands (they use
  `${CLAUDE_PLUGIN_ROOT}` and are not built by the installer).

## Design

1. **Quoting rule.** `hook_command` (`install.py`) and `runner_command`
   (`vibe_plugin.py`) share one rule and keep producing identical strings
   (the existing `test_vibe_runner_command_matches_hook_command` keeps
   pinning that): the python path is wrapped in double quotes when it
   contains any character outside letters and digits (any Unicode letter or
   digit, as `str.isalnum`) and `_ . / : \ -`;
   otherwise it is written bare. So `python`, `python3` and
   `C:/Python311/python.exe` and `C:/Users/José/python.exe` stay bare and
   unchanged, and a path with a
   space, `'`, `&`, `(`, `)`, `;` or any other character is quoted (the
   characters design 2 refuses never reach this rule).
   The runner path stays double-quoted as today.
2. **Refuse what quoting cannot protect.** A python path containing `"`,
   `$`, a backtick or `%` cannot be quoted portably: POSIX shells still
   expand `$` and backticks inside double quotes, and cmd.exe still expands
   `%`. `install.py --agent vibe|codex|cursor` (every install that
   writes a hook command) and `vibe_plugin.py --python` refuse it
   before writing anything, and before the existing python check: one
   `ERROR:` line naming the character, exit 1, nothing changed.
3. **Failed rollback keeps the backup.** In `vibe_plugin.swap`, when a
   restore rename (moving a `<name>.old` copy back) fails, the build does
   not delete the staging folder: `BuildError` says which plugins could not
   be restored and names the staging folder that holds their previous
   copy, and it does not say "nothing changed" (the installer prints the
   message as is, without its usual "; nothing changed." suffix for this
   case, and `vibe_plugin.py`'s own command line drops it too). When every
   restore succeeds, behaviour is as today (staging
   removed, "nothing changed").
   On the next build, before the stale staging folder is removed, each
   `<staging>/<name>.old` whose `<out>/<name>` is missing is moved back to
   `<out>/<name>` first, so the backup is never deleted by a rerun.
4. **Duplicate-skills warning.** In `install_vibe`, when a Codex or Cursor
   `hooks.json` keeps the old skill links:
   - "kit links" means links under this checkout's skill roots, the ones
     `remove_kit_links` would remove (not the same-named `Kept` links);
   - nothing is printed about kept links when `skills_dir` holds no kit
     links;
   - otherwise the existing "Vibe lists the kit's skills twice" warning
     names only the hook files that hold a kit hook command, and each
     `hooks.json` that cannot be read or parsed gets its own line instead:
     `Kept the kit's skill links: <path> cannot be read, so it may still use them.`
     (still counted as in use, as today).
5. **Write errors after the build.** If writing or deleting
   `~/.vibe/hooks.toml` or writing `~/.vibe/AGENTS.md` raises `OSError`
   after the plugins were swapped in, `install_vibe` prints what was done
   (the plugins installed) and what was not (the file and the error, with
   "remove the kit block from `<path>` by hand or rerun" for `hooks.toml`
   and "update the kit block in `<path>` by hand or rerun" for
   `AGENTS.md`), skips nothing else it can
   still do, and exits 1. No traceback.
6. **Link removal errors.** In `remove_kit_links`, an `OSError` from
   `remove_link` prints `Could not remove <name>: <error>` and removal
   continues with the next link; the install then exits 1.
7. **Docs.** `docs/setup.md`'s sentence "Links into a kit checkout you have
   since deleted are reported as `Skipped`" says it applies to Codex and
   Cursor, and adds that for Vibe a same-named link into another checkout
   is reported as `Kept <name>` and left in place.
8. **Guard tests.** `tracked()` in `tests/test_publish.py` lists
   `git ls-files` plus `git ls-files --others --exclude-standard`, so the
   guards also check new files that are not committed yet and not ignored.
9. **Version.** `plugin/.claude-plugin/plugin.json` becomes `1.1.1`; the
   `agent-kit` Vibe manifest follows it as today.

## Decisions

- **D1 (quoting rule):** quote only when the path holds a character
  outside the safe set (Unicode letters and digits, `_ . / : \ -`). Decided by the
  user. Rejected: always quoting, which changes every existing hook
  command and breaks if PowerShell is the hook shell (`"python" args` is a
  string expression there).
- **D2 (frozen test changes):** `tests/test_vibe_plugin.py`, frozen by the
  PR 73 plan, changes: `test_hooks_toml_survives_quote_in_python_path`
  asserts the command splits (`shlex.split`) into the python path and the
  runner path instead of starting with the bare path. Decided by the user.
- **D3 (version 1.1.1):** a patch bump, bug fixes only; no new ADR.
  Decided by the user.
- **D4 (refuse `"`, `$`, backtick, `%`):** a python path holding one of
  these stops the install with nothing changed. Builder's call: double
  quotes do not stop `$` and backtick expansion in POSIX shells or `%`
  expansion in cmd.exe, and no single quoting works in every shell.
- **D5 (restore before removing stale staging):** a rerun moves a
  surviving `.old` copy back before removing the staging folder. Builder's
  call: otherwise the backup kept by design 3 dies on the next run.
- **D6 (link errors exit 1):** removal continues past a failed link, then
  exits 1. Builder's call: the install did most of its work, but scripts
  should notice that duplicates remain.
- **D7 (nothing frozen):** no `- **Frozen:**` bullet; every test the
  criteria name gains or changes cases for this change. Builder's call.

## Success criteria

Agreed with the user before the build:

1. **Tests** (`pytest`, temp `--home`, never the real home):
   - `shlex.split(hook_command(p, ...))[0] == p` and the same for
     `runner_command`, for `p` in: `python`, `C:/Python311/python.exe`,
     `C:/Program Files/python.exe`, `C:/Users/O'Neil/python.exe`,
     `C:/a&b/python.exe`, `C:/py(3)/python.exe`,
     `C:/Users/José/python.exe`; `python`, `C:/Python311/python.exe` and
     `C:/Users/José/python.exe` produce exactly today's strings;
   - `test_hooks_toml_survives_quote_in_python_path` asserts the argv
     (D2), and the built `hooks.toml` parses;
   - a python path with `"`, `$`, a backtick or `%` makes
     `install.py --agent vibe`, `--agent codex` and `vibe_plugin.py --out`
     exit 1 with the refusal's `ERROR:` line and nothing changed;
   - a swap whose restore rename fails keeps the staging folder with the
     `.old` copy, and the error (from `install.py` and from
     `vibe_plugin.py --out`) names it without "nothing changed"; the
     next build moves the `.old` copy back before removing staging;
   - with kit links present, a Codex `hooks.json` holding a kit command
     prints the duplicate warning naming it, and an unreadable one prints
     the "cannot be read" line and is not named in the warning; with no kit
     links, neither line prints;
   - an `OSError` writing `hooks.toml` or `AGENTS.md` after the build exits 1
     with no traceback and says the plugins were installed;
   - a failing `remove_link` prints `Could not remove <name>`, the other
     links are still removed, and the install exits 1;
   - `tests/test_publish.py`'s guards flag an untracked, unignored file
     that breaks a guard (and ignore an ignored one);
   - `tests/test_plugin_manifest.py`: `test_version_is_1_1_0` is replaced by
     `test_version_is_1_1_1`, asserting `1.1.1`.
2. **Unchanged elsewhere:** the full suite passes, including
   `test_vibe_runner_command_matches_hook_command`,
   `test_agent_claude_matches_default` and the existing Codex and Cursor
   install cases; `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean.
3. **Live check on this machine:** after merging, rerun
   `python plugin/install.py --agent vibe` from the main checkout; it exits
   0, and a headless `vibe -p` in a child repo quotes the
   `Kit map (agent-kit)` line with `~/.vibe/plugins/agent-kit` as plugin
   root.
