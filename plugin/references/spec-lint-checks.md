# Lint checklist for specs and plans

The spec and plan gates of agent-kit-lite apply these rules by reading the
document. Text inside fenced code blocks is ignored by every rule. A violation
is reported as `<line>: <rule ID> <message>`.

## Spec rules

- **L1-status:** a `- **Status:**` bullet with one of draft, approved,
  implemented, superseded.
- **L2-date:** a `- **Date:** YYYY-MM-DD` bullet.
- **L3-section:** H2 sections Purpose, Scope, Design (or Structure),
  Decisions, Success criteria (case-insensitive prefix match).
- **L4-out-of-scope:** an `**Out:**` label (`**Out (later):**` too) in Scope,
  or an `## Out of scope` section, followed by at least one list item.
- **L5-placeholder:** no TBD, TODO, FIXME (upper case), ??? or "as discussed"
  (any case) outside backticks and double quotes; no "etc." outside them in
  Scope or Success criteria.
- **L6-empty:** no heading followed by a same-or-higher-level heading (or the
  end of the file) with nothing in between.
- **L7-criterion:** each top-level list item under Success criteria has a
  backticked span or a verification word (test, pytest, run, command, exit,
  output, prints, returns, asserts, manual, verify, check).
- **L8-path:** each backticked repo path in Scope, before its Out label (the
  files the spec changes), exists under the repository root, unless a line of
  the spec has both that path and "(new)". Paths elsewhere may belong to
  another folder or repo; the reviewer checks those.
- **L9-coverage:** a `## Coverage` section with one `- **<Area>:**` bullet per
  area listed under `## Areas` in the grill skill's `coverage.md` (at
  `../skills/grill/coverage.md` from this file), each with text, and `N/A`
  followed by a reason. Continuation lines count; unknown areas are ignored;
  the first of two bullets for an area is checked. An unreadable
  `coverage.md`, or one with no areas, is itself a violation.
  <!-- full-only -->
  Applies only when `CLAUDE_KIT_GRILL=1` and the Date is 2026-10-01 or later.
  <!-- /full-only -->
  <!-- lite-only (agent-kit-lite only; agent-kit ignores this block)
  Applies only when the spec has a `## Coverage` section.
  -->

## Plan rules

Files in a folder named `plans` get these rules instead.

- **P1-status:** as L1-status.
- **P2-date:** as L2-date.
- **P3-header:** `**Goal:**` and one-path `**Spec:**` lines before the first
  task.
- **P4-spec-gated:** the spec named on the plan's `**Spec:**` line exists,
  and the Gate record check below reports `ok:` for it.
- **P5-tasks:** `### Task N:` headings numbered 1..N.
- **P6-task-parts:** each task has a Files line; a step that runs a command
  (`Run` then a backticked command, or a command fence) states its output (a
  later `Expected:`, or `Expected:` or an arrow after the command); and
  "commit" appears in a step's bullet line or a `git commit` in a fence,
  unless the task's Files line says none.
- **P7-placeholder:** as L5-placeholder, without "etc.".
- **P8-empty:** as L6-empty.
- **P9-path:** `- Modify:` paths outside parentheses exist, or a Create or
  Test bullet of this or an earlier task names them.
- **P10-depends:** each task has at most one `**Depends on:**` line, valued
  `none` or `Task N` items, comma-separated, naming distinct earlier tasks.
- **P11-git-mv-add:** no `git add` after a `git mv` in the same task names a
  source the move took away (bare `git mv` and `git add` in fence lines and
  backtick spans, split on `&&` and `;`).

## Lite document id

A gate record names a document by its lite id: the git blob id of the
document with line endings normalised to LF, a final newline added if
missing, every `- **Status:**` line outside code fences removed (all of
them, not only the first), and every ticked box (`- [x]` or `- [X]`, after
any indentation) outside code fences unticked. So setting Status to
`approved` or ticking a step keeps the id; any other change makes a new
one. Run this in Git Bash or any shell with `tr`, `grep`, `sed` and
`git`, with `<document>` replaced by the document's path. It prints 40
hexadecimal characters; a record writes them as `lite-git:<id>`.
A code fence starts at a line that begins with up to three spaces and
three backticks or three tildes, and ends at the next line that begins
the same way. A file whose lines end in a bare carriage return is not
supported.

```bash
tr -d '\r' < <document> | grep '' | sed -e '/^ \{0,3\}```/,/^ \{0,3\}```/b' -e '/^ \{0,3\}~~~/,/^ \{0,3\}~~~/b' -e '/^- \*\*Status:\*\*/d' -e 's/^\([[:space:]]*\)- \[[xX]\]/\1- [ ]/' | git hash-object --stdin
```

## Gate record check

A spec's record is `docs/superpowers/gates/<spec file name>`; a plan's is
`docs/superpowers/gates/plans/<plan file name>`. Report the first reason
that applies, followed by the record's path:

- `missing:` the record file does not exist.
- `not passed:` a spec record's `- **Verdict:**` is not `pass`; a plan
  record's is neither `pass` nor `pass-with-decisions`.
- `stale:` a spec record's `- **Spec SHA-256:** lite-git:<id>` is absent
  or differs from the spec's current lite id; or a plan record's
  `- **Plan SHA-256:** lite-git:<id>` differs from the plan's current id,
  or its `- **Spec SHA-256:** lite-git:<id>` differs from the current id
  of the spec on the plan's `**Spec:**` line (or that spec is missing).
- `decisions not approved:` a plan record at `pass-with-decisions` has no
  `- **Decisions approved:** YYYY-MM-DD` line.
- Otherwise `ok:`.

## Frozen check

Input: the spec, the plan if there is one, and a base (`origin/main`
unless the caller names another). Patterns: the backticked spans of each
`- **Frozen:**` bullet before the first `## ` heading, outside code
fences; a value starting with `none` (any case) freezes nothing. `*` and
`?` match inside one path segment, `**/` matches any number of folders,
and a pattern ending in `/` freezes everything under it. No pattern:
report `frozen: none declared`.

Let `<mb>` be `git merge-base <base> HEAD`. For each path from
`git diff --name-only <mb> HEAD` that a pattern matches: its snapshot is
`<mb>` when `git cat-file -e <mb>:<path>` succeeds, else the oldest
commit of `git log --format=%H <mb>..HEAD -- <path>` (the one that added
it). If a later commit in `<mb>..HEAD` carries a trailer line
`Frozen-change-approved: <path>`, the newest such commit is the snapshot.
When `git diff --quiet <snapshot> HEAD -- <path>` exits 1, report
`frozen: changed <path> since <first 7 characters of the snapshot>`.
With no changed line, report `frozen: ok (<number of matched files>
files)`. A git command that fails is an error to debug, not a result.
