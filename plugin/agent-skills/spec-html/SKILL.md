---
name: spec-html
description: "Render a spec or plan to its HTML view and open it in the browser (latest spec/plan when no path is given)"
disable-model-invocation: true
---

# /spec-html (claude-kit command)

Follow `<plugin>/commands/spec-html.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected claude-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
