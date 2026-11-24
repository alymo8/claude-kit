# Gate: Quote hook commands safely and harden the Vibe installer

- **Spec:** docs/superpowers/specs/2026-11-24-hook-quoting-design.md
- **Spec SHA-256:** 6e5dc5c84a5fde605ecb5bc7a08e7431de69642f93bd6d9d4bfecd7c280d3045
- **Verdict:** pass
- **Date:** 2026-11-24
- **Rounds:** 3 discovery + 0 verification

## Key decisions

- Quote the python path only when it holds a character outside Unicode letters and digits (`str.isalnum`) plus `_ . / : \ -`; plain paths stay byte-identical (Design 1, D1).
- Refuse python paths containing `"`, `$`, a backtick or `%` for every hook-writing install and for `vibe_plugin.py`, before the python check, with exit 1 and nothing changed (Design 2, D4).
- A failed restore keeps the staging folder and drops the "nothing changed" claim in both command lines; a rerun moves surviving `.old` copies back before removing staging (Design 3, D5).
- The duplicate-skills warning prints only when kit links exist; unreadable `hooks.json` files get their own line and still count as in use (Design 4).
- Post-build write errors and link-removal errors exit 1 with no traceback, after doing what still can be done (Design 5, Design 6, D6).
- The `tests/test_publish.py` guards also check untracked, unignored files (Design 8).
- Edit the PR 73 frozen test `test_hooks_toml_survives_quote_in_python_path` to assert the `shlex.split` argv (D2).
- Patch version 1.1.1, no new ADR; nothing frozen (D3, D7).
- Out of scope: the Windows hook shell, `--python` values with arguments, non-BMP home paths, backslash python paths, runner-path character checks, Claude Code's `hooks.json`.

## Findings fixed

- round 1 [blocking] Double quotes do not protect `$`, backtick or `%`: Design 2 and D4 now refuse them like `"`; the `/opt/py$1/python` criterion case became `C:/py(3)/python.exe` and the refusal criterion covers all four characters.
- round 1 [blocking] `vibe_plugin.py`'s own CLI after a failed rollback: Design 3 says it also drops "nothing changed"; the criterion checks both command lines.
- round 1 [minor] Guard-test gap overstated: Purpose says "until it is added (staged or committed)".
- round 1 [minor] Version test not named: criterion names `test_version_is_1_1_0` replaced by `test_version_is_1_1_1`.
- round 1 [plan-adjacent] Refusal ordering: Design 2 runs it before the existing python check and the criterion asserts the refusal's `ERROR:` line.
- round 2 [blocking] "Letters" ambiguous: Design 1 and D1 say any Unicode letter or digit (`str.isalnum`); `C:/Users/José/python.exe` added to the criteria as unchanged.
- round 2 [blocking] "Cannot be read" line condition: Design 4 defines kit links, prints nothing when there are none, and lists unreadable files on their own line instead of in the warning; the criterion covers both cases.
- round 2 [blocking] Warning text misquoted: now quotes the existing "Vibe lists the kit's skills twice".
- round 2 [minor] Backslash python path and runner-path characters: added to Out as unchanged.
- round 2 [minor] `AGENTS.md` failure message: Design 5 gives each file its own message.

## Plan questions

- One shared quoting helper or two copies kept in step by `test_vibe_runner_command_matches_hook_command` (`vibe_plugin.py` must stay importable on its own and parse on Python 3.8)? (Design 1)
- Does `vibe_plugin.build` also refuse the characters when called as a library, or only the two `main`s? Exact `ERROR:` wording. (Design 2)
- How do `install_vibe` and `vibe_plugin.main` recognise the restore-failed error: a `BuildError` subclass, an attribute, or a message check? How does `build`'s `finally` skip removing staging in that case? (Design 3)
- On a rerun, does moving a `.old` copy back create `<out>` when it is missing; what error is raised (staging kept) when that move fails; how is `test_vibe_build_turns_stuck_staging_into_build_error` updated? (Design 3)
- When rollback cannot fully remove a swapped-in target, so `<out>/<name>` survives next to a `.old`, does the error say so and does the rerun keep the `.old`? (Design 3)
- Is the duplicate warning left out when no readable file holds a kit command, so only "cannot be read" lines print? (Design 4)
- After a `hooks.toml`, `AGENTS.md` or link-removal `OSError`, which remaining steps (AGENTS.md write, link handling, `NEXT_STEP`) still run before exit 1, and does `remove_kit_links` return a failure flag? (Design 5, Design 6)
- How do tests inject the `OSError`s (in-process calls with monkeypatching, or file-system setups that work on Windows and POSIX)? (Design 5, Design 6)
- Does the publish-guard test write an untracked file into the real repo (and clean up), or use a temp git repo with `tracked()` taking a root? (Design 8)

## Open

- none
