# /ship-fast: cleanup (on request)

Part of `commands/ship-fast.md`, which reads this file when it reaches it. That command's Stop rules and Git lock retry apply here.

Stop the app started in step 5. Leave the feature worktree (`ExitWorktree`
with `keep` if the session entered it with `EnterWorktree`, otherwise
change directory). If the task used Docker: stop and remove the containers
labelled `claude-kit.task=<slug>` (`docker compose -p <slug> down
--volumes --rmi local` for a stack), remove the images, volumes and
networks it created or pulled that are not in the step-4 baseline, and
`docker buildx rm <slug>`; never run a prune without a
`label=claude-kit.task=<slug>` filter. If the task used Docker, then run
`python "${CLAUDE_PLUGIN_ROOT}/scripts/docker-disk.py"` (fallback
`~/.claude/skills/claude-kit/scripts/docker-disk.py`) and put its
`docker disk:` line in your clean-up reply; it changes nothing and never
prompts. Then
`git -C <main-checkout> worktree remove <worktree-path>`,
`git -C <main-checkout> worktree prune` and
`git -C <main-checkout> branch -D poc/<slug>`. The remote branch stays for
the PR; the user deletes it when merging. A handoff an earlier stop wrote
on this branch (`.claude/handoffs/poc_<slug>.md`) lives in the feature
worktree and goes with `worktree remove`; leave the main checkout's handoff
files alone. Delete the step-4 Docker baseline file and any scratch files
you created outside the repo; the spec under `~/.claude/ship-fast-specs/`
is not a scratch file and stays. The repository itself always stays.
