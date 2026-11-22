---
name: handoff
description: "Write the per-branch handoff file (task, git state, done, next, files, commands, suggested skills, open questions) so the next session can continue from it after /clear"
disable-model-invocation: true
---

# /handoff (claude-kit command)

Follow `<plugin>/commands/handoff.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected claude-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
