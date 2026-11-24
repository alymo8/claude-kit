---
name: adopt-conventions
description: "Add the kit's conventions to an existing repo (CLAUDE.md skeleton, knowledge layer, decisions, specs index, CI, secret scan, PR template), writing only files that do not exist"
disable-model-invocation: true
---

# /adopt-conventions (agent-kit command)

Follow `<plugin>/commands/adopt-conventions.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected agent-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
