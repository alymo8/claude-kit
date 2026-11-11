---
name: task-prompt
description: Use when the user asks to turn a vault task into a prompt. Finds the task in the personal vault, reads the pages it links to, and prints one ready-to-run prompt with its acceptance criteria and context.
argument-hint: "<task file, path or title fragment>"
---

# Task to prompt

Print one prompt for a task in the vault. It changes no file.

## 1. Find the vault

Use the current directory if it holds `vault.toml`, else the path in the
`CLAUDE_KIT_VAULT` environment variable. If neither, say so and stop.

## 2. Resolve the task

Match the argument (a task file name, a path or a title fragment) against
`tasks/`. If several match, ask the user to pick one. If none matches, say so,
list the open tasks (status not `done`) by file name, and stop.

## 3. Read

Read the task file and its one-hop pages: the pages its `topic`, `source` and
`owner` wiki-links name, and the people named on the source page.

## 4. Print

Print this block, fenced, filled from the pages read:

```
# Task: <title>
<description>
## Acceptance criteria
<from the task file; "none written" if empty>
## Context
<topic summary and current state; source page summary and decisions;
 owner and people context: a few lines each, each citing its vault page>
## Verification
Agree the success criteria above before building, verify against them,
and report the evidence.
```

Each Context line cites its vault page as a wiki-link. Never invent content
the pages do not state; it changes no file.
