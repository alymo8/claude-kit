# agent-kit

agent-kit is a set of workspace conventions, commands, skills and session hooks
for building software with Claude Code. It is for developers who want a
spec-driven flow: write a spec, gate it, plan it, build it in a git worktree,
review it and merge it, with handoff files and context nudges that keep long
sessions cheap. It also scaffolds new projects (`/new-project`) and adds the
conventions to existing ones (`/adopt-conventions`).

## Install

In Claude Code:

```
/plugin install superpowers@claude-plugins-official
/plugin marketplace add alymo8/claude-kit
/plugin install agent-kit@agent-kit
```

The first line installs the superpowers plugin, whose skills the kit's flow
uses. Hooks run `python`, which must be Python 3.11 or later; `/ship` and the
worktree flow also need `git` and `gh`, signed in.

A contributor who works from a checkout of the repo and also installs the
plugin from the marketplace reruns `python plugin/install.py` afterwards: it
then removes its own `agent-kit` link, so only one copy of the kit loads.

## What runs automatically

Every hook is a Python script in this plugin, listed in `hooks/hooks.json`.
Each one exits 0 even when it fails (errors go to stderr), so a hook never
blocks your work. The `CLAUDE_KIT_*` switches named below turn a hook off or on.

| Event | Script | Reads | Writes | Prints |
|---|---|---|---|---|
| PostToolUse (Write, Edit) | `hooks/on_spec_edit.py` | the edited file's path from the hook event | when the file is a spec or plan under `docs/superpowers/specs/` or `plans/`, regenerates `docs/superpowers/README.md` through `spec-index.py` | nothing, except errors |
| SessionStart | `hooks/worktree_audit.py` | `git worktree list` and the local branches of the current repo | nothing (never deletes or prunes) | a short list of leftover worktrees and merged, upstream-gone or upstream-less branches, or nothing |
| SessionStart | `hooks/lean_context_inject.py` | `CLAUDE_KIT_LEAN_CONTEXT` | nothing | a one-paragraph token-discipline rule as session context (off with `CLAUDE_KIT_LEAN_CONTEXT=0`) |
| SessionStart | `hooks/kit_map_inject.py` | the playbook table in `./conventions/README.md` | nothing | the plugin root and the absolute path of each playbook (off with `CLAUDE_KIT_KIT_MAP=0`) |
| SessionStart | `hooks/workspace_rules_inject.py` | `rules.md` in this plugin, `CLAUDE_PROJECT_DIR` or the event's `cwd`, and `git rev-parse --git-common-dir` | nothing | the workspace rules as session context when the project is outside a kit checkout (off with `CLAUDE_KIT_WORKSPACE_RULES=0`) |
| SessionStart | `hooks/grill_inject.py` | `CLAUDE_KIT_GRILL` | nothing | the spec-grill rule, only when `CLAUDE_KIT_GRILL=1` |
| SessionStart (startup, clear) | `hooks/handoff_inject.py` | `.claude/handoffs/<branch>.md` in the current repo and `git` branch state | nothing | the current branch's handoff when it is under seven days old, else one line naming fresh handoffs for other branches, or nothing |
| PreCompact | `hooks/precompact_keep.py` | `CLAUDE_KIT_PRECOMPACT` | nothing | one instruction for the compaction summary (off with `CLAUDE_KIT_PRECOMPACT=0`) |
| SessionEnd | `hooks/handoff_snapshot.py` | the tail of the session transcript (your last few prompts), `git` status, log and upstream, and the open PR's URL through `gh pr view` | creates `.claude/handoffs/<branch>.md`, or replaces only its State section | nothing, except errors |
| Stop | `scripts/spec-index.py` | the specs and plans under `$CLAUDE_PROJECT_DIR/docs/superpowers/` (else the current folder's) | `docs/superpowers/README.md`, only when its content changed and it carries the generated marker | nothing, except errors |
| UserPromptSubmit | `hooks/context_nudge.py` | the tail of the session transcript (token usage of the last API call) and `CLAUDE_KIT_NUDGE_AT`, `CLAUDE_KIT_NUDGE_STEP` | a small marker file, `<scratchpad>/claude-kit/nudge-level` in the session's scratchpad folder (else a `claude-kit-nudge-<session>` file in the system temp folder), holding the last threshold crossed | a one-sentence nudge to run `/handoff` and `/clear` when the context passes 300k tokens, then every further 100k |

`hooks/run.py` runs the same hooks for Mistral Vibe, Codex and Cursor, which
have no `hooks.json` of their own; it skips the Claude-only ones
(`context_nudge.py`, `handoff_snapshot.py`, `precompact_keep.py`,
`on_spec_edit.py`).

## Commands and scripts

Commands and skills run only when you invoke them (the side-effecting commands
cannot be invoked by the model on its own). `/ship`, `/ship-many`, `/ship-fast`
and the spec and plan gates run `git`, `gh`, `python` (the scripts in
`scripts/`) and subagents. `/ship`, `/ship-many` and `/ship-fast` create
branches and worktrees, commit, push branches to your `origin` remote and open
pull requests; `/ship` and `/ship-many` also merge them (squash-merge on
`main`). `/ship-many` starts one headless `claude -p` session per spec
(`scripts/ship-child.py`). `/new-project` and `/adopt-conventions` write files
into the folder you choose, and `install.py` (run by hand from a checkout)
creates a link in your skills folder and edits your settings file for the
status line.

## Network

No hook opens a network connection, except the SessionEnd hook
`handoff_snapshot.py`: when the current branch has an upstream and `gh` is
installed, it runs `gh pr view` (a GitHub API call, with your `gh` sign-in) to
record the branch's pull-request URL in the handoff file.

Scripts under `scripts/` that reach the network, each only when you run the
command or skill that calls it:

- `handoff.py` (`/handoff` and the SessionEnd hook): `gh pr view`, as above.
- `review-threads.py` (the `pr-review-respond` skill): one `gh api graphql`
  query that reads a pull request's review threads, reviews and comments.
- `ship-child.py` (`/ship-many`): `gh pr list` to check whether a child's pull
  request merged, and `claude -p`, which talks to Claude like any session.

Commands and skills that call `gh` or reach your git remote: `/ship`,
`/ship-many` and `/ship-fast` (`git fetch`, `git push`, and `gh pr` and
`gh run` commands that create, edit and watch the pull request and its CI,
and for `/ship` and `/ship-many` merge it with `gh pr merge`), the
`pr-review-respond` skill (reads review threads, posts replies and pushes
fixes), the `audit-deep` skill (`gh run list`, when `gh` is signed in) and the
`present` skill (`gh pr view` for pull-request sources). `/new-project` leaves
creating a remote (`gh repo create`) to you.

There is no telemetry. Nothing is sent anywhere else: GitHub calls go through
your own `gh` and `git`, to your own repositories.

## Licence

MIT: see the repository's
[LICENSE](https://github.com/alymo8/claude-kit/blob/main/LICENSE).
