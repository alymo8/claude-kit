---
name: ship-fast
description: "Use for a proof of concept of about an hour - interview the user for the spec (or take an existing one), have the user read and approve it, ask the product decisions out loud, and take it to a tested, smoke-run pull request with green CI, with no gates, no review round and no merge; independent tasks run in parallel"
disable-model-invocation: true
---

# /ship-fast (claude-kit command)

Follow `<plugin>/commands/ship-fast.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected claude-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
