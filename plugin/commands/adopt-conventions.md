---
description: Add the kit's conventions to an existing repo (CLAUDE.md skeleton, knowledge layer, decisions, specs index, CI, secret scan, PR template), writing only files that do not exist
argument-hint: [node|python]
---

Add the claude-kit convention files that are missing from the current repository.
Argument: `$ARGUMENTS` (expected: `node` or `python`).

1. If the stack is missing or not `node` / `python`, ask for it.
2. Confirm the current directory is the repo root (`git rev-parse --show-toplevel`);
   if not, `cd` there. Then run:

   python "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" --adopt --stack <stack>

   (Fallback path if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/scaffold.py`.) The script never overwrites
   and never commits.
3. Show its `created:` and `skipped (already present):` lists verbatim.
4. If `.gitignore` was skipped, remind the user to make sure it ignores
   `docs/superpowers/**/*.html` and `.env*`. Tell the user to review `git status`
   and commit when satisfied; do not commit for them unless asked.
