# Duplicate-intent pass

Pass 4 of `audit` and Phase H of `audit-deep` follow this procedure. The
session that runs the audit always runs it itself, never a subagent, because
subagents cannot start subagents. It finds functions that do the same thing
under different names or bodies. `<repo>` is the target repo.

Names used below:

- CATALOG: the absolute path of `../../scripts/function-catalog.py`, resolved
  from this file's folder.
- SCRATCH: the `audit-scratch` folder that `rules.md` section 1 allows. Every
  scratch file this pass writes goes there.

## 1. Catalog

Run `python CATALOG <repo> -o SCRATCH/catalog.json`. It prints the entry count
`n`; each entry has `file`, `line`, `name`, `language` and `snippet`.

- A non-zero exit: write `Skipped: function-catalog.py exited <code>: <first
  stderr line>.` in place of the counts line and end this pass. The rest of the
  audit continues.
- Fewer than 20 entries: write `Skipped: <n> functions, below the 20-function
  threshold.` and end.
- More than 3,000 entries: write `Skipped: <n> functions, above the
  3,000-function limit; audit a smaller repo.` and end.

## 2. Group by domain

Run `python CATALOG <repo> --split SCRATCH/batches`. It writes
`batch-001.json`, `batch-002.json` and so on, in batches of 150 entries, and
prints the batch count. Dispatch one `general-purpose` subagent per batch, all
in one message, each with `model: haiku`. If a dispatch is refused because
that model is unavailable, dispatch that batch again with no model override.

Each prompt gives the batch path and the output path
`SCRATCH/categorized-<NNN>.json`, and asks the subagent to:

- assign every entry exactly one domain from: files-and-paths,
  strings-and-formatting, validation, errors, http-and-api, dates-and-times,
  data-transforms, storage-and-database, logging, config-and-env,
  concurrency-and-retry, cli-and-processes, ui, crypto-and-ids, git, or
  `other: <subdomain>`;
- judge by what the function does, not how it does it;
- add a one-sentence `purpose` to each entry;
- cover every entry in the batch, with no truncation;
- write the result with the Write tool as a JSON array of
  `{file, line, name, domain, purpose}` and nothing else (no snippets).

Check that each output parses and has as many entries as its batch. On a
mismatch, dispatch that batch once more. Then join the outputs back to the
catalog by `file` and `line`: catalog entries with no match in any categorized
output count as uncategorized, and categorized entries with no catalog match
are dropped. Continue with what joined. When `k` entries are uncategorized
out of `n`, write one line in the report: `Grouping gap: <k> of <n> functions
not categorized (batches: <NNN, ...>).` listing the affected batches.

## 3. Compare within domains

A domain is its exact label after trimming and lowercasing, so each distinct
`other: <subdomain>` is its own domain. Compare the domains with 3 or more
functions, largest first. A domain over 150 entries is split into chunks of at
most 150, sorted by file then line. Each domain or chunk is one compare unit.
Dispatch at most 12 units; list every unit not dispatched under "Not compared".

Dispatch one `general-purpose` subagent per unit, all in one message, with no
model override (the session's model). Each is told to read only and change
nothing. The prompt gives the repo root and the unit's entries (`file`, `line`,
`name`, `purpose`), and asks it to open each function in the repo and return
groups of functions with the same intent (the same inputs to the same result,
whatever the names or bodies). Each group has:

- the intent, in one line;
- the confidence: `HIGH` (same behaviour), `MEDIUM` (same purpose, small
  differences) or `LOW` (related, needs a closer look);
- the functions as `path:line`, each with its definition line quoted;
- how they differ;
- a recommended survivor and the reason (better tests, more callers, clearer
  name).

A unit with no group returns `none`.

## 4. Findings

Each HIGH or MEDIUM group becomes one finding in the `rules.md` format:

- Title: `Duplicate intent: <intent>`.
- **Where:** the recommended survivor's `path:line`.
- **Evidence:** the survivor's quoted definition line.
- **Confidence:** `verified` once this session has opened every function in the
  group and confirmed its definition line. Where it could not open a function,
  `inferred (from: duplicate-intent subagent)`.
- **Impact:** the other functions as `path:line`, and how they differ.
- **Fix:** "consolidate on the survivor, move callers, delete the others; first
  check the survivor's tests cover every caller's use", effort S or M.
- Severity: for a verified finding, `Medium` when the functions return or do
  different things for the same input, else `Low`. For an inferred one, follow
  the subagent's "how they differ": `Medium` when it names a different result
  for the same input, else `Low`.

LOW groups are not findings. List them in one table, `| Intent | Functions |`.

## Output

This is the content the audit puts in its duplicate-intent section, in order:

1. The counts line `<n> functions catalogued; <u> of <t> compare units
   dispatched; groups: <h> HIGH, <m> MEDIUM, <l> LOW`, or the one skip line
   from step 1 instead.
2. The `Grouping gap:` line, if any.
3. The findings.
4. The LOW table.
5. The "Not compared" list.

## 5. Clean up

Delete the scratch files this pass made. The folder itself is deleted at the
end of the audit, as `rules.md` says.
