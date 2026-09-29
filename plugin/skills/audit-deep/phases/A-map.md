# Phase A: repo map and product

Build the shared map that the four area audits will depend on, and cover the
product picture. Do not audit quality, security or design here.

## Step 1: orient before reading deeply

- Identify build files, entry points and service boundaries.
- Contributors: `git log --format=%an | sort | uniq -c | sort -rn | head -20`
- Churn: `git log --name-only --format= --since="18 months ago" | sort | uniq -c | sort -rn | head -40`
- Lines of code by directory, excluding vendored, generated and lockfile
  paths. Count from `git ls-files` and say which tool you used.

## Step 2: write `docs/audit/00-repo-map.md`

Start with a header: repo, date, commit (`git rev-parse --short HEAD`) and the
production bar. Then:

- Tech stack and runtime, with versions where pinned.
- Entry points: every process, CLI, server, worker, scheduled job and hook.
- Module boundaries: a table of directory, purpose, approximate LOC, and the
  source file you verified the purpose from.
- Data stores, external services and third-party APIs it calls.
- The 20 highest-churn files, with a one-line note on what each does.
- Directories you are deliberately skipping, and why.
- "Read these first": the 10 files a later auditor should open to understand
  this codebase.
- "AI tooling config": inventory the repo's CLAUDE.md files (rough size in
  tokens, characters / 4, and what they cover) and everything in `.claude/`
  and `.mcp.json` (settings, hooks, subagents, commands, skills, MCP servers).
  Describe only; phases C and D assess it.

## Step 3: write `docs/audit/01-product.md`

- What the platform does, in three sentences.
- Use cases and the business value of each.
- Feature inventory, each feature tied to the code that implements it
  (`path:line`).
- Three or four realistic end-to-end usage scenarios, traced through actual
  code paths: name the files and functions involved at each hop.

## Step 4: close the map

End `00-repo-map.md` with two sections:

- `## Assumptions`: things you concluded but could not confirm.
- `## Open questions for the maintainer`.

The map describes; it does not judge. If you do record a finding, use the
format in the rules and put it under `## Early findings`.
