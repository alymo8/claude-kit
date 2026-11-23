---
description: Add the kit's status line (context tokens, cost, branch) to your Claude Code user settings when none is set
disable-model-invocation: true
---

Add the kit's status line to the user's Claude Code settings.

1. Run:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/install-statusline.py" --stable-copy
   ```

   Where `${CLAUDE_PLUGIN_ROOT}` is not expanded, use the plugin root stated in the kit map, else `~/.claude/skills/agent-kit`, in its place.

2. Show its output verbatim, then explain:
   - It never replaces a status line the user set; a line that still runs the
     script through the old link is moved to the new one.
   - It copies the script to `~/.claude/claude-kit/` (or `<config>/claude-kit/`
     when `CLAUDE_CONFIG_DIR` is set), so the line survives plugin updates.
   - After a plugin update, rerun `/agent-kit:statusline` to refresh the copy.
   - The status line shows from the next prompt.
