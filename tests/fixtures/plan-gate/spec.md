# Spec stats command

- **Status:** approved
- **Date:** 2026-09-30

## Purpose

Show how many specs a repo has in each Status, so a user can see at a glance
what is drafted, approved or done.

## Scope

**In:**

- `plugin/scripts/spec-stats.py` (new): counts the specs in a folder per
  Status.
- `tests/test_spec_stats.py` (new): its tests.

**Out:**

- Plans; only specs are counted.
- Any change to `plugin/scripts/spec-index.py`.

## Design

`python spec-stats.py [SPECS_DIR] [--json]`, with `SPECS_DIR` defaulting to
`docs/superpowers/specs`. For each `*.md` file in the folder (not recursive),
the Status is the first word after `- **Status:**` on a line that starts with
it, lower-cased; a file with no such line counts as `unknown`. The output is
one line per Status, sorted by name, as `<status>: <count>`. With `--json` it
prints one JSON object mapping each Status to its count, keys sorted, instead.
A folder with no `*.md` files prints `no specs` and exits 0, with or without
`--json`. A missing folder prints `spec-stats: no such folder: <path>` to
stderr and exits 2. Standard library only.

## Decisions

- Count specs only, not plans: the index already lists plans.
- Text output by default; JSON behind a flag, for scripts.

## Success criteria

1. A test in `tests/test_spec_stats.py` asserts that a folder with two
   `approved` specs and one spec without a Status prints
   `approved: 2\nunknown: 1\n` and exits 0.
2. A test asserts `--json` prints `{"approved": 2, "unknown": 1}` for that
   folder.
3. A test asserts an empty folder prints `no specs` and exits 0.
4. A test asserts a missing folder exits 2.
5. `pytest` and `ruff check plugin tests` pass.
