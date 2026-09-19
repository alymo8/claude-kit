---
description: Write the per-branch handoff file (task, git state, done, next, files, commands, open questions) so the next session can continue from it after /clear
---

Write the handoff for the current branch. It is gitignored, per work tree, and
the next session on this branch loads it automatically on start.

1. Durable first. Ask: did this session produce something that outlives it? A
   finding belongs in `knowledge/`, a locked decision in an ADR under
   `knowledge/decisions/`, a change of approach in the plan under
   `docs/superpowers/plans/`. Write those now; the handoff only links to them.
2. Get the path and the generated State section:

   python "${CLAUDE_PLUGIN_ROOT}/scripts/handoff.py" path
   python "${CLAUDE_PLUGIN_ROOT}/scripts/handoff.py" state

   (Fallback if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/handoff.py`.)
3. Write the file at that path with exactly these sections, in this order. If
   `.claude/handoffs/.gitignore` does not exist, create it containing a single `*`
   line so the folder stays untracked in repos that do not ignore it.

   # Handoff: <branch>

   - **Written:** <YYYY-MM-DDTHH:MM> by /handoff
   - **Spec / plan:** <path or "none">

   ## Task
   One paragraph: what is being built and why. No references to this chat.

   <paste the State section verbatim>

   ## Done this session
   ## Next
   Ordered, concrete steps in the voice of a plan: exact paths and commands.
   ## Files that matter
   `path`: why.
   ## Commands that work
   Exact commands verified this session, in a fenced block.
   ## Open questions
   ## Moved to durable homes
   Links from step 1, or "nothing".

   Keep it under 80 lines. If Next has more than 8 steps, they belong in the plan
   file; link it and keep the first 3 here.
4. End your reply with the path and this sentence: "Run `/clear` to start fresh;
   the next session loads this handoff automatically."
