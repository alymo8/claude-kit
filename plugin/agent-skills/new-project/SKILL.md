---
name: new-project
description: "Scaffold a new project with the kit's conventions (knowledge layer, decision log, specs, CI, CLAUDE.md), git-initialised with one commit"
disable-model-invocation: true
---

# /new-project (agent-kit command)

Follow `<plugin>/commands/new-project.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected agent-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
