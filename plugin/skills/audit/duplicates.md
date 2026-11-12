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

Check that each output parses and has as many entries as its batch; on a
mismatch, dispatch that batch once more.

## 3. Compare within domains

Join and split in code, never by hand (copying alters `path:line` keys); set
`S` to SCRATCH:

```python
import glob, json

S = "SCRATCH"
cat = json.load(open(S + "/catalog.json", encoding="utf-8"))
key = lambda e: (e["file"], e["line"])
byk, by, seen = {key(e): e for e in cat}, {}, set()
for p in sorted(glob.glob(S + "/categorized-*.json")):
    for c in json.load(open(p, encoding="utf-8")):
        if key(c) in byk and key(c) not in seen:
            seen.add(key(c))
            e = {x: c[x] for x in ("file", "line", "name", "purpose")}
            by.setdefault(c["domain"].strip().lower(), []).append(e)
units = []
for d in sorted((d for d in by if len(by[d]) >= 3), key=lambda d: -len(by[d])):
    es = sorted(by[d], key=key)
    units += [(d, es[i : i + 150]) for i in range(0, len(es), 150)]
for n, (d, es) in enumerate(units[:12], 1):
    with open(f"{S}/unit-{n:02d}.json", "w", encoding="utf-8") as f:
        json.dump({"domain": d, "entries": es}, f)
gap = sorted({i // 150 + 1 for i, e in enumerate(cat) if key(e) not in seen})
print(len(units), len(cat), len(cat) - len(seen), gap)  # t, n, k, batches
print([(d, len(es)) for d, es in units[12:]])  # not compared
```

Catalog entries with no categorized match are uncategorized. When `k` of `n`
are, write one report line: `Grouping gap: <k> of <n> functions not categorized
(batches: <NNN, ...>).` listing the affected batches.

A domain is its label trimmed and lowercased, so each distinct `other:
<subdomain>` is its own domain. The code keeps domains with 3 or more
functions, largest first, and splits any over 150 entries into chunks of at
most 150: each domain or chunk is one compare unit, `SCRATCH/unit-<NN>.json`.
Write at most 12; list every other unit under "Not compared".

Dispatch one `general-purpose` subagent per unit, all in one message, with no
model override (the session's model), told to read only and change nothing.
The prompt gives the repo root and the unit file's path (entries with `file`,
`line`, `name`, `purpose`), and asks it to open each function in the repo and
return groups of functions with the same intent (the same inputs to the same
result, whatever the names or bodies). Overrides, implementations of one
interface or base class, and abstract declarations are not duplicates. A unit
with no group returns `none`. Each group has:

- the intent, in one line;
- the confidence: `HIGH` (same behaviour), `MEDIUM` (same purpose, small
  differences) or `LOW` (related, needs a closer look);
- the functions as `path:line`, each with its definition line quoted;
- how they differ;
- a recommended survivor and the reason (better tests, more callers, clearer
  name).

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

In the counts line, `<t>` = compare units after chunking, `<u>` = units
dispatched (at most 12), `<h>`/`<m>`/`<l>` = groups by confidence across all
dispatched units, `<n>` = catalogued functions.

## 5. Clean up

Delete the scratch files this pass made. The folder itself is deleted at the
end of the audit, as `rules.md` says.
