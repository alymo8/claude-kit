# Spec index: a `--check` mode

- **Status:** draft
- **Date:** 2026-09-30

## Purpose

`plugin/scripts/spec-index.py` regenerates `docs/superpowers/README.md` and
always exits 0, so CI cannot tell when a spec was committed without the
regenerated index. A `--check` mode lets CI fail on a stale index without
writing anything.

## Scope

**In:**

- `plugin/scripts/spec-index.py`: a `--check` flag, and its module docstring
  updated to document `--check` and its exit codes.
- `tests/test_spec_index.py`: tests for it.

**Out:**

- Adding the check to CI (a separate change).
- Any change to the index format.
- Any change to the script's behaviour without `--check`.

## Design

`python spec-index.py --check [DOCS_DIR]` compares `render(docs_dir)` with the
current `README.md` (read as `utf-8`, as `write_index` reads it), and never
writes. On Windows, `README.md` may be checked out with CRLF line endings
while `render` produces LF; the check must take this into account. The cases are
evaluated in this order; the first match wins. Messages go to stdout.

1. Neither `specs/` nor `plans/` exists: print `no specs or plans` and exit 0.
2. `README.md` is missing: print `index stale: run spec-index.py` and exit 1.
3. `README.md` lacks the generated marker (`MARKER`): print
   `index is hand-written; not checked` and exit 0, matching `write_index`,
   which leaves such a file alone.
4. The texts are equal: print `index up to date` and exit 0.
5. Otherwise: print `index stale: run spec-index.py` and exit 1.

In `--check` mode an exception is not swallowed: it prints
`[claude-kit] spec-index error: <exc>` to stderr and exits 2.

Arguments: `--check` may appear in any position, and the first other argument
is `DOCS_DIR`. With `--check`, any other argument starting with `--`, or a
second positional argument, prints `usage: spec-index.py [--check] [DOCS_DIR]`
to stderr and exits 2. Without `--check`, argument handling and everything
else stay exactly as today, including the catch-all that always exits 0 (the
Stop hook relies on it).

## Decisions

- **Exit 1 on a stale index, with no diff printed.** CI needs a status, and
  the fix is always to run the script, so a diff adds noise.
- **A hand-written README passes.** `write_index` never overwrites one, so
  failing on it would demand a change the script cannot make.
- **Errors fail loudly only in `--check` mode.** CI must not pass on an error;
  the hook path keeps its never-block contract.

## Success criteria

1. `pytest tests/test_spec_index.py` passes with new tests, each asserting the
   exit code and the printed message: an up-to-date index exits 0, an edited
   spec title exits 1, a missing `README.md` exits 1, a hand-written
   `README.md` exits 0, no `specs/` or `plans/` exits 0, a spec
   file that is not valid UTF-8 exits 2, and
   `--check --bogus` exits 2.
2. A test asserts that `--check` leaves `README.md` byte-identical.
3. All existing tests in `tests/test_spec_index.py` pass unchanged.
