---
description: Write the per-branch handoff file (task, git state, done, next, files, commands, suggested skills, open questions) so the next session can continue from it after /clear
argument-hint: "What will the next session focus on?"
---

Write the handoff for the current branch. It is gitignored, per work tree, and
the next session on this branch loads it automatically on start.

If arguments were passed (`$ARGUMENTS`), they describe what the next session will
focus on: shape Task, Next, Suggested skills and Open questions around that focus,
and leave out what it does not need.

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
   - **Next focus:** <the arguments, or "continue the task">

   ## Task
   One paragraph: what is being built and why. No references to this chat.

   <paste the State section verbatim>

   ## Done this session
   Commit SHAs with their subjects, plus anything not yet committed. Do not
   describe what a commit or diff already shows.
   ## Next
   Ordered, concrete steps in the voice of a plan: exact paths and commands.
   ## Files that matter
   `path`: why.
   ## Commands that work
   Exact commands verified this session, in a fenced block.
   ## Suggested skills
   Skills the next session should load with the Skill tool, each with one line on
   when (e.g. `superpowers:executing-plans`: resume the plan at task 4).
   ## Open questions
   ## Moved to durable homes
   Links from step 1, or "nothing".

   Do not duplicate what already lives in a spec, plan, ADR, issue, commit or
   diff: link it by path, SHA or URL instead.

   Never write secrets or personal data: no API keys, tokens, passwords,
   connection strings or personal details. The file is re-injected into every
   future session on this branch. Write `<redacted>` and say where the value
   lives (env var name, secret store) instead.

   Keep it under 80 lines. If Next has more than 8 steps, they belong in the plan
   file; link it and keep the first 3 here.
4. End your reply with the path and this sentence: "Run `/clear` to start fresh;
   the next session loads this handoff automatically."
