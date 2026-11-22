---
name: ship
description: "Use after a spec is approved to land it on main without further check-ins — plan, implement, CI, review, PR, green CI, squash-merge, verify main, clean up"
disable-model-invocation: true
---

# /ship (claude-kit command)

Follow `<plugin>/commands/ship.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected claude-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
