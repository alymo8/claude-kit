---
name: docker-compact
description: "Reclaim unused space in Docker Desktop's virtual disk on Windows (asks first; stops Docker; one UAC prompt)"
disable-model-invocation: true
---

# /docker-compact (agent-kit command)

Follow `<plugin>/commands/docker-compact.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected agent-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
