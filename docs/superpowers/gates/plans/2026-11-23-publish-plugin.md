# Plan gate: Publish the kit as a Claude Code plugin (agent-kit) Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-23-publish-plugin.md
- **Plan SHA-256:** cf90aea4542c725c81e5001e62e18062430b44a1106ade390d22027e9b22aa02
- **Spec:** docs/superpowers/specs/2026-11-23-publish-plugin-design.md
- **Spec SHA-256:** 8b3ba17e9d417c82d3a0300f746466ca31140e264242743eb5892e3588da1b9a
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-23
- **Approved by:** /ship (auto)
- **Date:** 2026-11-23
- **Rounds:** 3 discovery + 1 verification

## Plan-introduced decisions

- `/agent-kit:statusline` is a `--stable-copy` mode of `install-statusline.py`: it copies `statusline.py` into the kept state folder `<config>/claude-kit/statusline.py` and writes a status line that runs that copy; rerunning the command refreshes the copy, so the script updates only when the user reruns it after a plugin update (Task 3).
- `install.py` adds a status line when none is set in every case: the stable-copy command when a marketplace copy is present, the `~/.claude/skills/agent-kit` link command otherwise (Task 3).
- A marketplace copy is detected only from `<config>/plugins/installed_plugins.json` under `agent-kit@agent-kit`; the user-scope entry is preferred, but any entry whose `installPath` exists counts (so a project-scope install also stops the link); a read, parse or shape problem counts as no copy (Task 3).
- `CLAUDE_CONFIG_DIR` moves only the installed-plugins record and the stable copy; `install.py`'s `--settings` and `--skills-dir` defaults stay under `<home>/.claude`, while `install-statusline.py`'s defaults follow `--config-dir` (Task 3).
- An old `claude-kit` skills link is removed only when its target's `.claude-plugin/plugin.json` names `claude-kit` or `agent-kit` (Task 3).
- The old-root `conventions/` test exempts `plugin/rules.md` and every `plugin/conventions/*.md` file outright, treating a bare `conventions/` there as the shipped folder (Task 2).
- `plugin/commands/ship.md:11` names `${CLAUDE_PLUGIN_ROOT}/conventions/engineering-practices.md`, the kit's copy (Task 2).
- `token-report.py` counts `/agent-kit:ship` instead of `/claude-kit:ship`, so older transcripts' `/claude-kit:ship` runs are no longer recognised by `--ship` (Task 4).
- The contributor instructions clone the repo into a folder named `agent-kit` (`git clone https://github.com/alymo8/claude-kit.git agent-kit`) (Task 6).

## Findings fixed

- round 1 [blocking] Old-path test failed on the `conventions/` links kept in `plugin/rules.md`: the scan skips `plugin/rules.md` and `plugin/conventions/*.md`; plan question answer updated.
- round 1 [blocking] Task 3 broke `test_one_wrapper_per_command_except_ship_many`: `tests/test_agent_skills.py` added to Task 3 with the new wrapper set.
- round 1 [blocking] Criterion 6 (PR open) uncovered: Task 7 Step 6 collects the evidence for the PR and checks `gh pr view --json state`.
- round 1 [blocking] ADR-index test contradicted itself: the row check uses `re.search(r"amended by [\d, ]*0052", row)`.
- round 1 [minor] `run_install` env handling clarified; session-hygiene kit-map sentence reworded in Task 2; Task 5 worktree path made absolute.
- round 2 [blocking] Task 3 commit left out `tests/test_agent_skills.py`: added to the `git add` line.
- round 2 [blocking] Task 4 rename would corrupt the state-folder path in `statusline.md`: the command writes `<config>/claude-kit/`, which joins `ALLOWED`.
- round 2 [minor] settings default under `CLAUDE_CONFIG_DIR` stated; Task 3 now depends on Task 1 and appends its manifest test at the end; garbled sentence split; `session-hygiene.md` added to Task 2 Files; live-check paths noted as forward slashes.
- round 3 [blocking] PowerShell wrapper test ran against the real config dir: it passes `-Home` and drops `CLAUDE_CONFIG_DIR`, and asserts the `agent-kit` link.
- round 3 [blocking] "version test does not exist": not changed; `test_version_is_0_36_1` exists at `tests/test_plugin_manifest.py:209` (confirmed by verification round 1).
- round 3 [minor] Task 5 creates its cwd; Task 6 test names `docs/setup.md` and the sentence is reworded; `plugin/rules.md` defines `<plugin root>`.

## Open

- none
