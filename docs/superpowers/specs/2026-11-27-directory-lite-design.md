# A Markdown-only `agent-kit-lite` plugin for Anthropic's plugin directory

- **Status:** approved
- **Date:** 2026-11-27
- **Frozen:** tests/test_lite_build.py

## Purpose

ADR 0055 made `plugin/` pass the directory's pre-submission checklist. The
portal's Validate step on `main @ b0d0a63` (2026-11-27) then gave 2 blocking
issues, 5 refusals and 3 warnings. The two blocking ones cannot be fixed
inside `plugin/` and cannot be appealed:

- The directory accepts hooks of any type only from Verified organizations.
  This account's organization is not Verified.
- From an unverified organization it accepts only Markdown, text, JSON, YAML
  and PNG/JPEG/GIF/WebP/ICO files. It refuses anything starting with `#!`,
  package manifests, `CLAUDE.md` and `AGENTS.md` (any case), `.claude/skills`
  style folders and similar files. Scripts must be removed, not renamed. A
  licence and a readme may stay.

`plugin/` has 22 hook commands and 36 Python files, and most of its 13
skills and 10 commands call a script. So a directory listing needs a second
plugin made only of allowed files. The user chose (2026-11-27): a lite
plugin kept in this repo and generated from `plugin/`, named
`agent-kit-lite`. The full `agent-kit` stays on this repo's own marketplace,
unchanged for its users.

The other portal findings, read against `plugin/`:

- A name close to the publisher "Talentkit" (refused, appealable). A
  different name is expected to clear it; Success criterion 6 confirms, and
  an appeal is the fallback.
- No icon: a square PNG or JPEG, 512 to 2048 px per side, under 2 MB, at
  `.claude-plugin/icon.png` or named by `icon` in `plugin.json`. The portal
  takes the icon only the first time the plugin is saved or submitted.
- A YAML value that must be double-quoted (a `#` or `: ` inside an unquoted
  frontmatter value).
- A file pointed at outside the plugin's folder; a value read from the user's
  machine instead of `userConfig`; text that downloads code (CI templates,
  install commands in docs); hook commands that should split interpreter and
  arguments. All of these sit in files the lite plugin does not ship, or in
  text the lite build removes or the source rewords.

Goal: the `lite` folder passes the portal's Validate with 0 blocking issues
and 0 refusals, and stays that way as the kit changes, because `lite/` is a
build output that CI checks. Anti-goals: two hand-kept copies of the kit
that drift apart; any change in behaviour for `agent-kit` users; a lite
plugin whose shipped text tells Claude to run one of the kit's scripts, rely
on a Claude Code hook, or call an `agent-kit-lite` skill it does not ship.

## Scope

**In:**

- `scripts/build-lite.py` (new): the build. Run from the repo root, it
  rewrites `lite/` from `plugin/`. Not shipped in either plugin.
- `lite/` (new): the generated plugin, committed, so the directory can read
  it from `main`. It holds the generated manifest, icon, README, licence,
  conventions, skills, commands and references, all new.
- `plugin/references/spec-lint-checks.md` (new): the spec and plan lint
  rules as a checklist Claude applies by reading.
- `scripts/lite-README.md` (new): the source of `lite/README.md`, next to
  the build that reads it (not under `plugin/references/`, where
  `test_every_reference_file_is_read_by_a_command` requires a command to
  read every file).
- `scripts/lite-icon.png` (new): the icon source, drafted by the agent
  and approved by the user before the PR.
- Marker blocks (Design: Full-only and lite-only text) in the kept sources
  that mention a script, a hook, the kit map or an excluded command:
  `plugin/rules.md`, `plugin/commands/ship.md`, `plugin/commands/ship-fast.md`,
  `plugin/commands/handoff.md`, `plugin/skills/spec-gate/SKILL.md`,
  `plugin/skills/plan-gate/SKILL.md`, `plugin/skills/grill/SKILL.md`,
  `plugin/skills/grill/coverage.md`, `plugin/skills/review/SKILL.md`,
  `plugin/skills/present/SKILL.md`, `plugin/skills/pr-review-respond/SKILL.md`,
  `plugin/skills/audit/SKILL.md`, `plugin/skills/audit/rules.md`,
  `plugin/skills/capture-learnings/SKILL.md`,
  `plugin/skills/lean-context/SKILL.md`, and the references `/ship` and
  `/ship-fast` name: `plugin/references/ship-finish.md`,
  `plugin/references/pr-body.md`, `plugin/references/ship-fast-finish.md`,
  `plugin/references/ship-fast-cleanup.md`,
  `plugin/references/ship-fast-resume.md`,
  `plugin/references/ship-fast-spec.md`, and the kept sources that already
  hold flagged strings: `plugin/conventions/session-hygiene.md`,
  `plugin/conventions/spec-driven-development.md`,
  `plugin/conventions/engineering-practices.md`,
  `plugin/skills/spec-gate/rubric.md`, `plugin/skills/audit/duplicates.md`.
  The plan may add any other kept source the build's checks flag.
- `.claude-plugin/marketplace.json`: list `agent-kit-lite` (source `./lite`)
  next to `agent-kit`.
- `tests/test_publish.py`: `test_marketplace_fields` unpacks exactly one
  plugin today. It changes to look up the `agent-kit` entry by name (same
  assertions) and to assert an `agent-kit-lite` entry with source `./lite`.
- `.gitignore`: the root file ignores `/*` and whitelists folders; add
  whitelist lines for the new `lite` and `scripts` folders (new).
- `AGENTS.md` (Developing the kit): one line, "after editing `plugin/` or
  bumping its version, rerun `python scripts/build-lite.py` and commit
  `lite/`", and `scripts` added to its two ruff commands.
- `tests/test_lite_build.py` (new): the lite checks (Success criteria 2).
- `.github/workflows/ci.yml`: add `scripts` to both ruff steps.
- `docs/directory-submission.md`: submit plugin path `lite`, name
  `agent-kit-lite`; listing text for the lite scope; the icon note.
- `README.md`: a short "Two plugins" note (full kit on this marketplace,
  lite in the directory once listed).
- `knowledge/decisions/0058-directory-lite-plugin.md` (new) and its row in
  `knowledge/decisions/README.md`; `knowledge/decisions/0055-directory-listing.md`
  stays `accepted` and gains a "See ADR 0058" line: its decisions (a
  checklist-clean repo, the sibling default, the Stop hook) all still hold
  for `plugin/`; ADR 0058 adds the lite plugin and changes only which path
  is submitted, so nothing in 0055 is replaced.

**Out:**

- Getting the organization Verified, or reworking `plugin/` hooks for a
  Verified listing.
- Changing what `agent-kit` does. Full-only text is kept as it is, and
  every lite-only block opens with a line telling `agent-kit` to ignore it
  (Success criterion 5 checks this).
- The skills and commands left out of the lite plugin (D3): `/ship-many`,
  `/new-project`, `/adopt-conventions`, `/spec-html`, `/statusline`,
  `/docker-compact`, `/archive-session`, `parallel-tasks`, `supabase-cli`,
  `audit-deep`, the `audit --user` mode, and every hook.
- The portal submission itself, the contact email and the compliance
  acknowledgements (the user's, ADR 0055 D1).
- Appeals in the portal.
- The Vibe installer and the `agent-skills/` mirror: they do not ship in
  `lite/`.

## Design

### Build

`python scripts/build-lite.py` deletes `lite/` and writes it again from an
allowlist kept at the top of the script:

- `conventions/*.md`.
- Skills, as whole folders: `capture-learnings`, `lean-context`, `teach`,
  `grill`, `spec-gate`, `plan-gate`, `review`, `present`,
  `pr-review-respond`, `audit`. From `audit` it leaves out `user-mode.md`
  (the `--user` mode is not in lite).
- Commands: `ship.md`, `ship-fast.md`, `handoff.md`.
- `references/spec-lint-checks.md`, plus every `references/*.md` that a kept
  file names by path, as a Markdown link or a backticked path. The build
  follows these names transitively.
- Generated files: `lite/.claude-plugin/plugin.json`, `lite/README.md`
  (from `scripts/lite-README.md`), `lite/LICENSE` (copied from the
  repo licence), `lite/.claude-plugin/icon.png` (from
  `scripts/lite-icon.png`), and
  `lite/skills/workspace-rules/SKILL.md` (see Rules as a skill).

File rules inside a copied folder:

- Kept as they are: `.md`, `.txt`, `.json`, `.yaml`, `.yml`, `.png`, and a
  file named exactly `LICENSE` (the portal lets a licence stay; this keeps
  `skills/teach/LICENSE`, the third-party MIT notice that must travel with
  that skill's content).
- `.html` files are renamed to `<name>.html.txt` (only
  `skills/present/template.html` today). The `present` lite-only text names
  the `.txt` file and says to copy it to the deck's `.html` path.
- Everything else is dropped, and so is any kept-type file that starts with
  `#!`.

The README and icon sources sit in `scripts/`, outside `plugin/`, so
`agent-kit` is unchanged.

The build is deterministic: same input, same output, LF line endings,
sorted traversal. It takes no arguments except `--check`, which builds into
a temporary folder and exits 1 with a list of differences if it does not
match `lite/` (used by the test). `--check` compares text files with CRLF
normalised to LF and binary files (the icon) as bytes, because Windows
checkouts with `core.autocrlf=true` put `lite/` on disk with CRLF; this
follows `plugin/scripts/agent-skills.py --check`. It also exits 1, naming file and
line, when the built text breaks a rule in "Checks on the built text".

`lite/.claude-plugin/plugin.json` carries: `name: agent-kit-lite`, the same
`version` as `plugin/.claude-plugin/plugin.json`, `description` (lite scope,
one sentence), `author`, `homepage`, `repository`, `license: MIT`,
and `keywords`. It sets no `icon` field: the portal reads the default path
`.claude-plugin/icon.png`.

### Full-only and lite-only text

Sources mark text that differs between the plugins with HTML comments, which
rendered Markdown hides:

- `<!-- full-only -->` … `<!-- /full-only -->`: kept in `plugin/`, removed
  from `lite/` with its markers.
- `<!-- lite-only (agent-kit-lite only; agent-kit ignores this block)` …
  `-->`: a comment in `plugin/`; in `lite/` the build replaces the comment
  with its inner text. Claude reads skills as raw Markdown, so the opener
  must be exactly this string: it tells an `agent-kit` session the block
  does not apply. The build rejects any other `lite-only` opener.

Markers may not nest, and each opener must be closed in the same file; the
build exits 1 otherwise. Lite text never names a script, so lite needs no
"does the script exist" test and never runs the full kit's scripts even when
both plugins are installed.

What the lite-only text says, per script or dependency:

| Where | Full kit | Lite-only text |
|-------|----------|----------------|
| `spec-gate`, `plan-gate` | `spec-lint.py` lint | apply `references/spec-lint-checks.md` by reading the document |
| `spec-gate`, `plan-gate` records | `spec-lint.py --hash` | a spec record writes `- **Spec SHA-256:** lite-git:<spec id>`; a plan record writes both `- **Plan SHA-256:** lite-git:<plan id>` and `- **Spec SHA-256:** lite-git:<id of the spec the plan names>`; ids are the lite document id below |
| `/ship` record check | `spec-lint.py --verify-record` for spec and plan | the same acceptance as `verify_record` and `verify_plan_record` in `spec-lint.py`, with ids recomputed instead of SHA-256: a spec record says `pass` and its id matches; a plan record says `pass`, or `pass-with-decisions` with the approval line `/ship` writes (ADR 0036), and both its plan id and its spec id match; otherwise rerun the gate |
| `grill`, `grill/coverage.md` | names lint rule L9 | names the L9 entry in `references/spec-lint-checks.md` |
| `review`, `/ship`, `/ship-fast`, `ship-fast-finish.md` | `frozen-check.py` | list the `Frozen` paths from the spec and confirm with `git diff --name-only <base>...HEAD` that none changed |
| `/ship`, `/ship-fast` | `parallel-plan.py` and `parallel-tasks` | run plan tasks one at a time, in order |
| `/ship-fast`, `ship-fast-spec.md` | `scaffold.py` | skip scaffolding; work in the current repo, and tell the user that project scaffolding needs the full kit |
| `ship-finish.md`, `ship-fast-cleanup.md` | `spec-index.py` | skip; say in the report that the spec index is not updated |
| `ship-finish.md`, `ship-fast-cleanup.md` | `docker-disk.py` status line | skip |
| `/handoff` | `handoff.py` | write `.claude/handoffs/<branch>.md` from the section list in `handoff.md`, then tell the user to start the next session with "read `.claude/handoffs/<branch>.md` and continue" (no hook loads it) |
| `present` | `check-deck.py` | check the deck against the same rules by reading it |
| `pr-review-respond` | `review-threads.py` | fetch threads with one `gh api graphql` query printed in the lite text |
| `audit`, `audit/rules.md` | `check-findings.py`, `function-catalog.py` | open each cited file and line by hand; skip the duplicate-intent pass and say so |
| any kept file | `<plugin root>` from the kit map, else `~/.claude/skills/agent-kit` | the plugin root is the folder that holds this plugin's `conventions/`: two levels above a skill's folder (`skills/<name>/`), one level above `commands/`; playbooks are `conventions/<file>.md` under it |
| `rules.md` | `render-spec.py`, `/spec-html`, `/ship-many`, the kit map, the grill hook, the session-start worktree report | full-only; lite keeps the rule that specs and plans are never opened unless asked, without the rendering commands |

The plan settles the exact wording of each block.

**L9 in lite.** Lite has no grill switch. In lite, L9-coverage applies only
when the spec has a `## Coverage` section; then each area bullet is checked
as in the full kit. `spec-lint-checks.md` states this in a lite-only block
with no variable name, and the Coverage text in
`conventions/spec-driven-development.md` takes a matching lite-only block.

**Lite document id.** The full kit's hash leaves out the Status line (and,
for plans, what `plan_hash` in `spec-lint.py` leaves out), so `/ship` can
set Status to `approved` and tick boxes without staling the record. Lite
gets the same property with no script: the id is the output of `git
hash-object --stdin` fed the document with the same lines removed and
normalised, using only `grep`/`sed` (the plan writes the exact pipeline from
`spec_hash` and `plan_hash`, and `spec-lint-checks.md` prints it). It works
on untracked and uncommitted files. The test runs that pipeline on two
fixtures (a spec and a plan) and checks that changing only Status or a tick
leaves the id unchanged and changing any other line changes it.

### Skill names

Kept sources call skills as `agent-kit:<name>`. The build rewrites every
`agent-kit:` in shipped text to `agent-kit-lite:`, and the lite-only text
names only skills lite ships. `agent-kit:<excluded skill>` references sit in
full-only blocks.

### Rules as a skill

A plugin cannot ship `CLAUDE.md`, and without hooks nothing injects the
workspace rules. The build writes `lite/skills/workspace-rules/SKILL.md`: a
frontmatter header kept in `build-lite.py` followed by the built text of
`plugin/rules.md` (markers applied), so it never drifts and `agent-kit`
gains no new skill. The frontmatter description makes Claude load it for
feature work, specs, plans, worktrees and shipping. `lite/README.md` also
tells users they can make the rules always-on by importing the installed
skill's file from their own `CLAUDE.md` (no path outside the plugin is
written in any shipped file).

`rules.md` sits at the plugin root and links `](conventions/...)`. When
the build writes it two folders deeper, it rewrites those links (and
backticked `conventions/` paths) to `../../conventions/...`. Links to ADRs
are absolute GitHub URLs already. Every relative Markdown link in `lite/`
must resolve to a file in `lite/` (a test assertion).

### Checks on the built text

The build and the test both fail on any of these in `lite/`:

- A line the portal refuses from unverified publishers: `curl `, `wget `,
  `Invoke-WebRequest`, `pip install`, `npm i`, `npm install`,
  `pnpm install`, `npx`, `uvx`, `pipx`, `bunx`; or `$VAR`, `${VAR}`,
  `%VAR%`, `$env:` for any variable other than `CLAUDE_PLUGIN_ROOT` and
  `ARGUMENTS`. Known sources today: `plugin/rules.md` (`pip install`, made
  full-only), `plugin/skills/audit/rules.md` (`$TMPDIR`, `%TEMP%`),
  `plugin/skills/lean-context/SKILL.md` (`$SCRATCH`), and the `grill`
  frontmatter (`CLAUDE_KIT_GRILL`, fixed by the description override in
  Frontmatter). Otherwise fix in the source:
  move to a full-only block, or reword with the full plugin's meaning kept.
- A mention of the kit's own code, matched as plain substrings: the file
  name of any file under `plugin/scripts/` or `plugin/hooks/` (case
  sensitive, read from those folders at build time so the list stays
  current), `<plugin root>/scripts/`, `${CLAUDE_PLUGIN_ROOT}/scripts/`,
  `hooks.json`, `CLAUDE_KIT_GRILL`, and `kit map` (case insensitive).
  Nothing else: hook event names, generic paths such as `tests/x.py`, and
  git or pre-commit hooks in a user's project are allowed. Text that leans
  on a kit hook without naming one of these is handled by the marker edits
  and the reviewer, not this check.
- `agent-kit:` not followed by `-lite`, or `agent-kit-lite:<name>` where
  `<name>` is neither a folder in `lite/skills/` nor a file
  `lite/commands/<name>.md`.
- An unclosed or nested marker, or a marker left in the output.
- A slash command lite does not ship, written as `/<name>` for any name in
  the D3 Out list (`/ship-many`, `/new-project`, `/adopt-conventions`,
  `/spec-html`, `/statusline`, `/docker-compact`, `/archive-session`,
  `/audit-deep`), with or without a plugin prefix.
- A path that starts with `~/` or `%USERPROFILE%`.

### Frontmatter

Every `SKILL.md` and command frontmatter in `lite/` must parse as YAML in
which each string value that holds `#` or `: ` is double-quoted. Markers
cannot sit inside frontmatter, so the build changes frontmatter in one way
only: `build-lite.py` holds a table of lite `description` overrides keyed
by skill or command name, and replaces that file's `description` value with
the override. The table has three entries:

- `grill`: the source names `CLAUDE_KIT_GRILL=1` and the hook-injected rule,
  which lite lacks; the lite description triggers only when the user asks
  to be grilled on a plan, design or idea.
- `audit`: the source mentions `/audit-deep`, `--user` and a path under
  `~/.claude/`; the lite description keeps only the one-pass repository and
  setup audit.
- the `ship-fast` command: the source says independent tasks run in
  parallel; the lite description says tasks run one at a time.

The overrides leave `agent-kit`'s frontmatter unchanged. Any other
frontmatter problem (such as quoting) is fixed in the source without
changing its meaning, and the test enforces both.

### Icon

The agent draws a simple square 1024 x 1024 PNG with no embedded metadata
(no text chunks beyond the image) and shows it to the user. It is committed
only after the user approves it in chat. The portal takes it only once, so
the PR description says that the icon is final once the user first saves
the plugin in the portal.

## Decisions

- **D1 (user, 2026-11-27): a lite plugin for the directory.** Rejected:
  getting Verified first; not listing; submitting as-is and appealing (the
  two blocking rules are not appealable).
- **D2 (user, 2026-11-27): generated from `plugin/`, committed, checked in
  CI.** Rejected: a hand-kept `lite/` (drifts); making `plugin/` itself
  Markdown-only (splits the full kit into two installs).
- **D3 (user, 2026-11-27): scope.** 10 copied skills plus the generated
  `workspace-rules`, and `/ship`, `/ship-fast` without scaffolding,
  `/handoff`. Everything that only works with code is left out.
- **D4 (user, 2026-11-27): name `agent-kit-lite`.** Rejected: a new name
  such as `spec-ship` (harder to connect to the full kit).
- **D5 (user, 2026-11-27): the agent drafts the icon, the user approves it
  before it is committed.**
- **D6 (agent): the lite plugin carries the full kit's version number.**
  One version per release; the directory rescans each bump.
- **D7 (agent): lite differences live in `plugin/` sources as full-only and
  lite-only comment blocks that the build applies.** Lite text never names a
  script. The one exception is frontmatter, where markers cannot sit:
  `build-lite.py` keeps a table of lite `description` overrides (today only
  `grill`, `audit`, `ship-fast`), next to the `workspace-rules`
  frontmatter it already holds.
  Rejected: runtime "if the script exists" sentences (lite would run
  the full kit's scripts when both plugins are installed, and lite would
  still name scripts); lite-only edited copies (the drift D2 avoids).
- **D8 (agent): the build rewrites `agent-kit:` to `agent-kit-lite:`.**
  Rejected: unqualified skill names in the sources (ambiguous when both
  plugins are installed).
- **D9 (agent): `present`'s template ships as `template.html.txt`;
  `LICENSE` files without an extension are kept.** The portal allows `.txt`
  and a licence.
- **D10 (agent): `tests/test_lite_build.py` is frozen** once written, so
  later changes cannot weaken the directory checks to make a build pass.
- **D11 (agent): lite requires the superpowers plugin, as the full kit
  does.** The kept skills call `superpowers:*` skills; `lite-README.md`
  states the prerequisite and links to that plugin's own install page. The
  built-text checks cover `agent-kit-lite:` names only.

## Success criteria

1. `claude plugin validate ./lite --strict` exits 0.
2. `pytest tests/test_lite_build.py` passes, and it asserts that:
   `python scripts/build-lite.py --check` exits 0 (no drift), and also
   exits 0 on a copy of `lite/` whose text files (every file except the
   icon) are converted to CRLF; every file in
   `lite/` has an allowed extension or is named `LICENSE`, is UTF-8 with no
   NUL byte and does not start with `#!`; no `CLAUDE.md`, `AGENTS.md`,
   `hooks/`, `.mcp.json` or folder named exactly `.claude` exists in
   `lite/`; no shipped
   line breaks a rule in "Checks on the built text"; every frontmatter value
   with `#` or `: ` is double-quoted; `lite/.claude-plugin/icon.png` is a
   square PNG, 512 to 2048 px, under 2 MB; every rule ID in `spec-lint.py`'s
   docstring appears in `references/spec-lint-checks.md`; `lite` and
   `plugin` versions match; `lite/skills/` holds exactly the D3 skills;
   every relative Markdown link in `lite/` resolves; the lite document id
   pipeline ignores Status and tick changes and catches any other change
   (fixtures).
3. The full suite (`pytest`) and `ruff check plugin tests scripts` and
   `ruff format --check plugin tests scripts` pass. No existing test is
   changed except to add coverage, and the `test_marketplace_fields`
   change listed in Scope.
4. Manual: in an isolated config, add this repo's marketplace from a local
   path, install `agent-kit-lite` only, confirm no hook runs, then run
   `agent-kit-lite:spec-gate` on a sample spec; check that it lints by the
   checklist, runs no script and writes a record with
   `- **Spec SHA-256:** lite-git:<id>`; then set the spec's Status to
   `approved` and confirm the lite `/ship` record check still accepts it. Report the transcript excerpt.
5. Manual, full kit unchanged: with `agent-kit` (not lite) loaded, run
   `agent-kit:spec-gate` on the same sample spec; it runs `spec-lint.py`
   and writes a 64-hex `Spec SHA-256`, and `spec-lint.py --verify-record`
   prints `ok:`. Report the excerpt.
6. Manual, by the user after merge: the portal's Validate on `lite` at the
   merge commit shows 0 blocking issues and 0 refusals.
