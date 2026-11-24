---
description: Scaffold a new project with the kit's conventions (knowledge layer, decision log, specs, CI, CLAUDE.md), git-initialised with one commit
argument-hint: "[name] [node|python]"
disable-model-invocation: true
---

Scaffold a new project from the agent-kit templates. Arguments: `$ARGUMENTS`
(expected: `<name> <node|python>`).

1. If the name or the stack is missing or the stack is not `node` or `python`,
   ask for it before doing anything.
2. Run, from any directory:

   python "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" --name <name> --stack <stack>

   If `${CLAUDE_PLUGIN_ROOT}` is not expanded in this context, the script lives at
   `<plugin root>/scripts/scaffold.py`.
   `<plugin root>` is the plugin root stated in the kit map, else `~/.claude/skills/agent-kit`.
   The project is created in the kit's main checkout when the current folder is
   inside a kit checkout or one of its worktrees, else in the kit checkout the
   plugin runs from (a contributor link), else in the current folder; never in
   the plugin cache or a worktree. It is on `main`, with one commit. Pass
   `--parent <dir>` only if the user asks for a different location.
3. Show the script's output verbatim. If it exits non-zero, show the error and stop.
4. Close with the next steps the script printed: the stack's own init command
   (required before CI is green), `/init` to fill in `CLAUDE.md`, and creating the
   remote (`gh repo create --private`) as the user's own step. Never create the
   remote or push unless the user explicitly asks.
