# claude-kit agent tools

The kit's commands, skills and references are written for Claude Code. In this
agent, read their Claude wording as follows.

The kit's plugin folder is <plugin>.

## Skill names

`superpowers:<name>` and `claude-kit:<name>` mean the skill `<name>`. Load it
the way this agent loads any skill.

## Subagents

"Dispatch a subagent" or "use the Agent tool": use this agent's subagent
feature when it has one (Vibe documents subagents). With none, do the step
inline as a separate pass that rereads its inputs from disk and does not rely
on the conversation.

## Questions to the user

AskUserQuestion and the app's wrap-up box: ask in chat.

## Task list

TodoWrite or the task list: use this agent's own plan or todo feature, or a
short checklist in chat.

## Slash commands

A slash command such as `/ship`: run the wrapper skill of the same name.

## Paths

`${CLAUDE_PLUGIN_ROOT}` means <plugin>. Every `~/.claude/skills/claude-kit`
path in any kit command, skill or reference (for example spec-gate's linter
fallback) also means <plugin>.

## Claude Code built-in skills

The Claude Code built-in `code-review` skill (named by `ship-fast.md`): run the
bundled `requesting-code-review` skill on the branch diff, then fix the
findings it reports.

## Not available in this agent

- `/ship-many`
- the status line
- `token-report.py`
- `audit --user`
- Claude auto-memory
- the transcript, precompact and spec-edit hooks

`/ship` and `/ship-fast` run in one session with no headless child sessions.
The Stop-time `spec-index.py` keeps the specs index current.
