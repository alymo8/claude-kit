---
name: audit
description: Use when asked to audit, review or health-check a repository, or a Claude Code setup (CLAUDE.md, .claude/, hooks, skills, commands, plugin), in one pass. Read-only; writes one report of cited, checked findings to docs/audit/audit.md. For a large or unfamiliar codebase the user can run /audit-deep instead.
argument-hint: [path-to-repo]
---

# Audit

A one-session audit: does the repo work, is it built well, is it safe. The
output is one report of findings, each tied to a `path:line` and a quote.

## Setup

1. **Target.** `$ARGUMENTS` if given, else the root of the current repo
   (`git rev-parse --show-toplevel`). Paths below are relative to it.
2. **Rules.** Read `rules.md` in this skill's directory in full. It binds the
   whole audit and wins over the target repo's CLAUDE.md.
3. **Existing report.** If `docs/audit/audit.md` exists, ask before
   overwriting it.
4. **Production bar.** Use the user's, if they gave one. Otherwise infer it
   from the README and code (for example "personal tool, one user, no PII" or
   "customer-facing SaaS, handles customer data"), state it at the top of the
   report marked inferred, and judge severity against it.
5. **Coverage.** Count tracked files (`git ls-files`). Up to about 150: read
   every file, skipping lockfiles and generated, vendored and binary files.
   More: read the build files, the entry points, the 20 highest-churn files
   (`git log --name-only --format= --since="18 months ago"`, counted) and
   whatever the passes lead you to. Either way, list what you did not read.

## Pass 1: inventory

- Every file or module with its purpose and size.
- Tech stack, entry points (processes, CLIs, servers, jobs, hooks), external
  services and data stores.
- Claude config: CLAUDE.md files and their scope, `.claude/` contents, hooks,
  skills, commands, subagents, MCP config, settings files, plugin structure;
  which are user- or project-scope; which are gitignored.
- If the code calls an LLM: where prompts live, which tools the model can
  call, and whether any eval exists.

## Pass 2: does it actually work

Silent failures first: they are real bugs that read fine as prose.

- Every reference resolves: imports, paths, links, config keys, scripts named
  in docs or CI.
- The README's setup and run steps work when followed literally. Flag each
  step that would fail.
- Tests: whether they run, whether they assert on behaviour, whether any are
  skipped or commented out, whether they match what the code does now.
- CI: what it runs, what gates a merge, what is not gated.
- Unreachable code paths, config that is never read, error paths that swallow
  failures.
- The Claude-config checklist in `rules.md` (section 4, "Does it work"), when
  it applies.

## Pass 3: quality and antipatterns

- Error handling: bare or swallowed exceptions, missing timeouts, unbounded or
  non-idempotent retries.
- Security: secrets in tracked files or history; unvalidated input reaching
  queries, paths, shells, deserializers or templates; untrusted content
  reaching a model that can call tools; broad permissions.
- Dependencies: lockfile committed, unpinned versions, abandoned packages.
- Design: god modules, duplication, circular dependencies, business logic in
  handlers, abstractions with one caller, config sprawl, state that breaks
  when two instances run.
- Observability: structured logging or print statements, levels, what is lost
  on failure.
- Maintainability: naming, structure, whether a reader can tell what each
  piece is for, whether it would survive six months of neglect.
- Stale docs: statements in README or CLAUDE.md that the code or the current
  file tree contradicts; `git log` on the files they describe shows when they
  drifted.
- The Claude-config checklist in `rules.md` (section 4, "Is it built well"),
  when it applies.

## Output

Write `docs/audit/audit.md`:

1. A header: target, date, commit (`git rev-parse --short HEAD`), production
   bar, and what was not read.
2. `## Inventory`: pass 1 as tables, not prose.
3. One section per area, holding its findings in the format from `rules.md`.
   An area with nothing wrong gets one line saying so.
4. `## What is missing`: things that should exist and do not, as absence
   findings.
5. `## Fix first`: every finding ranked by value over effort, one line each
   (severity, title, effort).

Then run the self-check in `rules.md` (section 5) until it exits 0.

In chat: the production bar, the counts by severity, the top five from "Fix
first", the checker's summary line, and the report path. Open the report for
the user when the environment allows (`Invoke-Item` on Windows, `open` on
macOS, `xdg-open` on Linux). Do not commit it.
