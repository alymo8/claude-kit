---
description: Write the per-branch handoff file (task, git state, done, next, files, commands, suggested skills, open questions) so the next session can continue from it after /clear
argument-hint: "What will the next session focus on?"
---

Write the handoff for the current branch. It is gitignored, per work tree,
and no hook loads it in agent-kit-lite, so the next session reads it when
the user asks.

If arguments were passed (`$ARGUMENTS`), they describe what the next session will
focus on: shape Task, Next, Suggested skills and Open questions around that focus,
and leave out what it does not need.

1. Durable first. Ask: did this session produce something that outlives it? A
   finding belongs in `knowledge/`, a locked decision in an ADR under
   `knowledge/decisions/`, a change of approach in the plan under
   `docs/superpowers/plans/`. Write those now; the handoff only links to them.
2. Get the path and the generated State section:
   - **Path:** `<git rev-parse --show-toplevel>/.claude/handoffs/<name>.md`,
     where `<name>` is the branch (`git branch --show-current`, or
     `detached-<git rev-parse --short=7 HEAD>` when detached) with every
     character other than letters, digits, `.`, `_` and `-` replaced by
     `_` (`feat/x` becomes `feat_x`).
   - **State section:** write these lines from the commands named:
     `## State`
     `- branch: <branch>  (worktree: <git rev-parse --show-toplevel>)`
     `- upstream: <git rev-parse --abbrev-ref @{u}>, ahead <A>, behind <B>`,
       where `<B>` and `<A>` are the two numbers `git rev-list --left-right
       --count @{u}...HEAD` prints; or `- upstream: none` without an upstream
     `- dirty:` the paths from `git status --porcelain`, comma-separated, or
       `clean`
     `- last commits:` `git log --oneline -5` joined with `"; "`, or `none`
     `- PR:` the URL from `gh pr view --json url -q .url`, or `none`
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
   connection strings or personal details.
   Every future session on this branch may read it.
   Write `<redacted>` and say where the value
   lives (env var name, secret store) instead.

   Keep it under 80 lines. If Next has more than 8 steps, they belong in the plan
   file; link it and keep the first 3 here.
4. End your reply with the path and this sentence:
   "Run `/clear`, then start the next session with: read
   `.claude/handoffs/<name>.md` and continue."
