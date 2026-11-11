---
description: Scaffold a personal knowledge vault (raw/ and wiki/ folders, templates, Obsidian settings, git repo) at a path
argument-hint: <path> [personal|work]
disable-model-invocation: true
---

Create a new vault with the claude-kit template.
Arguments: `$ARGUMENTS` (a path, then optionally `personal` or `work`).

1. If `$ARGUMENTS` has no path, ask for one. The profile defaults to `personal`.
2. Run:

   python "${CLAUDE_PLUGIN_ROOT}/scripts/vault-init.py" <path> --profile <profile>

   (Fallback path if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/vault-init.py`.) The script refuses a
   non-empty path, never creates a remote and never pushes.
3. Show its output verbatim, including the next steps it prints.
4. On a non-zero exit, report it and stop.
