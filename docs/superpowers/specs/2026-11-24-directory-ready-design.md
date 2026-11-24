# Directory-ready plugin, a sibling default for `/new-project`, and a `git mv` plan check

- **Status:** approved
- **Date:** 2026-11-24

## Purpose

ADR 0052 published the kit as the `agent-kit` plugin through this repo's own
marketplace. People can install it only if they already know the repo name.
This change covers three pieces of follow-up work in one PR.

1. **Directory readiness.** Anthropic's plugin directory is the only official
   listing. It is managed at `claude.ai/directory/manage`, and one listing
   reaches claude.ai, Cowork and Claude Code. The `claude-plugins-official`
   marketplace takes no public submissions. The submission itself needs the
   user's paid plan, a contact email and four compliance acknowledgements, so
   the user submits it. This change makes the repo pass the directory's
   pre-submission checklist and writes the portal steps down.
2. **`/new-project` for marketplace users** (ADR 0052, spec D9 follow-up).
   With no kit checkout around, `scaffold.py` falls back to the current
   folder. Run from inside some other git repo, it nests the new project
   inside that repo.
3. **A plan check for `git mv`** (#70 follow-up, recorded in
   `knowledge/kit-dev-gotchas.md`). A plan task that runs `git mv <src> <dst>`
   and then lists `<src>` in its `git add` step stops git on the missing
   pathspec. The commit then holds only the renames. `spec-lint.py` should
   catch this before a plan runs.

Anti-goal: a directory submission that blocks or gets held because of
something the repo could have fixed. Also: a `/new-project` default that
writes into a repo the user did not choose.

### What the directory checks (official docs, checked 2026-11-24)

- `code.claude.com/docs/en/plugins/publish.md`,
  `claude.com/docs/plugins/submit.md`,
  `claude.com/docs/plugins/pre-submission-checklist.md`.
- Source: a public github.com repo, a plugin path (`plugin` here) and a
  tracked branch or tag. Each commit is scanned, then a reviewer publishes the
  version.
- Name: kebab-case and permanent. It must not contain the reserved words
  `claude`, `anthropic`, `official`, `plugin`, `mcp` or `test`.
- Missing `description`, `author` or `version` gives warnings. `homepage`
  must parse as a URL. A licence is required, as a `LICENSE` file or a
  `license` field.
- README: at least 40 words, and it should describe everything the plugin
  runs or fetches. Undisclosed behaviour is flagged.
- No symlinks, submodules, LFS pointers, `.DS_Store` or `Thumbs.db`. Files
  are under 5 MiB, with at most 512 files.
- Hooks: only documented events and types. Command paths are written as
  `${CLAUDE_PLUGIN_ROOT}/...` with no other variables, no wildcards and no
  inline `python3 -c`. `hooks/hooks.json` should not also be listed in
  `plugin.json`.
- `claude plugin validate <path> --strict` checks the manifest locally. It
  does not check the README, the licence or whether the name is free.

## Scope

**In:**

- `plugin/README.md` (new): what the plugin is, how to install it, and what every hook and script runs, reads, writes and fetches.
- `plugin/.claude-plugin/plugin.json`: `homepage`, `repository`, `keywords`, version 1.2.0.
- `docs/directory-submission.md` (new): the portal steps, with drafted listing and data-handling answers.
- `plugin/scripts/scaffold.py`: `default_parent` adds the sibling rule.
- `plugin/commands/new-project.md`: the default-parent sentence.
- `plugin/scripts/spec-lint.py`: plan check P11.
- `plugin/hooks/hooks.json`: the Stop hook command drops its `${CLAUDE_PROJECT_DIR}` argument.
- `plugin/scripts/spec-index.py`: with no argument, reads the project folder from `CLAUDE_PROJECT_DIR`.
- `knowledge/kit-dev-gotchas.md`: the `git mv` gotcha says P11 now catches it.
- `knowledge/decisions/0055-directory-listing.md` (new), `knowledge/decisions/README.md`: ADR.
- `tests/test_directory_ready.py` (new), `tests/test_plugin_manifest.py`, `tests/test_scaffold.py`, `tests/test_spec_lint.py`, `tests/test_spec_index.py`, `tests/test_run_hooks.py`.

**Out:**

- Submitting in the portal, filling in the contact email and compliance
  acknowledgements, and any later portal edits (the user does these).
- A README Install line for the directory route. It is added once the
  listing is live, as a separate change.
- Shortening `plugin.json`'s `description`. Tests pin phrases in it, and
  the listing text is typed into the portal.
- Getting into `claude-plugins-official` or `claude-community`. Neither
  documents a public route in.
- Third-party directories.

## Design

1. **`plugin/README.md`.** This is the README the directory reads for the
   plugin path. It has at least 40 words and is plain Markdown, in this order:
   - one paragraph on what the kit is and who it is for;
   - **Install:** the marketplace commands from the repo README, plus the
     contributor note from `docs/setup.md`: a contributor who also installs
     from the marketplace reruns `python plugin/install.py` so only one copy
     loads;
   - **What runs automatically:** one row per hook in
     `plugin/hooks/hooks.json`, giving the event, the script file name, and
     what the script reads, writes and prints. The rows are written from the
     scripts themselves, not from memory;
   - **Commands and scripts:** what `/ship`, `/ship-many`, `/ship-fast` and
     the gates run (`git`, `gh`, `python`, subagents), and that they push
     branches and open, and for `/ship` merge, pull requests;
   - **Network:** hooks open no network connection. A line then names each
     script under `plugin/scripts/` that does (found by reading each one,
     for example `vendor-superpowers.py`), and each command that calls
     `gh`. No telemetry, nothing sent elsewhere;
   - **Licence:** MIT, linking the repo `LICENSE`.
2. **`plugin.json`.** Adds `"homepage": "https://github.com/alymo8/claude-kit"`,
   `"repository": "https://github.com/alymo8/claude-kit"` and `keywords`
   (`spec-driven`, `workflow`, `specs`, `code-review`, `git-worktrees`,
   `conventions`). The version becomes `1.2.0`. `name`, `author`, `license`
   and `description` stay as they are.
3. **`tests/test_directory_ready.py`.** The pre-submission checklist as
   tests. They run on `git ls-files plugin`, so untracked and ignored files
   (like `__pycache__`) do not count. They check:
   - no tracked entry under `plugin/` has mode `120000` (symlink) or
     `160000` (submodule), and none is named `.DS_Store` or `Thumbs.db`;
   - every tracked file under `plugin/` is under 5 MiB, and there are at
     most 512 of them;
   - no tracked file under `plugin/` starts with the LFS pointer line
     `version https://git-lfs.github.com/spec/v1`;
   - `plugin/README.md` has at least 40 words and names every script file
     referenced in `hooks.json`;
   - `plugin.json` has a `license`, `description`, `author` and `version`;
     its `homepage` parses with `urllib.parse` to an `https` URL with a host;
     its `name` is kebab-case and contains none of the reserved words;
     it has no `hooks` key;
   - every `command` in `hooks.json` matches
     `^python3? "\$\{CLAUDE_PLUGIN_ROOT\}/(hooks|scripts)/[a-z_-]+\.py"( --[a-z-]+( [A-Za-z]+)?)*$`.
     That means only the plugin-root variable, no other variable, no `-c`
     and no wildcard. A test case asserts that the old Stop command (with
     `"${CLAUDE_PROJECT_DIR}/docs/superpowers"`) fails the pattern. If any
     other current command does not fit, that is a build stop: the builder
     reports it rather than widening the pattern.
4. **`docs/directory-submission.md`.** A step-by-step guide for the owner:
   - before you start: a paid claude.ai plan; run
     `claude plugin validate ./plugin --strict` and `pytest tests/test_directory_ready.py`;
   - **Source:** repo `alymo8/claude-kit`, plugin path `plugin`, tracked
     branch `main`;
   - **Validate:** what to do with a warning or a hold;
   - **Listing details:** a drafted one-line summary, a short description
     and the keywords;
   - **Data handling:** drafted answers based on `plugin/README.md`'s
     Network section;
   - **Compliance:** the contact email and acknowledgements are the user's;
     the guide does not fill them in;
   - **After publishing:** each version bump on `main` gets scanned and
     reviewed again; add the directory route to the README Install section.
   It holds no personal data.
5. **`/new-project` default parent.** `default_parent(cwd)` in
   `plugin/scripts/scaffold.py` checks these in order:
   1. the main checkout of the kit checkout that contains `cwd` (unchanged);
   2. the main checkout of the kit checkout the plugin runs from
      (unchanged);
   3. **new:** if `cwd` is inside a git repo (`git -C cwd rev-parse --show-toplevel`
      succeeds), the parent folder of that repo's main checkout (from
      `main_checkout`). So a project made from `/a/repo/sub`, or from a
      worktree `/a/repo/.worktrees/w`, lands in `/a`. If that main checkout
      has no parent folder (a drive or filesystem root), `scaffold.py` exits
      2 with `cannot pick a folder next to <repo>; pass --parent <dir>`;
   4. `cwd` (unchanged).
   Rules 1 to 3 never return the plugin cache or a worktree.
   `plugin/commands/new-project.md`'s sentence becomes: "...else, inside
   another git repo, the folder that holds that repo (never inside it), else
   the current folder...".
6. **P11 in `spec-lint.py`.** The plan check is named `P11-git-mv-add`
   (`P10-depends` exists). For
   each task (`task_spans`), across its fenced code lines and inline
   backtick spans:
   - it finds every `git mv` command, tokenised with `shlex.split` (posix).
     Flags are tokens starting with `-`. The sources are the non-flag
     arguments except the last (`git mv -f a b` has source `a`);
   - it finds every `git add` command that comes after a `git mv` in the
     same task (a `git add` before it is not checked). If a non-flag
     argument equals a source (after removing a trailing `/` from both), it
     reports
     `` `git add` names `<src>`, which `git mv` moved; add the new path with `git add -A <dst> ...` ``
     on the `git add` line;
   - a line that `shlex` cannot split is skipped;
   - commands joined with `&&` or `;` on one line are split before checking.
   The module docstring lists P11 after P10-depends. The gotcha bullet in
   `knowledge/kit-dev-gotchas.md` gains "spec-lint P11 flags this".
7. **ADR 0055** (`knowledge/decisions/0055-directory-listing.md`, MADR
   format like 0054) records two things. First, the kit targets Anthropic's
   directory; the owner submits in the portal and the repo keeps a
   checklist test. Second, `/new-project` inside a foreign repo defaults to
   a sibling folder. The index in `knowledge/decisions/README.md` gains the
   row. ADR 0052 is extended in both places: its index row's status becomes
   `accepted; extended by 0054, 0055`, and the Status line in
   `0052-published-plugin.md` keeps its 0054 parenthetical and adds
   `, 0055 ([ADR 0055](0055-directory-listing.md): directory listing and the
   /new-project sibling default)`.
8. **Version.** `plugin.json` becomes `1.2.0`, and
   `tests/test_plugin_manifest.py`'s exact-version test asserts `1.2.0`. The
   parallel hook-quoting change moves it to `1.1.1`. Whichever PR merges
   second rebases this one test and keeps `1.2.0`.
9. **Stop hook.** Today it is
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py" "${CLAUDE_PROJECT_DIR}/docs/superpowers"`,
   a second variable the directory flags. It becomes
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py"`. With no
   argument, `spec-index.py` uses `$CLAUDE_PROJECT_DIR/docs/superpowers`
   when that environment variable is set and not empty, else
   `<cwd>/docs/superpowers` as today. An explicit argument still wins.
   Claude Code sets `CLAUDE_PROJECT_DIR` for hooks, and
   `plugin/hooks/run.py` (Vibe, Codex, Cursor) already sets it in the
   hook's environment, so every agent gets the same folder.

## Decisions

- **D1 (prepare, the owner submits):** the repo is made checklist-clean and
  the portal steps are written down; the user submits. Decided by the user.
  Rejected: a guide only, with no repo changes.
- **D2 (sibling of the enclosing repo):** inside a foreign git repo,
  `/new-project` defaults to the folder that holds that repo's main checkout.
  Decided by the user. Rejected: stopping to ask for `--parent`.
- **D3 (one spec, one PR):** decided by the user, knowing the three parts
  share no code and could ship apart. Rejected: three specs through
  `/ship-many` (more overhead for three small changes).
- **D4 (version 1.2.0):** a minor bump for the new check and the changed
  default. Builder's call.
- **D5 (checklist as a test):** the directory checklist lives in
  `tests/test_directory_ready.py` and runs in CI, not as a separate script.
  Builder's call: CI catches a regression before the next version is
  scanned.
- **D6 (ADR 0055):** the directory route and the `/new-project` default
  change product boundaries, so they get an ADR. Builder's call.
- **D7 (nothing frozen):** every test named below is new or gains cases for
  this change. Builder's call.
- **D8 (Stop hook reads the environment):** the Stop hook drops its
  `${CLAUDE_PROJECT_DIR}` argument and `spec-index.py` reads the variable
  itself, so every hook command uses only `${CLAUDE_PLUGIN_ROOT}`. Builder's
  call under D1 (fix what the directory would flag). Rejected: keeping the
  argument as a known warning.

## Success criteria

Agreed with the user before the build:

1. **Tests** (`pytest`):
   - `tests/test_directory_ready.py` passes on the branch. Each of its
     checks fails when its condition is broken, which is shown by
     parametrized cases on a temporary copy or on fixture data, not on the
     real tree;
   - `tests/test_scaffold.py` gains cases on temporary git repos for:
     inside a foreign repo, giving the repo's parent; inside a foreign
     repo's worktree, giving the main checkout's parent; outside any repo,
     giving `cwd`; in a kit checkout, unchanged; and the root-repo case
     exiting 2 (monkeypatched, since a real drive-root repo is not built);
   - `tests/test_spec_lint.py` gains P11 cases: a flagged `git add <src>`
     after `git mv <src> <dst>`; no flag for `git add -A <dst>`; a flag
     when the source and the `git add` argument differ only by a trailing
     `/` (`git mv dir/ new` then `git add dir`); `git mv -f a b` then
     `git add a` flagged; a `&&`-joined line; `git add <src>` before the
     `git mv`, not flagged; `git mv` in one task and `git add` in another,
     not flagged; and a line `shlex` cannot split, skipped;
   - `tests/test_spec_index.py` gains cases: no argument with
     `CLAUDE_PROJECT_DIR` set uses that folder; with it unset or empty, the
     cwd as today; an explicit argument wins over the variable;
   - `tests/test_run_hooks.py` still passes with the new Stop command, and
     the Stop hook run through `run.py` writes the index in the project
     folder;
   - `tests/test_plugin_manifest.py` asserts version `1.2.0` and the
     `homepage` and `repository` values.
2. **Validation:** `claude plugin validate ./plugin --strict` and
   `claude plugin validate .` both exit 0 on the branch.
3. **No new false alarms:** running `python plugin/scripts/spec-lint.py` on
   every plan under `docs/superpowers/plans/` gives no `P11-git-mv-add`
   finding, except on a plan checked by hand to have a `git mv` source named
   in a later `git add` of the same task. Each such plan is listed in the PR
   body with that line as evidence, and is not edited.
4. **Unchanged elsewhere:** the full suite passes, and
   `ruff check plugin tests` and `ruff format --check plugin tests` are
   clean.
5. **Post-merge (user, not gating the merge):** the portal's Validate step
   on `main` shows no blocking issue. Any warning it shows becomes a
   follow-up.
