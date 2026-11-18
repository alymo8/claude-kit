# ADR 0048: User-config audit is a mode of audit, reports outside repos, never reads secrets

- **Status:** accepted
- **Date:** 2026-11-16

## Context
The repo audit covers one repo's Claude Code config. Most of a user's exposure
sits outside any repo: user settings, MCP servers in `~/.claude.json`, plugin
hooks, skills and scheduled tasks. The idea of auditing that setup comes from
ECC's AgentShield; only the ideas were taken, no code.

## Decision
D1: user-scope auditing is a `--user` mode of `audit`, so it reuses
`rules.md` and `check-findings.py` instead of a second rule set; rejected a
separate `config-audit` skill (duplicated rules and checker wiring) and the
inventory script alone (lists items but judges nothing).
D3: the report goes to `~/.claude/claude-kit/audit/user-config.md`, never into
a repo, because it holds private paths and settings; rejected
`<repo>/docs/audit/`, where it could be committed to a public repo.
D4: the inventory (`user-config-inventory.py`) prints env and header key names
only and masks secrets in hook and `statusLine` commands and MCP `args` and
`url`, and in MCP `command` (`NAME=value` and PowerShell `$env:NAME = value`
values, URL passwords, query values and `Authorization`-style header values
become `***`, key names kept); the session reads the settings files and `.claude.json` only at
the lines the inventory cites, never a command, `args` or `url` line; rejected
reading them in full, and printing those fields verbatim with a wider report
self-check, both of which would load secrets into context.

## Consequences
The user-scope audit reuses the repo audit's rules and citation checker, and
env and header values and secrets in `NAME=value` or URL form never enter the
session's context or the report. The costs: a secret passed as a bare argument
(`--token x`) or in a URL path (a webhook URL) is not masked, and ordinary `--flag=value` values are masked too;
whether the session really keeps to cited lines is a behavioural rule, checked
only by a manual run, not by a test.
