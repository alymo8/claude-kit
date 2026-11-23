# Audit: user mode

Audits the user-scope Claude Code setup in the home directory, read-only.

## Rules

Read `rules.md` in this directory in full. Its read-only, finding-format,
hard-rule and self-check sections bind this mode, with one change: "repo root"
is the home directory. Paths in **Where** are relative to it; a file outside it
is cited by its absolute posix path, as the inventory writes it.
`~/.claude/claude-kit/audit/` replaces `<repo>/docs/audit/` as the one folder
section 1 lets the audit write to. The scratch-file rule is unchanged.

## Setup

1. **Production bar.** Use the user's, if they gave one. Otherwise use "one
   person's workstation: agents with tool access to their private repos,
   accounts and credentials", and mark it default in the report header.
2. **Existing report.** If `~/.claude/claude-kit/audit/user-config.md` exists,
   ask before overwriting it.

## Inventory

Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/user-config-inventory.py"` (fallback
`~/.claude/skills/claude-kit/scripts/user-config-inventory.py`) and read its
stdout; redirect long output to the `audit-scratch` folder. It prints one JSON
object with the keys `settings`, `mcp_servers`, `plugins`, `skills`,
`scheduled_tasks`, `instructions` and `errors`. Every item has `file` and a
1-based `line`; env and header values never appear, only key names. Hook and
`statusLine` commands and MCP `command`, `args` and `url` come masked:
`NAME=value` and `$env:NAME = value` values, URL passwords, query values and
auth header values read `***`. Report each
`errors` entry as unread.

## Reading

Never read `.claude/settings.json`, `.claude/settings.local.json` or `.claude.json` in full: read only the line ranges the inventory cites (for an MCP server, its cited line only, never a range), never an `env` or `headers` block, and never the line of a hook or `statusLine` command or an MCP server's `args` or `url`: take those from the inventory, which masks them. A finding on such an item cites the inventory's `file:line` for it. Its Evidence quotes the inventory's masked text with each `***` written as `...` (`check-findings.py` skips the text at a `...`), and any part holding a `"` or `\`, which the JSON file escapes, written as `...` too. Its Confidence is `inferred (from: inventory)`.

Read in full:

- every hook command's target script (the kit's, skills-dir plugins' and
  installed plugins'), and the `statusLine` command's target script;
- skill files, scheduled-task files and every `instructions` file;
- for an item with `manifest_hooks: true`, its `.claude-plugin/plugin.json` and
  every hooks file it names. Treat those hooks like the listed ones.

Resolving a hook command (the inventory's masked `hooks[].command` or `statusLine.command`):

1. Substitute `${CLAUDE_PLUGIN_ROOT}` with the item's `root`, and `~`, `$HOME`
   and `%USERPROFILE%` with the home directory.
2. Skip the interpreter (`python`, `python3`, `py`, `node`, `bash`, `sh`,
   `pwsh`, `powershell -File`, `uv run`).
3. The first remaining path argument is the target: relative to `root` for a
   plugin hook, to the home directory otherwise.
4. A command with no resolvable script (inline shell, a program on PATH) is
   judged on its text and listed under what was not read.

## Checks

Apply section 4 of `rules.md`, both halves ("Does it work" and "Is it built
well"), to every item. Add:

- Permission rules broader than their apparent purpose, and auto-approve modes.
- Hooks that run on every tool call or prompt, or that fetch or run remote
  code.
- MCP servers with unpinned packages (`npx` or `uvx` without a version), remote
  URLs, or wide scope.
- Plugins without a pinned commit. For a project-scope plugin (`scope`,
  `project_path`), say that its project's settings decide whether it is enabled
  and that they were not read.
- Scheduled tasks that read untrusted content (web, inbox, notes ingest) with no
  human in the loop.
- Untrusted text paths into a tool-using model across the whole setup.

For a skills entry that is a link, `link` and `target` say where it points;
cite files inside it through the entry path.

## Output

Write `~/.claude/claude-kit/audit/user-config.md` (create the folder), because
it holds private paths and settings: never inside a repo. Header: date, home
directory written as `~`, the `version` in the kit's `plugin.json`
(`../../.claude-plugin/plugin.json` from this directory), production bar, and
what was not read. Sections, in order:

1. `## Inventory` (tables)
2. `## Permissions`
3. `## Hooks`
4. `## MCP servers`
5. `## Plugins`
6. `## Skills`
7. `## Scheduled tasks`
8. `## Instructions`
9. `## Fix first`

Findings use the format in `rules.md`. Never copy a secret or an env or header
value.

## Self-check

A file the report quotes (a scheduled task, a hook script) can hold an env
value. Search the report for every `env` value in the two settings files and
every `env` and `headers` value in `.claude.json` with a throwaway script in
`audit-scratch`, run with `python -I`, that
prints only counts and key names, never a value; skip values shorter than 4 characters, which match ordinary
words. Replace each hit in the report with `<redacted: KEY>` and search again
until none is found.

Run `python <dir of rules.md>/../../scripts/check-findings.py <home> <report>`
until it exits 0. In chat: counts by severity, the top five from Fix first, the
checker's summary line and the report path. Open the report (`Invoke-Item` on
Windows, `open` on macOS, `xdg-open` on Linux).
