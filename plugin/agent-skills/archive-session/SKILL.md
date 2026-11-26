---
name: archive-session
description: "Archive this conversation from within it (it leaves the Vibe sessions list; reversible), or restore an archived one"
disable-model-invocation: true
---

# /archive-session (agent-kit command)

Follow `<plugin>/commands/archive-session.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected agent-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
