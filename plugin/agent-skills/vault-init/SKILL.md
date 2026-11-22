---
name: vault-init
description: "Scaffold a personal knowledge vault (raw/ and wiki/ folders, templates, Obsidian settings, git repo) at a path"
disable-model-invocation: true
---

# /vault-init (claude-kit command)

Follow `<plugin>/commands/vault-init.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected claude-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
