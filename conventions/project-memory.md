# Project memory file

Every repo carries a **project memory file** at its root — a checked-in `CLAUDE.md`
holding the handful of things anyone (human or agent) needs to work in the repo:
build commands, test commands, architectural conventions, and gotchas. It is cheap
to write and disproportionately effective: it removes the rediscovery tax that gets
paid at the start of every session.

Because it is **static**, it sits in the cacheable prefix of every request — the
cost is paid once, not per turn. That is only true while the file stays stable, so
churn is expensive and brevity is a feature, not a nicety.

## Principles

1. **Checked into the repo, not stored per-machine.** The memory file is part of the
   project, reviewed like code, and improves for everyone who clones it.
2. **Operational, not encyclopedic.** It answers *"how do I work in this repo?"* —
   not *"what does this project know?"* (that is the
   [knowledge layer](knowledge-layer.md)) and not *"why did we choose this?"* (that
   is the [decision log](decision-log.md)). Link out to those; do not restate them.
3. **Earn every line.** Include what a competent newcomer would otherwise waste time
   rediscovering or get wrong. Leave out what the repo already makes obvious in
   seconds.
4. **Stable by default.** Edit it deliberately, as part of the change that made it
   wrong. Rewriting it casually throws away the cache benefit and the trust in it.

## What goes in it

- **Setup / prerequisites** — runtimes and versions, `install` command, required env
  vars (names only, never values), services that must be running.
- **Build & run commands** — exact, copy-pasteable, including how to run the app
  locally.
- **Test commands** — the full suite *and* how to run a single test or file, plus
  lint / format / type-check commands.
- **Architecture in brief** — where things live, the module or service boundaries,
  the one or two flows that explain the shape of the codebase.
- **Project conventions** — naming, layering, error handling, migration or codegen
  steps, commit/branch rules that differ from the workspace defaults.
- **Gotchas** — the footguns: things that look wrong but are intentional, steps that
  must run in a specific order, flaky areas, platform quirks.
- **Pointers** — one-line links to `knowledge/`, `knowledge/decisions/`, and
  `docs/superpowers/specs/`.

## What stays out

- Anything discoverable in seconds from the repo tree or `package.json`-equivalent.
- Fast-moving detail (open TODOs, in-flight task state, current sprint) — that
  belongs in specs, plans, or issues.
- Secrets, credentials, or real config values.
- Long prose, tutorials, or duplicated knowledge docs — link instead.

## Conventions

- **One screen, roughly.** If it grows past ~100 lines, most of it belongs in
  `knowledge/` with a link from here.
- **Imperative and concrete.** Exact commands in fenced blocks; no "the usual build".
- **Update it in the same PR** that changes a command, layout, or convention it
  documents — a stale memory file is worse than none, because it is trusted.
- **Bootstrap it with `/init`**, then prune hard: the generated draft is a starting
  point, not the deliverable.
- Workspace-wide preferences live in the workspace `CLAUDE.md` one level up; the
  project file records only what is *specific to this repo*.

## Definition of done

- A checked-in `CLAUDE.md` exists at the repo root.
- Someone who has never seen the repo can install, build, test, and run a single
  test from it alone, without asking.
- Its architecture notes, conventions, and gotchas match the current code.
- It links to the knowledge base, decision log, and specs instead of duplicating
  them.
