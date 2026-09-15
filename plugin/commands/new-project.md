---
description: Scaffold a new project with the kit's conventions (knowledge layer, decision log, specs, CI, CLAUDE.md), git-initialised with one commit
argument-hint: [name] [node|python]
---

Scaffold a new project from the claude-kit templates. Arguments: `$ARGUMENTS`
(expected: `<name> <node|python>`).

1. If the name or the stack is missing or the stack is not `node` or `python`,
   ask for it before doing anything.
2. Run, from any directory:

   python "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" --name <name> --stack <stack>

   If `${CLAUDE_PLUGIN_ROOT}` is not expanded in this context, the script lives at
   `~/.claude/skills/claude-kit/scripts/scaffold.py`. The project is created
   inside the workspace directory (the kit checkout's root), beside the other
   project repos, on `main`, with one commit. Pass `--parent <dir>` only if the
   user asks for a different location.
3. Show the script's output verbatim. If it exits non-zero, show the error and stop.
4. Close with the next steps the script printed: the stack's own init command
   (required before CI is green), `/init` to fill in `CLAUDE.md`, and creating the
   remote (`gh repo create --private`) as the user's own step. Never create the
   remote or push unless the user explicitly asks.
