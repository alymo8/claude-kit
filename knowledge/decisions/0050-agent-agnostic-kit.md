# ADR 0050: The kit runs in Mistral Vibe, Codex and Cursor from one source

- **Status:** accepted; amended by 0052 ([ADR 0052](0052-published-plugin.md): rules table changed for other agents; markers renamed `agent-kit`); amended by 0054 ([ADR 0054](0054-vibe-native-plugin.md): Vibe gets native plugins instead of skill links and a user hook block)
- **Date:** 2026-11-22

## Context
The kit worked only in Claude Code: its rules sat in `CLAUDE.md`, its hooks
in a Claude plugin manifest and its skills in a Claude skills dir. Mistral
Vibe, Codex and Cursor share three things the kit can use: an `AGENTS.md`
instruction file, the `~/.agents/skills/` skills folder and a user hook file
that runs a command at session start. The design is in
`docs/superpowers/specs/2026-11-18-agent-agnostic-kit-design.md`.

## Decision
- D1: one source, adapted per agent. The kit root's rules move to `AGENTS.md`,
  `CLAUDE.md` becomes an `@AGENTS.md` stub, and `plugin/install.py --agent`
  adapts the rest; rejected a static `AGENTS.md` with no hooks (loses the
  worktree audit, handoff and per-session context) and per-agent copies
  (drift).
- D2: `plugin/hooks/hooks.json` stays the one hook list. The runner
  `plugin/hooks/run.py` reads it, so a new hook reaches every agent; rejected
  a separate manifest that generates `hooks.json`.
- D3: map tools, don't rewrite skills. One reference file explains Claude
  wording to other agents and Claude's skill text is untouched; rejected
  editing 19 skill and command files to add fallbacks.
- D4: bundle a pinned superpowers copy under `vendor/superpowers/`, only for
  non-Claude agents and outside `plugin/skills/`; rejected downloading it at
  install time.
- D5: existing repos keep `CLAUDE.md`; the runner injects a project
  `CLAUDE.md` when there is no `AGENTS.md`; rejected migrating every project
  repo now.
- D6: Claude-only features stay Claude-only (`/ship-many`, status line,
  token report, `audit --user`, transcript, precompact and spec-edit hooks).
  In other agents `/ship` and `/ship-fast` run in one session, using
  subagents per the tool mapping; the Stop-time `spec-index.py` keeps the
  specs index current.
- D7: all three agents in this version. Codex is covered by tests and
  checked live once installed.
- D8: moving project repos to `AGENTS.md` is a separate spec; the runner
  works for `CLAUDE.md`-only repos.
- D9: the workspace rules are injected for every non-Claude agent in child
  repos inside the kit folder too; rejected relying on Vibe's native load,
  which gives no rules when only the child repo is trusted.
- D10: nothing is frozen; the Claude-unchanged check compares against
  `origin/main` itself, not a committed fixture.
- D11: capture-learnings follows the stub. A repo whose root `CLAUDE.md` is
  only `@AGENTS.md` gets its learnings in `AGENTS.md`; rejected appending
  under the stub, which only Claude would see.

## Consequences
- Claude Code's output is unchanged apart from the workspace-rules header,
  which now names `AGENTS.md`.
- A new hook added to `hooks.json` reaches every agent, unless it is in the
  Claude-only set.
- After editing a command, run `python plugin/scripts/agent-skills.py` to
  regenerate its wrapper skill; a test fails while the wrappers are stale.
- Updating superpowers means rerunning
  `python plugin/scripts/vendor-superpowers.py --from <dir>` and committing
  the new bundle.
- Cursor runs `sessionStart` hooks fire-and-forget, so the kit map may not
  reach the model; the installer prints a line to paste into Cursor's user
  rules as a fallback.
- Plan decisions beyond the spec's text: rerunning the installer relinks a
  kit link whose skill moved between the kit's skill roots and removes a
  dangling link into those roots; `run.py` swaps a leading `python` or
  `python3` in a `hooks.json` command for the interpreter running it.
