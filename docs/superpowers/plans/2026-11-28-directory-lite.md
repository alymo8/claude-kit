# agent-kit-lite Implementation Plan

- **Status:** approved
- **Date:** 2026-11-28
- **Frozen:** `tests/test_lite_build.py`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second, Markdown-only plugin `agent-kit-lite` in `lite/`, generated from `plugin/` by `scripts/build-lite.py`, committed and drift-checked by a frozen test, so Anthropic's plugin directory accepts it from an unverified publisher.

**Architecture:** `scripts/build-lite.py` copies an allowlist of `plugin/` (conventions, 10 skills, 3 commands, the references they name) into `lite/`, applies `<!-- full-only -->` and `<!-- lite-only ... -->` comment blocks that the sources carry, rewrites `agent-kit:` to `agent-kit-lite:`, swaps three frontmatter descriptions, generates the manifest, README, licence, icon and a `workspace-rules` skill from `plugin/rules.md`, and refuses output that breaks the directory's rules. Script-backed steps get lite-only text that does the same by reading, using a new checklist `plugin/references/spec-lint-checks.md` (lint rules, a `git hash-object` document id, the gate record check and the frozen check). `agent-kit` behaviour does not change: full-only text stays, lite-only text is an HTML comment.

**Tech Stack:** Python 3.11 standard library, pytest, ruff, Markdown, Git Bash `tr`/`grep`/`sed`, `claude plugin validate`.

**Spec:** `docs/superpowers/specs/2026-11-27-directory-lite-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-27-directory-lite-design.md`

## Context for the executor

This repo is the kit; the full Claude Code plugin lives in `plugin/`. Work in
the worktree `<repo-root>/.worktrees/directory-lite` on branch
`feat/directory-lite`; never switch branches. Setup once:
`pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks:
`pytest`, `ruff check plugin tests scripts`,
`ruff format --check plugin tests scripts` (before Task 2 creates `scripts/`,
drop `scripts` from the two ruff commands). `pyproject.toml` sets
`addopts = "-q"`; run plain `pytest` for the summary line.
`tests/helpers.py` exports `PLUGIN`, `REPO`, `load_module(path, name)`,
`command_text(name)` (a command with its reference files inlined) and
`run_script`. The repo is public: never write a machine username or a
private repo name into a tracked file. Lines fit ruff's 88 characters. Edit
test files with the Edit or Write tool, never through a bash heredoc (it
turns `\n` and `\b` escapes into real bytes). Commit after each task with a
message ending in `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
Read `knowledge/kit-dev-gotchas.md` before editing `plugin/commands/ship.md`
or `plugin/commands/ship-fast.md`: their tests split steps on lines that
start at column 0 with `<digits>. ` and pin about 60 phrases.

Facts the tasks rely on:

- `plugin/.claude-plugin/plugin.json` is at version `1.2.0`; this plan does
  not bump it (the spec lists neither the manifest nor its pinned test
  `test_version_is_1_2_0`).
- `plugin/hooks/workspace_rules_inject.py` injects `plugin/rules.md`
  verbatim (HTML comments included) into `agent-kit` sessions;
  `tests/test_workspace_rules_inject.py::test_size_cap` caps it at 9,500
  characters and it injects about 8,100 today, so `rules.md` gets only
  full-only markers and one short lite-only phrase.
- `tests/test_publish.py::test_no_live_file_names_old_conventions_root`
  fails any tracked line (outside `plugin/conventions/`, `plugin/rules.md`
  and a few exempt phrases) that holds `conventions/` not preceded by a
  letter, digit, `.`, `/` or `-`. That covers lite-only text inside
  `plugin/` files and every file in `lite/`. Lite-only text therefore writes
  `<plugin root>/conventions/<file>.md` or
  `${CLAUDE_PLUGIN_ROOT}/conventions/<file>.md`, never a bare
  `conventions/...`.
- That check reads untracked, unignored files too, and covers
  `scripts/` and `tests/`: new code builds the string with
  `"conventions" + "/"` (or an f-string over `C = "conventions" + "/"`)
  wherever `conventions/` would follow `)`, `(`, `[`, a backtick, a quote
  or a space.
- `tests/test_publish.py::test_claude_kit_only_in_allowed_places` rejects
  the bare string `claude-kit` in tracked files except inside
  `alymo8/claude-kit`, `claude-kit.task` and a few others; do not write it
  in new text.
- `tests/test_skill_size.py`: every `plugin/skills/*/SKILL.md` and
  `plugin/commands/*.md` stays under 20,000 bytes; each
  `${CLAUDE_PLUGIN_ROOT}/references/<file>.md` named in one must exist, and
  the file must also hold the `FALLBACK_RULE` sentence (which `ship.md` and
  `ship-fast.md` already do); every `plugin/references/*.md` must be named as
  `references/<file>` by some skill, command or hook.
- `tests/test_publish.py::test_fallbacks_name_the_kit_map_root` fails any
  `.md` under `plugin/commands`, `plugin/skills` or `plugin/references`
  that holds `<plugin root>/` (comments included) but not the phrase "the
  plugin root stated in the kit map". So lite-only text writes
  `<plugin root>/` only in a file that already holds that phrase in its
  full-only text (spec-gate, plan-gate, review, the spec-gate rubric);
  elsewhere it writes a relative path such as
  `../../conventions/<file>.md` from the skill's directory.
- `tests/test_kit_map_inject.py` pins the string
  `the session-hygiene playbook (path in the kit map)` in
  `plugin/skills/lean-context/SKILL.md`.
- `tests/test_plugin_manifest.py::test_lean_context_skill_exists_and_is_short`
  caps `plugin/skills/lean-context/SKILL.md` at 60 lines (45 today).

## Global Constraints

- Plugin name `agent-kit-lite`; marketplace source `./lite`; lite `version` equals `plugin/.claude-plugin/plugin.json`'s `version`; lite `license` is `MIT`; lite `plugin.json` has no `icon` and no `hooks` key.
- Lite skills, exactly: `capture-learnings`, `lean-context`, `teach`, `grill`, `spec-gate`, `plan-gate`, `review`, `present`, `pr-review-respond`, `audit`, plus the generated `workspace-rules`. Lite commands, exactly: `ship.md`, `ship-fast.md`, `handoff.md`. `skills/audit/user-mode.md` is not shipped.
- Kept file types: `.md`, `.txt`, `.json`, `.yaml`, `.yml`, `.png`, and files named exactly `LICENSE`; `.html` ships as `<name>.html.txt`; anything else, and any file starting with `#!`, is dropped.
- Full-only marker: `<!-- full-only -->` … `<!-- /full-only -->`. Lite-only opener, exactly: `<!-- lite-only (agent-kit-lite only; agent-kit ignores this block)`, closed by `-->`. Each marker block either sits on its own lines (opener line and closer line hold nothing else, leading spaces allowed) or opens and closes on one line (inline). No nesting; a lite-only block holds no `<!--` and no `-->` before its closer.
- Marker lines take the indentation of the text around them and never add blank lines, so a paragraph stays one paragraph. In `plugin/commands/ship.md`, `plugin/commands/ship-fast.md` and `plugin/references/ship-*.md` (whose tests split steps on column-0 numbers), no line inside a marker block, and no marker line, starts at column 0 with `<digits>. `; elsewhere a whole numbered item may sit inside a block. No marker goes inside a fenced code block (agent-kit would copy it into a record).
- You may rewrap the lines of a paragraph so a block starts and ends at line boundaries, except where a test pins a line break (`"one\n   copy, the only one the run starts"` in `ship-fast.md` step 5). Never edit an existing test to make a marker edit pass; move the marker instead.
- Lite-only text names no kit script, no hook, no `hooks.json`, no `CLAUDE_KIT_GRILL`, never says "kit map", never writes `curl `, `wget `, `Invoke-WebRequest`, `pip install`, `npm i`, `npm install`, `pnpm install`, `npx`, `uvx`, `pipx`, `bunx`, `$NAME`, `${NAME}`, `%NAME%` or `$env:` (except `${CLAUDE_PLUGIN_ROOT}` and `$ARGUMENTS`), no `/ship-many`, `/new-project`, `/adopt-conventions`, `/spec-html`, `/statusline`, `/docker-compact`, `/archive-session`, `/audit-deep`, no path starting `~/` or `%USERPROFILE%`, no bare `conventions/`, no bare `claude-kit`.
- Lite-only text names skills as `agent-kit:<name>` like the rest of the source (the build rewrites them) and names only lite skills and commands.
- Plugin root in lite-only text: in a skill folder, `<plugin root>` is two folders above this skill's directory; in `commands/`, `${CLAUDE_PLUGIN_ROOT}`, or where it is not expanded the folder one level above the `commands/` folder that holds the command; in `references/`, the files next to this file. Playbooks are `<plugin root>/conventions/<file>.md`.

## Decisions this plan makes

- Unit tests of the build script live in a second, unfrozen file `tests/test_lite_markers.py`; the frozen `tests/test_lite_build.py` checks the built tree, so the build's internals can change without a frozen-file approval.
- Markers may be inline (open and close on one line) as well as on their own lines; a line emptied by inline removal is dropped. The build does not skip code fences.
- The lite id removes every `- **Status:**` line outside fences (the full kit removes only the first) and unticks boxes for specs and plans alike: one pipeline for both.
- Positional shell parameters (`$1`, `$@`, `$?`) and `$(` command substitution are allowed by the variable check; only `$` or `%` followed by a name counts as a variable.
- Lite `/ship-fast` never creates a repository: it ignores a `**Repo:** new` line, works in the spec's repository, and stops when the spec is not in a git repository. Its Docker baseline goes to `<git common dir>/ship-fast/<slug>.docker-baseline.txt`.
- Two phrases are reworded in both plugins so their lite copies pass the existing `conventions/` check: `plugin/skills/review/SKILL.md` and `plugin/skills/spec-gate/rubric.md` write `./conventions/...`. `plugin/skills/audit/rules.md` and `plugin/skills/lean-context/SKILL.md` drop their `$TMPDIR`, `%TEMP%` and `$SCRATCH` spellings with the meaning kept.
- `plugin/conventions/project-memory.md` joins the marker files (it names `/new-project`).
- A missing `references/<name>.md` named by a kept file fails the build. A backticked file name that the build omits (such as `user-mode.md`) is not a build check: the marker edits handle it.
- The icon is a teal square with three white bars and a white check mark, drawn by a throwaway script; Task 1 is the one step that waits for the user (spec D5).

## Review Focus

- A Windows checkout with `core.autocrlf=true` gives the build CRLF sources: the output must be byte-identical to an LF checkout. Test: `test_build_normalises_crlf_sources` (Task 2), plus the frozen CRLF check (Task 6).
- A marker indented inside a list item (`   <!-- full-only -->`) must work like a column-0 one. Test: `test_indented_markers` (Task 2).
- A lite-only block whose text holds `-->` or another comment must fail the build, not leak half a comment into `lite/`. Test: `test_comment_inside_lite_block_fails` (Task 2).
- A real edit to a gated spec must stale its lite record while a Status change or a ticked box must not. Tests: `test_lite_id_ignores_status_ticks_and_line_endings` and `test_lite_id_catches_other_changes` (Task 6).
- A `.py` file or a `#!` file added later to a lite skill folder must be dropped, not shipped. Test: `test_file_rules` (Task 2).

## Plan questions answered

| Question (spec gate record) | Answered in |
|---|---|
| `$1` and positional parameters | Task 2 (check rules), Decisions above |
| Lite GraphQL query, placeholders, pagination | Task 5 (`pr-review-respond`) |
| Portable id pipeline, fences, CR, fixtures | Task 3 (pipeline text), Task 6 (fixtures) |
| P4 in lite | Task 3 |
| Docker baseline and new-repo spec without `~/` | Task 4 (`ship-fast.md`, `ship-fast-spec.md`) |
| Size limits for `ship.md`, `ship-fast.md`, lean-context | Global Constraints; Tasks 4 and 5 keep shared procedures in `spec-lint-checks.md` |
| Link check: folder targets, `#anchor` | Task 6 (`test_relative_links_resolve_inside_lite`): folders count, anchors are stripped |
| Omitted backticked file names | Decisions above; Task 5 (`audit` User mode) |
| Lite `/handoff` State section and file name | Task 4 (`handoff.md`) |
| Lite `present` and `audit` rules | Task 5 |
| Reference discovery after markers | Task 2 (`build`) |
| PNG check with the standard library | Task 6 (`test_icon_is_a_square_png_within_limits`), Task 1 |

---

### Task 1: The lite icon (main session, waits for the user)

**Files:**
- Create: `scripts/lite-icon.png`
- Modify: `.gitignore`

**Depends on:** none

This task runs in the main session, not a subagent: it ends with a question
to the user (spec D5). Under `/ship` it is the one check-in.

- [ ] **Step 1: Draw the icon with a throwaway script**

Write `<scratchpad>/draw_icon.py` (never committed). Standard library only
(`zlib`, `struct`). Output: a 1024 x 1024 RGB PNG with exactly three chunks,
`IHDR` (bit depth 8, colour type 2), one `IDAT` (each row prefixed by filter
byte 0, compressed with `zlib.compress(raw, 9)`) and `IEND`, each with its
`zlib.crc32` CRC; no `tEXt`, `iTXt`, `zTXt`, `tIME` or `eXIf`. Picture:
background `#0F766E`; three white (`#FFFFFF`) bars, x from 200 to 640, 560
and 480, y from 260 to 330, 400 to 470 and 540 to 610; a white check mark
made of the pixels within 40 px of segment (500, 700)-(610, 810) or segment
(610, 810)-(830, 560).

Run: `python <scratchpad>/draw_icon.py <repo-root>/scripts/lite-icon.png`
Expected: the file exists, under 2 MB, and
`python -c "import struct;d=open('scripts/lite-icon.png','rb').read();print(struct.unpack('>II',d[16:24]))"`
prints `(1024, 1024)`.

- [ ] **Step 2: Show it to the user and wait**

Open it (`Invoke-Item scripts/lite-icon.png` on Windows, `open` on macOS,
`xdg-open` on Linux) and ask: "Approve this icon for agent-kit-lite? The
directory fixes it the first time you save the plugin in the portal." Wait.
On a change request, edit the script, redraw, and ask again. Do not commit
before a yes.

- [ ] **Step 3: Whitelist the new folders, then commit**

The root `.gitignore` ignores `/*`; in it, after `!/.github/`, add the two
lines `!/scripts/` and `!/lite/` (without them `git add` refuses
`scripts/`).

```bash
git add .gitignore scripts/lite-icon.png
git commit -m "Add the agent-kit-lite icon (approved)"
```

---

### Task 2: The build script and its unit tests

**Files:**
- Create: `scripts/build-lite.py`
- Test: `tests/test_lite_markers.py`

**Depends on:** none

**Interfaces:**
- Produces, in `scripts/build-lite.py` (loaded in tests with
  `load_module(REPO / "scripts" / "build-lite.py", "build_lite")`):
  - `class MarkerError(ValueError)`
  - `apply_markers(text: str, path: str) -> str`
  - `rewrite_skill_names(text: str) -> str`
  - `override_description(text: str, value: str, path: str) -> str`
  - `rules_skill(rules_text: str) -> str`
  - `check_text(rel: str, text: str, kit_names: list[str], skills: set[str], commands: set[str]) -> list[str]`
  - `build(root: Path, dest: Path) -> list[str]`
  - `check_tree(root: Path, dest: Path) -> list[str]`
  - `compare(built: Path, lite: Path) -> list[str]`
  - `main(argv: list[str] | None = None) -> int`
- Output line formats (Tasks 3 to 6 grep them): marker and source problems
  `plugin/<source path>:<line>: <message>`; built-text violations
  `<lite path>:<line>: <rule>: <detail>` with `<rule>` one of `install`,
  `variable`, `kit-code`, `skill-name`, `marker`, `command`, `home-path`;
  drift `missing: <lite path>`, `extra: <lite path>`, `differs: <lite path>`;
  success `ok`.

- [ ] **Step 1: Check the folder is tracked**

If Task 1 has not run yet, add its `.gitignore` lines (`!/scripts/` and
`!/lite/` after `!/.github/`) here and include `.gitignore` in this task's
commit.

Run: `git check-ignore -v scripts/build-lite.py`
Expected: no output (exit 1: not ignored).

- [ ] **Step 2: Write the failing unit tests in `tests/test_lite_markers.py`**

Module header: load the build module once as `bl`; `OPEN = bl.OPEN_LITE`;
`C = "conventions" + "/"`.
A helper `make_root(tmp_path) -> Path` writes a minimal fake repo:
`LICENSE`, `scripts/lite-README.md` (`# Lite\n`), `scripts/lite-icon.png`
(any bytes starting with the PNG signature),
`plugin/.claude-plugin/plugin.json` (`name`, `version` `9.9.9`, `author`,
`homepage`, `repository`, `keywords`), `plugin/rules.md` (built as
`f"# Rules\n\nSee [x]({C}a.md).\n"` with the module constant
`C = "conventions" + "/"`), `plugin/conventions/a.md`, `plugin/scripts/tool.py`,
`plugin/hooks/hook.py`, `plugin/references/spec-lint-checks.md`, the three
commands with frontmatter (`ship-fast.md` with a `description:` line), and
each of the 10 skill folders with a `SKILL.md` that has a frontmatter
`description:` line. Tests:

```python
def test_full_only_block_on_its_own_lines_is_removed():
    text = "a\n<!-- full-only -->\nb\n<!-- /full-only -->\nc\n"
    assert bl.apply_markers(text, "x.md") == "a\nc\n"


def test_lite_only_block_on_its_own_lines_is_unwrapped():
    text = f"a\n{OPEN}\nb\n-->\nc\n"
    assert bl.apply_markers(text, "x.md") == "a\nb\nc\n"


def test_inline_blocks():
    text = f"x <!-- full-only -->old<!-- /full-only -->{OPEN} new --> y\n"
    assert bl.apply_markers(text, "x.md") == "x new y\n"


def test_line_emptied_by_inline_removal_is_dropped():
    text = "a\n<!-- full-only -->b<!-- /full-only -->\nc\n"
    assert bl.apply_markers(text, "x.md") == "a\nc\n"


def test_indented_markers():
    text = "1. a\n   <!-- full-only -->\n   b\n   <!-- /full-only -->\n   c\n"
    assert bl.apply_markers(text, "x.md") == "1. a\n   c\n"
```

and, each asserting `pytest.raises(bl.MarkerError, match=<message part>)`
with the source path and line in the message (`"x.md:2"`):
`test_unclosed_block_fails` (`full-only` opener with no closer, and a
lite-only opener with no `-->`), `test_nested_block_fails` (a lite opener
inside a full-only block), `test_comment_inside_lite_block_fails` (a line
`b --> c` inside a lite-only block), `test_other_lite_opener_fails`
(`<!-- lite-only something else` on its own line),
`test_stray_closer_fails` (`<!-- /full-only -->` with no opener).

```python
def test_skill_names_are_rewritten_once():
    text = "use agent-kit:spec-gate and agent-kit-lite:review"
    assert bl.rewrite_skill_names(text) == (
        "use agent-kit-lite:spec-gate and agent-kit-lite:review"
    )


def test_description_override_is_quoted():
    text = "---\nname: g\ndescription: old: text\n---\nbody\n"
    out = bl.override_description(text, 'new: "x" # y', "g.md")
    assert out == '---\nname: g\ndescription: "new: \\"x\\" # y"\n---\nbody\n'
    with pytest.raises(ValueError):
        bl.override_description("no frontmatter\n", "v", "g.md")


def test_rules_skill_moves_conventions_links():
    rules = (
        f"[a]({C}a.md#x) `{C}` [{C}b.md]({C}b.md)"
        " plugin/conventions/c.md ../../conventions/d.md\n"
    )
    out = bl.rules_skill(rules)
    assert out.startswith("---\nname: workspace-rules\ndescription: \"")
    body = out.split("\n---\n", 1)[1]
    assert "](../../conventions/a.md#x)" in body
    assert "`../../conventions/`" in body
    assert "[../../conventions/b.md](../../conventions/b.md)" in body
    assert "plugin/conventions/c.md" in body
    assert " ../../conventions/d.md" in body
```

`test_check_text_flags_each_rule`: with `kit_names=["tool.py"]`,
`skills={"spec-gate"}`, `commands={"ship"}`, each of these single lines
gives exactly one violation whose rule is named: `pip install x`
(`install`), `npx thing` (`install`), `see $HOME` (`variable`), `%TEMP%`
(`variable`), `$env:PATH` (`variable`), `run tool.py` (`kit-code`), `the
Kit Map` (`kit-code`), `hooks.json` (`kit-code`), `agent-kit:review`
(`skill-name`), `agent-kit-lite:nope` (`skill-name`), `<!-- full-only -->`
(`marker`), `run /ship-many now` (`command`), `/other:audit-deep`
(`command`), `` `~/.claude/x` `` (`home-path`).
`test_check_text_allows_clean_lines`: no violation for
`${CLAUDE_PLUGIN_ROOT}/conventions/a.md`, `$ARGUMENTS`, `echo $1 $@`,
`$(git rev-parse HEAD)`, `agent-kit-lite:spec-gate`,
`/agent-kit-lite:ship x`, `a SessionStart hook in your project`,
`tests/x.py`, `costs $5`.

`test_build_writes_the_tree(tmp_path)`: `build(make_root(...), dest)`
returns `[]`; `dest` holds `.claude-plugin/plugin.json` (name
`agent-kit-lite`, version `9.9.9`, no `icon`), `.claude-plugin/icon.png`,
`README.md`, `LICENSE`, `skills/workspace-rules/SKILL.md`,
`references/spec-lint-checks.md`, the three commands, and no
`skills/audit/user-mode.md` when the fake root has one.

`test_file_rules(tmp_path)`: in the fake root add
`plugin/skills/present/template.html`, `plugin/skills/present/tool.py`,
`plugin/skills/present/run.md` starting with `#!/bin/sh`, and
`plugin/skills/teach/LICENSE`; after `build`, `template.html.txt` and
`teach/LICENSE` exist, `tool.py`, `run.md` and `template.html` do not.

`test_references_follow_built_text(tmp_path)`: `ship.md` names
`${CLAUDE_PLUGIN_ROOT}/references/a.md` inside a full-only block and
`references/b.md` outside it; `b.md` names `references/c.md`. After
`build`: `references/b.md` and `references/c.md` exist,
`references/a.md` does not. A kept file naming `references/missing.md`
makes `build` return a problem line containing `references/missing.md`.

`test_build_normalises_crlf_sources(tmp_path)`: build the fake root, then
rewrite every text file under its `plugin/` with CRLF and build again into
a second folder; `compare(first, second) == []` and every built text file
holds no `\r`.

`test_compare_reports_drift(tmp_path)`: two built copies; append a line to
one copy's `commands/ship.md`, delete one file and add `extra.md`;
`compare` returns `differs: commands/ship.md`, a `missing:` line and
`extra: extra.md`. A copy whose text files are converted to CRLF (the PNG
untouched) compares equal. (`--check` on the real tree is Task 6's frozen
test.)

- [ ] **Step 3: Run the tests to see them fail**

Run: `pytest tests/test_lite_markers.py`
Expected: FAIL (`scripts/build-lite.py` does not exist).

- [ ] **Step 4: Implement `scripts/build-lite.py`**

Module docstring: usage `python scripts/build-lite.py [--check]`, what it
writes. Paths come from the script's own location:
`ROOT = Path(__file__).resolve().parents[1]`; never from the current
directory, and the build runs no `git` command. Constants at the top:

```python
SKILLS = ("capture-learnings", "lean-context", "teach", "grill", "spec-gate",
          "plan-gate", "review", "present", "pr-review-respond", "audit")
COMMANDS = ("ship.md", "ship-fast.md", "handoff.md")
SKIP = {"skills/audit/user-mode.md"}
KEEP_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".png"}
OPEN_FULL = "<!-- full-only -->"
CLOSE_FULL = "<!-- /full-only -->"
OPEN_LITE = "<!-- lite-only (agent-kit-lite only; agent-kit ignores this block)"
REF_RE = re.compile(r"references/([\w.-]+\.md)")
CONV_RE = re.compile(r"(?<![\w./-])" + "conventions" + "/")
EXCLUDED_COMMANDS = ("ship-many", "new-project", "adopt-conventions", "spec-html",
                     "statusline", "docker-compact", "archive-session", "audit-deep")
```

(format them with `ruff format`). `OVERRIDES` maps a lite path to a
description:

- `skills/grill/SKILL.md`: `Use when the user asks to be grilled on a plan, design or idea, for example after a design summary and before the spec is written. Interviews the user in numbered rounds, each question with a recommended answer, over the design's open decisions plus a coverage checklist, until the user confirms a shared understanding.`
- `skills/audit/SKILL.md`: `Use when asked to audit or health-check a whole repository, or the Claude Code setup in it (CLAUDE.md, .claude/, hooks, skills, commands, plugin), in one pass. Read-only; writes one report of cited, checked findings to docs/audit/audit.md.`
- `commands/ship-fast.md`: `Use for a proof of concept of about an hour - interview the user for the spec (or take an existing one), have the user read and approve it, ask the product decisions out loud, and take it to a tested, smoke-run pull request with green CI, with no gates, no review round and no merge; tasks run one at a time`

`RULES_FRONTMATTER` is exactly:

```text
---
name: workspace-rules
description: "Use before building a feature, designing or gating a spec or plan, creating a worktree, opening a pull request, or running /ship or /ship-fast. The agent-kit-lite workspace rules: key decisions, gates, pre-flight checks, worktrees and clean-up."
---

```

`MANIFEST_DESCRIPTION = "Markdown-only agent-kit for Claude Code: gated specs and plans, /ship and /ship-fast from spec to pull request, handoffs and the workspace conventions, with no hooks or scripts."`

Behaviour:

- `apply_markers`: input already LF. Line state machine with states none,
  full, lite. In state none: a line whose `strip()` is `OPEN_FULL` or
  `OPEN_LITE` enters that state and is dropped; otherwise replace every
  inline `OPEN_FULL.*?CLOSE_FULL` with nothing and every inline
  `OPEN_LITE(.*?)-->` with the group stripped of surrounding spaces; if the
  line still contains `<!-- full-only`, `<!-- /full-only` or
  `<!-- lite-only`, raise `MarkerError(f"{path}:{n}: marker must be alone on
  its line or open and close on one line")`; a line that inline removal
  left whitespace-only is dropped. In state full: a line whose `strip()` is
  `CLOSE_FULL` returns to none; a line holding `<!--` raises (nested);
  every other line is dropped. In state lite: a line whose `strip()` is
  `-->` returns to none; a line holding `<!--` or `-->` raises; other
  lines are kept as they are. End of text in state full or lite raises
  `unclosed`. Line numbers are 1-based source lines.
- `rewrite_skill_names`: `text.replace("agent-kit:", "agent-kit-lite:")`.
- `override_description`: the frontmatter is the text between a leading
  `---\n` and the next `\n---\n`; replace its `description:` line with
  `description: ` + `json.dumps(value, ensure_ascii=False)`; raise
  `ValueError` naming `path` when there is no frontmatter or no
  `description:` line.
- `rules_skill`: `RULES_FRONTMATTER + CONV_RE.sub("../../conventions/", rules_text)`.
- `transform(source: str, rel: str, text: str) -> str` (internal): `source`
  is the repo-relative source path used in messages (`plugin/skills/...`,
  `scripts/lite-README.md`), `rel` the lite path; normalise `\r\n` and
  `\r` to `\n`; `apply_markers(text, source)`; `rewrite_skill_names`; then
  the override if `rel in OVERRIDES`.
- `build(root, dest)`: collect problems instead of raising (a missing
  source file, a `MarkerError`, a `ValueError`, a missing reference, each
  one line) and keep going. Sources, sorted, from `root / "plugin"`:
  `conventions/*.md`; every file under each `skills/<name>/` in `SKILLS`
  (skip `__pycache__` folders and `SKIP`); `commands/<file>` for
  `COMMANDS`. Per file: bytes starting with `#!` are dropped; `.html`
  becomes text written as `<name>.html.txt`; a suffix in `KEEP_EXT` other
  than `.png`, or the name `LICENSE`, is text (`decode("utf-8-sig")`, then
  `transform`); `.png` is copied as bytes; anything else is dropped. Then
  references: start from `spec-lint-checks.md` plus every `REF_RE` match in
  the built text of the kept files, and add each name's built text and its
  own matches until no new name appears; a name with no
  `plugin/references/<name>` is a problem `"<rel>: names missing
  references/<name>"`. Generated files: `.claude-plugin/plugin.json`
  (`name` `agent-kit-lite`; `version`, `author`, `homepage`, `repository`,
  `keywords` from the plugin manifest; `description`
  `MANIFEST_DESCRIPTION`; `license` `MIT`; `json.dumps(..., indent=2,
  ensure_ascii=False) + "\n"`), `README.md` from
  `root / "scripts" / "lite-README.md"` through `transform`, `LICENSE` from
  `root / "LICENSE"` (newlines normalised), `.claude-plugin/icon.png` from
  `root / "scripts" / "lite-icon.png"` (bytes), and
  `skills/workspace-rules/SKILL.md` as `rules_skill(transform(rules.md))`.
  Write text with `newline="\n"`, UTF-8, in sorted order. Return the
  problems.
- `check_text`: per line (1-based), in this order, one violation per rule
  that matches: `install` (`curl `, `wget `, `Invoke-WebRequest`,
  `pip install`, `npm i\b`, `npm install`, `pnpm install`, `npx`, `uvx`,
  `pipx`, `bunx`); `variable` (`\$\{?([A-Za-z_]\w*)` or
  `%([A-Za-z_]\w*)%` whose name is not `CLAUDE_PLUGIN_ROOT` or
  `ARGUMENTS`, or `$env:` in any case; `$1`, `$@`, `$?`, `$(` and `$5` do
  not match); `kit-code` (any of `kit_names` as a case-sensitive substring,
  `<plugin root>/scripts/`, `${CLAUDE_PLUGIN_ROOT}/scripts/`, `hooks.json`,
  `CLAUDE_KIT_GRILL`, or `kit map` in any case); `skill-name` (`agent-kit:`
  anywhere, or `agent-kit-lite:<name>` with `<name>` in neither `skills`
  nor `commands`); `marker` (`<!--` then optional spaces then
  `full-only`, `/full-only` or `lite-only`); `command`
  (`/(?:[\w-]+:)?(?:<EXCLUDED_COMMANDS joined by |>)(?![\w-])`);
  `home-path` (`~/` or `%USERPROFILE%` at line start or after whitespace,
  a backtick, a quote, `(`, `[` or `<`).
- `check_tree(root, dest)`: `kit_names` = names of the files (not folders)
  directly in `root/plugin/scripts` and `root/plugin/hooks`; `skills` =
  folder names in `dest/skills`; `commands` = stems in `dest/commands`;
  `check_text` on every non-PNG file, with `rel` the posix path under
  `dest`.
- `compare(built, lite)`: posix relative file sets; `missing:` for a built
  file absent from `lite`, `extra:` for the reverse, `differs:` when
  contents differ, comparing `.png` as bytes and every other file after
  replacing `b"\r\n"` with `b"\n"` on both sides. Sorted output.
- `main`: build into a `tempfile.TemporaryDirectory()`, add `check_tree`
  problems; with `--check` add `compare(tmp, ROOT / "lite")`. Print every
  problem; any problem exits 1 and leaves `lite/` untouched. Otherwise
  `--check` prints `ok`; a plain run replaces `ROOT / "lite"` with the
  built tree (`shutil.rmtree` if present, then `shutil.copytree`) and
  prints `wrote lite/ (<n> files)`. Exit 0. Any other argument is a usage
  error (exit 2).

- [ ] **Step 5: Run the unit tests and lint**

Run: `pytest tests/test_lite_markers.py; ruff check plugin tests scripts; ruff format --check plugin tests scripts`
Expected: all tests pass; ruff prints `All checks passed!` and no file
would be reformatted.

- [ ] **Step 6: Run the real build once to see the work left**

Run: `python scripts/build-lite.py --check`
Expected: exit 1, with `missing:` lines (no `lite/` yet), a problem for
the missing `scripts/lite-README.md` (and for `scripts/lite-icon.png` if
Task 1 has not run, and for `references/spec-lint-checks.md` until Task 3), and `kit-code`, `variable`,
`home-path`, `command` and `skill-name` violations in the files Tasks 3 to
5 edit. Nothing is written to `lite/`.

- [ ] **Step 7: Run the full suite and commit**

Run: `pytest`
Expected: no failures.

```bash
git add scripts/build-lite.py tests/test_lite_markers.py
git commit -m "Add scripts/build-lite.py, the agent-kit-lite build"
```

---

### Task 3: Lint checklist, and the gate, grill and review sources

**Files:**
- Create: `plugin/references/spec-lint-checks.md`
- Modify: `plugin/skills/spec-gate/SKILL.md`
- Modify: `plugin/skills/spec-gate/rubric.md`
- Modify: `plugin/skills/plan-gate/SKILL.md`
- Modify: `plugin/skills/grill/SKILL.md`
- Modify: `plugin/skills/grill/coverage.md`
- Modify: `plugin/skills/review/SKILL.md`

**Depends on:** Task 2

**Interfaces:**
- Produces in `plugin/references/spec-lint-checks.md` the section headings
  later tasks point to by name: `## Spec rules`, `## Plan rules`,
  `## Lite document id`, `## Gate record check`, `## Frozen check`; the
  id pipeline is the only line in the file containing
  `git hash-object --stdin`, and it uses the placeholder `<document>`
  (Task 6's frozen test reads it from `lite/references/`).
- The Gate record check reports one line starting `ok:`, `missing:`,
  `not passed:`, `stale:` or `decisions not approved:` followed by the
  record path; the Frozen check reports `frozen: none declared`,
  `frozen: changed <path> since <short sha>` lines, or
  `frozen: ok (<n> files)`.

In the edits below, "F" means: wrap the quoted text in a full-only block
(own lines, or inline when it shares a line); "L" means: put this
lite-only text right after that F block (own lines for a sentence or more,
inline for a phrase).

- [ ] **Step 1: See the violations these files cause today**

Run: `python scripts/build-lite.py --check | grep -E "^(plugin/)?(skills/(spec-gate|plan-gate|grill|review)/|references/spec-lint-checks)"`
Expected: `kit-code` and `home-path` lines for `skills/spec-gate/SKILL.md`,
`skills/spec-gate/rubric.md`, `skills/plan-gate/SKILL.md`,
`skills/grill/SKILL.md`, `skills/grill/coverage.md` and
`skills/review/SKILL.md`.

- [ ] **Step 2: Write `plugin/references/spec-lint-checks.md`**

Title `# Lint checklist for specs and plans`, then one paragraph: the spec
and plan gates of agent-kit-lite apply these rules by reading the
document; text inside fenced code blocks is ignored by every rule; a
violation is reported as `<line>: <rule ID> <message>`.

`## Spec rules`: one bullet per rule, `**<ID>:** <rule>`, for `L1-status`,
`L2-date`, `L3-section`, `L4-out-of-scope`, `L5-placeholder`, `L6-empty`,
`L7-criterion`, `L8-path`, `L9-coverage`, each rule's text taken from the
`Rules` list in the docstring of `plugin/scripts/spec-lint.py`, worded for
a reader (no script names, no `--root`: "the repository root" instead).
`L9-coverage` keeps its common text (one `- **<Area>:**` bullet per area
listed under `## Areas` in the grill skill's `coverage.md`, at
`../skills/grill/coverage.md` from this file; each with text; `N/A`
followed by a reason; continuation lines count; unknown areas ignored; the
first of two bullets for an area checked) and puts its condition in two
blocks: F `Applies only when the CLAUDE_KIT_GRILL environment variable is 1 and the Date is 2026-10-01 or later.` (written as `CLAUDE_KIT_GRILL=1` is fine
inside F) and L `Applies only when the spec has a ## Coverage section.`

`## Plan rules`: the intro sentence "Files in a folder named `plans` get
these rules instead." and one bullet each for `P1-status`, `P2-date`,
`P3-header`, `P4-spec-gated`, `P5-tasks`, `P6-task-parts`,
`P7-placeholder`, `P8-empty`, `P9-path`, `P10-depends`, `P11-git-mv-add`,
from the same docstring. `P4-spec-gated` reads exactly: `**P4-spec-gated:** the spec named on the plan's **Spec:** line exists, and the Gate record check below reports ok: for it.` (with `**Spec:**` and `ok:`
in backticks).

`## Lite document id`, exactly this text, then the fence:

```text
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
```

and the pipeline in a `bash` fence, as one line, exactly:

```bash
tr -d '\r' < <document> | grep '' | sed -e '/^ \{0,3\}```/,/^ \{0,3\}```/b' -e '/^ \{0,3\}~~~/,/^ \{0,3\}~~~/b' -e '/^- \*\*Status:\*\*/d' -e 's/^\([[:space:]]*\)- \[[xX]\]/\1- [ ]/' | git hash-object --stdin
```

(Portability: `tr -d` strips CR; `grep ''` adds a missing final newline;
the sed uses only POSIX basic regular expressions, `b` with no label as
the last command of an `-e`, and `[[:space:]]`, so GNU sed, BSD sed on
macOS and Git Bash's sed agree; it was checked in Git Bash during
planning.)

`## Gate record check`, exactly:

```text
A spec's record is docs/superpowers/gates/<spec file name>; a plan's is
docs/superpowers/gates/plans/<plan file name>. Report the first reason
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
```

(In the file, `docs/superpowers/gates/<spec file name>` and the plan path
are in backticks.)

`## Frozen check`, exactly:

```text
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
```

- [ ] **Step 3: Edit `plugin/skills/spec-gate/SKILL.md`**

- F the Linter bullet (the three lines from `- **Linter:**` to
  `~/.claude/skills/agent-kit`.). L: `- **Lint checklist:** `../../references/spec-lint-checks.md` from this skill's directory. In this file, "run the linter" means apply its Spec rules by reading the spec, "exits 0" and "clean" mean no rule is broken, and a violation is a line it reports.`
- F the sentence starting `` `<path>` is the decision-log playbook's
  absolute path from the kit `` through `session-start output).` in step 2.
  L: `` `<path>` is the absolute path of `<plugin root>/conventions/decision-log.md`, with `<plugin root>` two folders above this skill's directory. ``
- Step 6: F `Run the linter with `--hash` on the spec after its last edit.`
  L: `After the spec's last edit, compute its lite id with the pipeline under "Lite document id" in the lint checklist.`
  After the closing fence of the record template, L: `In the record, the Spec SHA-256 line is - **Spec SHA-256:** lite-git:<id>, in place of the template's placeholder.` (the bullet in backticks).
  F `Then run the linter with `--verify-record` on the spec. On a pass verdict it must print `ok:`.` L: `Then run the Gate record check in the lint checklist on the spec: on a pass verdict it must report ok:.` (`ok:` in backticks).

- [ ] **Step 4: Edit `plugin/skills/spec-gate/rubric.md`**

- Check 8: reword (both plugins) `` `conventions/decision-log.md` in the
  repository `` to `` the repository's `./conventions/decision-log.md` ``.
- F the parenthesis `(In the kit repo, `<plugin root>/conventions/decision-log.md`, the plugin root stated in the kit map, is the workspace convention itself.)`. No L.

- [ ] **Step 5: Edit `plugin/skills/plan-gate/SKILL.md`**

- F the Linter bullet. L: `- **Lint checklist:** `../../references/spec-lint-checks.md` from this skill's directory. In this file, "run the linter" means apply its Plan rules by reading the plan (P4-spec-gated runs its Gate record check on the spec), "exits 0" and "clean" mean no rule is broken, and a violation is a line it reports.`
- Step 6: F `Run the linter with `--hash` on the plan and on the spec after the last plan edit.` L: `After the last plan edit, compute the lite ids of the plan and of the spec with the pipeline under "Lite document id" in the lint checklist.` After the record template's closing fence, L: `In the record, the two hash lines are - **Plan SHA-256:** lite-git:<plan id> and - **Spec SHA-256:** lite-git:<spec id>, in place of the template's placeholders.` (both bullets in backticks).
  F `Then run the linter with `--verify-record` on the plan: on `pass` it must print `ok:`; on `pass-with-decisions` it prints `decisions not approved` until the user approves.` L: `Then run the Gate record check in the lint checklist on the plan: on pass it must report ok:; on pass-with-decisions it reports decisions not approved: until the user approves.` (verdicts and results in backticks).

- [ ] **Step 6: Edit `plugin/skills/grill/SKILL.md` and `coverage.md`**

- `SKILL.md`, Hand-off to the spec: F `With `CLAUDE_KIT_GRILL=1`, `spec-lint.py` rule `L9-coverage` checks that section.` L: `The spec gate checks that section (the L9-coverage entry in ../../references/spec-lint-checks.md from this skill's directory).` (rule ID and path in backticks). The description is replaced by the build (Task 2); leave the frontmatter alone.
- `coverage.md`: F `` `spec-lint.py` (rule `L9-coverage`) reads `` (rewrap
  so it sits on one line). L: `The L9-coverage lint check reads` (rule ID
  in backticks).

- [ ] **Step 7: Edit `plugin/skills/review/SKILL.md`**

- Step 3: reword (both plugins) `` the repo's `conventions/engineering-practices.md` ``
  to `` the repo's `./conventions/engineering-practices.md` ``; F
  `, else the path from the kit map` (inline); L
  `, else <plugin root>/conventions/engineering-practices.md with <plugin root> two folders above this skill's directory` (path in backticks).
- Step 4: keep the line start `4. **Frozen check.**`; F everything after
  it in the step (from `Run` to the end of the `<plugin root>` sentence);
  L: `Run the Frozen check in ../../references/spec-lint-checks.md from this skill's directory with <spec>, [<plan>] and base <base>, and keep its whole output for the standards reviewer. With no spec and no plan, skip it and use Frozen: skipped (no spec or plan).` (paths, placeholders and the Frozen line in backticks).

- [ ] **Step 8: Run the check again**

Run: `python scripts/build-lite.py --check | grep -E "^(plugin/)?(skills/(spec-gate|plan-gate|grill|review)/|references/spec-lint-checks)"`
Expected: no output.

- [ ] **Step 9: Run the full suite and lint, then commit**

Run: `pytest; ruff check plugin tests scripts; ruff format --check plugin tests scripts`
Expected: no failures (in particular `tests/test_skill_size.py`,
`tests/test_spec_gate_skill.py`, `tests/test_plan_gate_skill.py`,
`tests/test_review_skill.py`, `tests/test_grill_skill.py`,
`tests/test_publish.py`); ruff clean.

```bash
git add plugin/references/spec-lint-checks.md plugin/skills/spec-gate plugin/skills/plan-gate plugin/skills/grill plugin/skills/review
git commit -m "Lint checklist and lite blocks for the gates, grill and review"
```

---

### Task 4: `/ship`, `/ship-fast`, `/handoff` and their references

**Files:**
- Modify: `plugin/commands/ship.md`
- Modify: `plugin/commands/ship-fast.md`
- Modify: `plugin/commands/handoff.md`
- Modify: `plugin/references/ship-finish.md`
- Modify: `plugin/references/ship-fast-finish.md`
- Modify: `plugin/references/ship-fast-cleanup.md`
- Modify: `plugin/references/ship-fast-resume.md`
- Modify: `plugin/references/ship-fast-spec.md`

**Depends on:** Task 2, Task 3

**Interfaces:**
- Consumes: the `## Gate record check` and `## Frozen check` sections of
  `plugin/references/spec-lint-checks.md` (Task 3) and their result words.

F and L as in Task 3. In `ship.md` keep every step's number line
(`0. **Gate.**` and so on) outside markers; prose inside a step stays
indented 3 spaces (4 in steps 10 to 12 of `ship-finish.md`). The commands
stay under 20,000 bytes: the long procedures live in
`spec-lint-checks.md`, so each block below is short. Check with
`git diff --stat` and `pytest tests/test_skill_size.py`; if one goes over,
move the longest lite-only block's text into a new named section of
`spec-lint-checks.md` and point to it.

- [ ] **Step 1: See the violations these files cause today**

Run: `python scripts/build-lite.py --check | grep -E "^(plugin/)?(commands/|references/(ship|pr-body))"`
Expected: `kit-code`, `home-path`, `command` and `skill-name` lines for
these files.

- [ ] **Step 2: Edit `plugin/commands/ship.md`**

- F the `FALLBACK_RULE` line (`Where `${CLAUDE_PLUGIN_ROOT}` is not expanded, use the plugin root stated in the kit map, ...`). L: `Where ${CLAUDE_PLUGIN_ROOT} is not expanded, use the plugin root in its place: the folder one level above the commands/ folder that holds this command.` (the variable in backticks).
- Stop rules: inline F `` `frozen-check.py` exits 1 `` and inline L
  `The frozen check finds a changed path` on the same line.
- Frozen check section: F from `` `python "${CLAUDE_PLUGIN_ROOT}/scripts/frozen-check.py" <spec> <plan>` ``
  through `it is not a stop rule.` (rewrap so `run` ends the line before).
  L: `run the Frozen check in ${CLAUDE_PLUGIN_ROOT}/references/spec-lint-checks.md with <spec> and <plan> in the feature worktree. frozen: ok or frozen: none declared: push. A frozen: changed line: the frozen stop rule. A git command that fails: debug it with superpowers:systematic-debugging and rerun before pushing; it is not a stop rule.` (path, placeholders, results and skill in backticks).
- Step 0: keep `0. **Gate.**`; F `Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-lint.py" --verify-record <spec>`.`; L `Run the Gate record check in ${CLAUDE_PLUGIN_ROOT}/references/spec-lint-checks.md on <spec>.` (backticks).
- Step 2: F the sentence `` `/ship-many`'s runner finds the branch by this rule. ``
- Step 3: F `` `spec-lint.py --verify-record <plan>` `` (inline); L `the Gate record check on <plan>` (placeholder in backticks).
- Step 3c: F `the decision-log playbook path from the kit map` (inline); L `${CLAUDE_PLUGIN_ROOT}/conventions/decision-log.md` (in backticks).
- Step 4: F from `` `spec-lint.py --verify-record <plan>` on the plan `` through
  `(under `/ship` its inline paths use SDD's task loop).`; L: `The Gate record check on the plan from step 3 must report ok:; otherwise return to step 3. Implement with superpowers:subagent-driven-development (SDD), one task at a time in plan order (agent-kit-lite has no parallel task runner).` (result and skill in backticks). Then F `(kit map)` after `engineering-practices playbook` (inline); L `(${CLAUDE_PLUGIN_ROOT}/conventions/engineering-practices.md)` (path in backticks).
- Step 6: F `` or `parallel-tasks`' `` (inline) so it reads "(SDD's)" in lite.

- [ ] **Step 3: Edit `plugin/references/ship-finish.md`**

- Step 9: F `is resolved by running `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py" docs/superpowers`, with the fallback `<plugin root>/scripts/spec-index.py`, then `git add docs/superpowers/README.md`, never by hand;` (rewrap as needed); L `is resolved by keeping every row from both sides, then git add docs/superpowers/README.md;` (command in backticks). F the `ROOT_NOTE` sentence at the end of step 9.
- Step 11: F `If the task used Docker, then run` through `its verdict is not a stop rule.`; F `` (`handoff.py` writes `/` as `_`) `` (inline); L `(a / in the branch name becomes _)` (the characters in backticks).
- Step 12 (Report): inline F `` the `docker disk:` line from step 11 if the task used Docker, `` (rewrap onto one line); at the end of the step, L: `In agent-kit-lite, add the line Spec index: not updated (needs the full agent-kit plugin).` (the line in backticks).

- [ ] **Step 4: Edit `plugin/commands/ship-fast.md`**

- F the `FALLBACK_RULE` line; L as in `ship.md`.
- Input, New repository bullet: F the bullet; L: `- **New repository:** agent-kit-lite never creates one. Ignore a - **Repo:** new line, work in the git repository that contains the spec, and tell the user once that creating a new project needs the full agent-kit plugin. A spec outside any git repository is a stop rule: say so and end.` (the Repo line in backticks).
- Stop rules intro: F from `Every stop after step 0 also states` through `` `~/.claude/ship-fast-specs/` path. ``; L: `Every stop after step 0 also states the absolute path of the spec to pass on the rerun, in the stop message and in the handoff.`
- Stop rules list: F the bullet `` - `git fetch origin`, `scaffold.py`, the stack's init command, or `gh repo create` fails. ``; L `` - `git fetch origin` fails. `` and `- The spec is not inside a git repository.` Then inline F/L the frozen bullet exactly as in `ship.md`.
- Step 1: keep `1. **Repo.**` on its line; F the rest of the step; L: `Run git fetch origin in the spec's repository.` (command in backticks).
- Step 2: inline F `For a repository created in step 1, skip this baseline run.` (lite never creates one).
- Step 4: keep `4. **Implement.**`; F from `Run` through `before implementing that task inline.`; L: `Implement the tasks one at a time, in order, in this session with superpowers:test-driven-development (agent-kit-lite has no parallel task runner). A product choice or risky engineering choice that the plan's ## Decisions does not settle is not guessed: ask it inline (see Questions) before implementing that task.` (skill and heading in backticks). Then F `playbook (kit map), with` through `for a later Cleanup).` (rewrap); L: `playbook (${CLAUDE_PLUGIN_ROOT}/conventions/engineering-practices.md), with <slug> as the task name and the baseline in <git common dir>/ship-fast/<slug>.docker-baseline.txt, where <git common dir> is the output of git rev-parse --path-format=absolute --git-common-dir (it outlives the worktree, for a later Cleanup).` (paths, placeholders and the command in backticks). Do not touch step 5's pinned line break.

- [ ] **Step 5: Edit the `/ship-fast` references**

- `ship-fast-spec.md` item 2: F `Otherwise Home is a grill question: a new repository (name, and `node` or `python`) or the path of an existing one.`; L `Otherwise Home is a grill question: the path of an existing git repository (agent-kit-lite does not create repositories).` Item 5: F `` a `- **Repo:** new <name> <stack>` line when Home is a new repository, `` (inline); F from `in an existing repository, under` through `step 1 copies it in).`; L `under docs/superpowers/specs/ in the home repository's main checkout (step 2 commits it on the branch).` (path in backticks).
- `ship-fast-resume.md`: F the paragraph `A repository folder counts as this run's only if` … and the three bullets that start `With **Repo:** new` (two) and `In both cases above`. No L.
- `ship-fast-finish.md` step 7: F the `ROOT_NOTE` sentence; F the `**Frozen check:**` paragraph; L: `**Frozen check:** before each push in this step, run the Frozen check in spec-lint-checks.md (in this file's folder) on <spec>; the task list carries no Frozen bullet. frozen: ok or frozen: none declared: push. A frozen: changed line: a stop rule. A git command that fails: debug it with superpowers:systematic-debugging and rerun before pushing.` (file, placeholder, results and skill in backticks).
- `ship-fast-cleanup.md`: F `If the task used Docker, then run` through `never prompts.`; F `` the spec under `~/.claude/ship-fast-specs/` is not a scratch file and stays. `` and the `ROOT_NOTE` sentence. L after the first F: none; after the Docker-baseline sentence, L: `The Docker baseline file is <git common dir>/ship-fast/<slug>.docker-baseline.txt.` (path in backticks).

- [ ] **Step 6: Edit `plugin/commands/handoff.md`**

- Opening: F `` and the next session on this branch loads it automatically on start. `` (rewrap so `It is gitignored, per work tree,` ends before it); L `and per work tree; no hook loads it in agent-kit-lite, so the next session reads it when the user asks.`
- Step 2: keep `2. Get the path and the generated State section:`; F the two
  command lines and the fallback lines below them; L, indented 3 spaces:

```text
   - **Path:** <git rev-parse --show-toplevel>/.claude/handoffs/<name>.md,
     where <name> is the branch (git branch --show-current, or
     detached-<git rev-parse --short=7 HEAD> when detached) with every
     character other than letters, digits, ".", "_" and "-" replaced by
     "_" (feat/x becomes feat_x).
   - **State section:** write these lines from the commands named:
     ## State
     - branch: <branch>  (worktree: <git rev-parse --show-toplevel>)
     - upstream: <git rev-parse --abbrev-ref @{u}>, ahead <A>, behind <B>,
       where <B> and <A> are the two numbers git rev-list --left-right
       --count @{u}...HEAD prints; or - upstream: none without an upstream
     - dirty: the paths from git status --porcelain, comma-separated, or clean
     - last commits: git log --oneline -5 joined with "; ", or none
     - PR: the URL from gh pr view --json url -q .url, or none
```

  (commands, paths and the State lines in backticks in the real file).
- Step 3: F `The file is re-injected into every future session on this branch.`; L `Every future session on this branch may read it.`
- Step 4: F the quoted sentence `"Run `/clear` to start fresh; the next session loads this handoff automatically."`; L `"Run /clear, then start the next session with: read .claude/handoffs/<name>.md and continue."` (command and path in backticks).

- [ ] **Step 7: Run the check again**

`plugin/references/pr-body.md` has no flagged text and gets no marker;
this check confirms it.

Run: `python scripts/build-lite.py --check | grep -E "^(plugin/)?(commands/|references/(ship|pr-body))"`
Expected: no output.

- [ ] **Step 8: Run the full suite and lint, then commit**

Run: `pytest; ruff check plugin tests scripts; ruff format --check plugin tests scripts`
Expected: no failures (in particular `tests/test_ship_command.py`,
`tests/test_ship_fast_command.py`, `tests/test_handoff*.py`,
`tests/test_skill_size.py`); ruff clean.

```bash
git add plugin/commands/ship.md plugin/commands/ship-fast.md plugin/commands/handoff.md plugin/references
git commit -m "Lite blocks for /ship, /ship-fast, /handoff and their references"
```

---

### Task 5: Rules, conventions and the other kept skills

**Files:**
- Modify: `plugin/rules.md`
- Modify: `plugin/conventions/session-hygiene.md`
- Modify: `plugin/conventions/spec-driven-development.md`
- Modify: `plugin/conventions/engineering-practices.md`
- Modify: `plugin/conventions/project-memory.md`
- Modify: `plugin/skills/capture-learnings/SKILL.md`
- Modify: `plugin/skills/lean-context/SKILL.md`
- Modify: `plugin/skills/present/SKILL.md`
- Modify: `plugin/skills/pr-review-respond/SKILL.md`
- Modify: `plugin/skills/audit/SKILL.md`
- Modify: `plugin/skills/audit/rules.md`
- Modify: `plugin/skills/audit/duplicates.md`

**Depends on:** Task 2

F and L as in Task 3.

- [ ] **Step 1: See the violations these files cause today**

Run: `python scripts/build-lite.py --check | grep -E "^(plugin/)?(rules.md|conventions/|skills/(workspace-rules|capture-learnings|lean-context|present|pr-review-respond|audit)/)"`
Expected: violations in each file listed above.

- [ ] **Step 2: Edit `plugin/rules.md` (full-only only, plus one phrase)**

Rewrap so each block sits on its own lines where it can. F, in order:
`In a child repo, the kit map injected at session start gives these files' absolute paths.`;
the whole paragraph `With `CLAUDE_KIT_GRILL=1`, the `agent-kit:grill` skill runs ...` in Designing a spec;
in Specs and plans, from `` `/spec-html [path]` renders and opens a view on demand `` through
`` else `~/.claude/skills/agent-kit`. `` (the `One exception: /ship-fast ...` sentence stays);
inline `` or `/ship-many <spec.md> ...` `` in the bold `/ship` sentence;
`The README describes all three.` with inline L `The README describes both.`;
`The kit's session-start hook reports leftover worktrees and branches; treat that as a to-do, but`
with inline L `Treat leftover worktrees and branches as a to-do, but`.
Keep the `test_docs.py` phrases intact ("no approval pause between design
sections", `agent-kit:plan-gate`, the `/ship-fast` interview paragraph,
"never suggests deleting", `agent-kit:capture-learnings` in the "A feature
is not finished" paragraph).

Run: `pytest tests/test_workspace_rules_inject.py tests/test_docs.py tests/test_publish.py`
Expected: pass (the injected size stays under 9,500 characters).

- [ ] **Step 3: Edit the conventions**

`session-hygiene.md`:
- Inline F ` (`token-report.py --all --dollars`)` before the `:` that ends
  the "across 235 sessions" sentence (rewrap onto one line).
- Principle 3: F from `The rule is on by default;` to `(ADR 0032).`
- Principles 4 and 5: F both items whole.
- The handoff file: F from `its State section is refreshed automatically at session end; it is injected automatically` through `so an old task is not revived).`; L `the next session reads it when you ask it to.`; inline F `loads it` / L `may read it` in `since every later session on the branch loads it`.
- The routine: item 1 inline F `read the injected handoff` / L `read the branch's handoff file`; item 2 inline F `; keep an eye on the status line`; item 3 inline F `When the nudge appears` / L `When the context grows large`.
- F the whole `## Re-measuring` section (heading and body).

`spec-driven-development.md`:
- Brainstorm step: F the grill paragraph (`With the kit's opt-in grill on ...
  before the spec is written.`); L: `If you ask for it, the agent-kit:grill skill then interviews you on the agreed design and a coverage checklist (the grill skill's coverage.md) before the spec is written.` (skill and file in backticks).
- F the `**Coverage**` bullet; L: `- **Coverage** (optional; checked only when present) — one - **<Area>:** bullet per area in the grill skill's coverage.md, saying where the spec addresses it or N/A with the reason. The spec gate checks it with rule L9-coverage.` (bullet shape, file, `N/A` and rule ID in backticks).
- F the bullet about the generated index (`` `docs/superpowers/README.md` is a **generated index** `` … `do not edit it by hand.`).
- Spec gate: inline F `` with `plugin/scripts/spec-lint.py` `` / L `against its lint checklist`. Plan gate: inline F `` with `plugin/scripts/spec-lint.py` (plan rules apply to files in a `plans` folder) `` / L `against its lint checklist (plan rules apply to files in a plans folder)` (`plans` in backticks).
- Frozen files: F `` `plugin/scripts/frozen-check.py` enforces this before each push in `/ship` and `/ship-fast`. ``; L `/ship and /ship-fast check this before each push.` (commands in backticks).
- F the whole `## Parallel plan tasks` section; L: `## Plan task order` (own line), a blank line inside the L block, then `A task may carry one **Depends on:** line under its **Files:** block: none, or the earlier tasks whose results it uses (Task 1, Task 3). The plan gate checks the line with rule P10-depends. In agent-kit-lite, /ship and /ship-fast run tasks one at a time, in plan order.` (bold labels kept, values and commands in backticks).
- F the body of `## Rendered views`; L `The .md is the only source of truth and the only thing produced; nothing renders it automatically.` (`.md` in backticks).

`engineering-practices.md`: inline F `` or `/ship-many` `` in "Ask during
design"; F the scaffolder paragraph (`` The scaffolder (`/new-project`,
`/adopt-conventions`) ships `` … `until the repo has credentials.`); F
`` The clean-up also runs `plugin/scripts/docker-disk.py` `` through
`(ADR 0038).` at the end of Docker hygiene.

`project-memory.md`: F the bullet `` **Bootstrap it with `/new-project`
(new repo) or `/adopt-conventions` (existing repo)** … not the
deliverable. ``; L: `- **Bootstrap it with /init** to draft the commands, architecture and gotchas, then prune hard — the draft is a starting point, not the deliverable.` (`/init` in backticks).

- [ ] **Step 4: Edit `capture-learnings` and `lean-context`**

- `capture-learnings/SKILL.md` Mode: inline F `` , so
  `/ship-many` children pass it too `` (rewrap onto one line) so lite
  reads "(passed by `/ship` and `/ship-fast`)". In the memory bullet, F
  `` : `/ship-many` children may write memory at the same time `` (inline,
  rewrapped) so lite reads "never by rewriting the whole file."
- `lean-context/SKILL.md` rule 4 example, reworded in both plugins:
  `` Example: `pytest > <scratchpad>/test.log 2>&1; grep -n -m5 -E 'FAIL|Error' <scratchpad>/test.log; tail -15 <scratchpad>/test.log`. ``
  Why: wrap the whole phrase `the session-hygiene playbook (path in the kit map)` in one inline F (it stays contiguous inside the markers, as `tests/test_kit_map_inject.py` pins it) / inline L `the session-hygiene playbook (../../conventions/session-hygiene.md from this skill's directory)` (path in backticks; no `<plugin root>/`, see the Context fact on `test_fallbacks_name_the_kit_map_root`). The file stays at most 60 lines.

- [ ] **Step 5: Edit `present`**

- The opening paragraph's sentence naming `template.html`: after `` `template.html` `` add inline L `(shipped as template.html.txt)` (file in backticks).
- Build, after the `Copy `template.html` to the target.` bullet: L `- In agent-kit-lite the template is template.html.txt next to this file: copy it to the deck's .html path.` (names in backticks).
- 4. Verify: F the section body (from `From the plugin root` through
  `say in the hand-over that the slides were not rendered.`); L: `Check the deck by reading it: every <section class="slide"> has a data-time="m:ss" start time, the times rise from slide to slide, the last slide starts before the length in minutes, and nothing loads from the network (no src= or href= value, @import or CSS url( outside HTML comments that starts with http:, https: or //). Fix each failure and check again. agent-kit-lite renders no screenshots: say so in the hand-over and ask the user to page through the deck once in a browser.` (markup, attributes and schemes in backticks).

- [ ] **Step 6: Edit `pr-review-respond`**

F the paragraph from `The script is `review-threads.py`` through `say so
in the report.`. L, the paragraph and the indented code line below
(placeholders are literal text the reader replaces; the query uses no
GraphQL variables, so it carries no `$`):

```text
Read the review items with gh. Take <owner> and <name> from
gh repo view --json owner,name and <number> from the arguments, else from
gh pr view --json number, and write them into this query literally:

    gh api graphql -f query='query { viewer { login } repository(owner: "<owner>", name: "<name>") { pullRequest(number: <number>) { number url state headRefName author { login } reviewThreads(first: 100) { pageInfo { hasNextPage } nodes { id isResolved isOutdated path line comments(first: 100) { pageInfo { hasNextPage } nodes { databaseId author { login } body url createdAt } } } } reviews(first: 100) { pageInfo { hasNextPage } nodes { databaseId author { login } state body url submittedAt } } comments(first: 100) { pageInfo { hasNextPage } nodes { databaseId author { login } body url createdAt } } } } }'

From its JSON take pr (number), url, state, head (headRefName), author,
viewer (viewer.login) and items: each unresolved thread whose last comment
is not by viewer (a thread, with thread_id its id, reply_to its first
comment's databaseId, path, line, outdated and its comments), then each
review with a non-empty body and each conversation comment, in both
cases by someone other than viewer and newer than viewer's latest
conversation comment. A null author is ghost. Below, "the script" means this query and
"its output" these fields. A failing gh command means stop: show its
stderr. Any hasNextPage that is true means only the first 100 entries
were read: say so in the report. No more pages are fetched.
```

(commands and field names in backticks in the real file).

- [ ] **Step 7: Edit `audit`**

- `SKILL.md` User mode: F the section body; L: `If $ARGUMENTS is --user, say that the user-scope audit needs the full agent-kit plugin, and stop.` (`$ARGUMENTS` and `--user` in backticks). The description is replaced by the build.
- `SKILL.md` Pass 4: F the body; L: `Skip this pass in agent-kit-lite. Its output is the single line Skipped: the duplicate-intent pass needs the full agent-kit plugin.` (the line in backticks).
- `rules.md` section 1, reworded in both plugins: `` the system temp directory (the folder named by the TMPDIR or TEMP environment variable, else `/tmp`) ``.
- `rules.md` section 5: F the body; L: `Check every finding's citation by hand: open the cited file, confirm the Where line or range is inside it and the Evidence quote (whitespace-normalised; ... skips a middle part) appears within three lines of it. Evidence (absent) and (history <sha>) skip the file check. Fix or drop each finding that fails, and use the line Citations checked by hand: <n> findings, <m> fixed or dropped. as the checker's summary line.` (quoted forms in backticks).
- `duplicates.md`: F everything after the `# Duplicate-intent pass` title; L: `agent-kit-lite skips this pass (see Pass 4 in SKILL.md).` (file in backticks).

- [ ] **Step 8: Run the check again**

Run: `python scripts/build-lite.py --check | grep -E "^(plugin/)?(rules.md|conventions/|skills/(workspace-rules|capture-learnings|lean-context|present|pr-review-respond|audit)/)"`
Expected: no output.

- [ ] **Step 9: Run the full suite and lint, then commit**

Run: `pytest; ruff check plugin tests scripts; ruff format --check plugin tests scripts`
Expected: no failures (in particular `tests/test_docs.py`,
`tests/test_publish.py`, `tests/test_audit_skills.py`,
`tests/test_present_skill.py`, `tests/test_pr_review_respond_skill.py`,
`tests/test_capture_learnings_skill.py`, `tests/test_plugin_manifest.py`,
`tests/test_workspace_rules_inject.py`, `tests/test_kit_map_inject.py`,
`tests/test_publish.py::test_fallbacks_name_the_kit_map_root`); ruff clean.

```bash
git add plugin/rules.md plugin/conventions plugin/skills/capture-learnings plugin/skills/lean-context plugin/skills/present plugin/skills/pr-review-respond plugin/skills/audit
git commit -m "Lite blocks for the rules, conventions and remaining skills"
```

---

### Task 6: Generate `lite/`, the frozen test, marketplace and CI

**Files:**
- Create: `scripts/lite-README.md`
- Create: `lite/` (generated by `python scripts/build-lite.py`)
- Test: `tests/test_lite_build.py`
- Modify: `tests/test_publish.py`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.github/workflows/ci.yml`
- Modify: `AGENTS.md`

**Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5

- [ ] **Step 1: Write the frozen test `tests/test_lite_build.py`, exactly**

```python
"""Checks on the generated agent-kit-lite plugin in lite/ (frozen, spec D10).

lite/ is built from plugin/ by scripts/build-lite.py. These tests hold it to
what Anthropic's plugin directory accepts from an unverified publisher.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LITE = REPO / "lite"
PLUGIN = REPO / "plugin"

ALLOWED_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".png"}
LITE_SKILLS = {
    "audit",
    "capture-learnings",
    "grill",
    "lean-context",
    "plan-gate",
    "pr-review-respond",
    "present",
    "review",
    "spec-gate",
    "teach",
    "workspace-rules",
}
LITE_COMMANDS = {"handoff.md", "ship-fast.md", "ship.md"}
EXCLUDED_COMMANDS = (
    "ship-many",
    "new-project",
    "adopt-conventions",
    "spec-html",
    "statusline",
    "docker-compact",
    "archive-session",
    "audit-deep",
)
ALLOWED_VARS = {"CLAUDE_PLUGIN_ROOT", "ARGUMENTS"}
INSTALL_RE = re.compile(
    r"curl |wget |Invoke-WebRequest|pip install|npm i\b|npm install"
    r"|pnpm install|npx|uvx|pipx|bunx"
)
VAR_RE = re.compile(r"\$\{?([A-Za-z_]\w*)|%([A-Za-z_]\w*)%")
ENV_RE = re.compile(r"\$env:", re.I)
KIT_LITERALS = (
    "<plugin root>/scripts/",
    "${CLAUDE_PLUGIN_ROOT}/scripts/",
    "hooks.json",
    "CLAUDE_KIT_GRILL",
)
KIT_MAP_RE = re.compile(r"kit map", re.I)
LITE_SKILL_RE = re.compile(r"agent-kit-lite:([A-Za-z0-9_-]+)")
MARKER_RE = re.compile(r"<!--\s*/?(?:full-only|lite-only)")
COMMAND_RE = re.compile(
    r"/(?:[\w-]+:)?(?:" + "|".join(EXCLUDED_COMMANDS) + r")(?![\w-])"
)
HOME_RE = re.compile(r"(?:^|[\s`'\"(\[<])(?:~/|%USERPROFILE%)")
FENCE_RE = re.compile(r"^```.*?^```[ \t]*$", re.M | re.S)
CODE_SPAN_RE = re.compile(r"(`+)(?:(?!\n[ \t]*\n).)+?(?<!`)\1(?!`)", re.S)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
FM_LINE_RE = re.compile(r"^([A-Za-z][\w-]*):(?: (.*))?$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def lite_files() -> list[Path]:
    return sorted(p for p in LITE.rglob("*") if p.is_file())


def rel(path: Path) -> str:
    return path.relative_to(LITE).as_posix()


def kit_code_names() -> list[str]:
    return sorted(
        p.name
        for folder in ("scripts", "hooks")
        for p in (PLUGIN / folder).iterdir()
        if p.is_file()
    )


def line_problems(
    line: str, skills: set[str], commands: set[str], kit_names: list[str]
) -> list[str]:
    found = []
    if INSTALL_RE.search(line):
        found.append("install")
    names = [a or b for a, b in VAR_RE.findall(line)]
    if ENV_RE.search(line) or any(n not in ALLOWED_VARS for n in names):
        found.append("variable")
    kit = any(n in line for n in kit_names)
    if kit or any(s in line for s in KIT_LITERALS) or KIT_MAP_RE.search(line):
        found.append("kit-code")
    known = skills | commands
    bad = [n for n in LITE_SKILL_RE.findall(line) if n not in known]
    if "agent-kit:" in line or bad:
        found.append("skill-name")
    if MARKER_RE.search(line):
        found.append("marker")
    if COMMAND_RE.search(line):
        found.append("command")
    if HOME_RE.search(line):
        found.append("home-path")
    return found


def run_check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "build-lite.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def copy_repo(dest: Path) -> None:
    skip = shutil.ignore_patterns("__pycache__")
    for name in ("plugin", "scripts", "lite"):
        shutil.copytree(REPO / name, dest / name, ignore=skip)
    shutil.copy2(REPO / "LICENSE", dest / "LICENSE")


def test_build_check_finds_no_drift():
    result = run_check(REPO)
    assert result.returncode == 0, result.stdout + result.stderr


def test_build_check_accepts_a_crlf_checkout(tmp_path):
    copy_repo(tmp_path)
    for path in (tmp_path / "lite").rglob("*"):
        if path.is_file() and path.suffix != ".png":
            data = path.read_bytes().replace(b"\r\n", b"\n")
            path.write_bytes(data.replace(b"\n", b"\r\n"))
    result = run_check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_build_check_reports_drift(tmp_path):
    copy_repo(tmp_path)
    ship = tmp_path / "lite" / "commands" / "ship.md"
    ship.write_bytes(ship.read_bytes() + b"drift\n")
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert "commands/ship.md" in result.stdout


def test_lite_has_its_generated_files():
    for name in ("README.md", "LICENSE", ".claude-plugin/plugin.json"):
        assert (LITE / name).is_file(), name
    assert (LITE / ".claude-plugin" / "icon.png").is_file()
    assert (LITE / "skills" / "workspace-rules" / "SKILL.md").is_file()


def test_every_file_is_an_allowed_type():
    problems = []
    for path in lite_files():
        data = path.read_bytes()
        if path.suffix not in ALLOWED_EXT and path.name != "LICENSE":
            problems.append(f"{rel(path)}: file type")
        if data.startswith(b"#!"):
            problems.append(f"{rel(path)}: starts with #!")
        if path.suffix == ".png":
            continue
        if b"\0" in data:
            problems.append(f"{rel(path)}: NUL byte")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{rel(path)}: not UTF-8")
    assert not problems, problems


def test_no_banned_files_or_folders():
    problems = []
    for path in LITE.rglob("*"):
        name = path.name
        if path.is_file() and name.lower() in {"claude.md", "agents.md"}:
            problems.append(rel(path))
        if name == ".mcp.json":
            problems.append(rel(path))
        if path.is_dir() and name in {"hooks", ".claude"}:
            problems.append(rel(path))
    assert not problems, problems


def test_no_line_breaks_a_built_text_check():
    skills = {p.name for p in (LITE / "skills").iterdir() if p.is_dir()}
    commands = {p.stem for p in (LITE / "commands").glob("*.md")}
    kit_names = kit_code_names()
    assert "spec-lint.py" in kit_names and "run.py" in kit_names
    problems = []
    for path in lite_files():
        if path.suffix == ".png":
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            for rule in line_problems(line, skills, commands, kit_names):
                problems.append(f"{rel(path)}:{number}: {rule}")
    assert not problems, "\n".join(problems)


def test_frontmatter_values_are_quoted():
    files = sorted(LITE.glob("skills/*/SKILL.md"))
    files += sorted(LITE.glob("commands/*.md"))
    problems = []
    for path in files:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        assert text.startswith("---\n"), rel(path)
        head = text[4 : text.index("\n---\n", 4)]
        for line in head.splitlines():
            match = FM_LINE_RE.match(line)
            if not match:
                problems.append(f"{rel(path)}: not key: value: {line}")
                continue
            value = (match.group(2) or "").strip()
            quoted = len(value) >= 2 and value[0] == value[-1] == '"'
            if ("#" in value or ": " in value) and not quoted:
                problems.append(f"{rel(path)}: unquoted: {line}")
    assert not problems, problems


def png_chunks(data: bytes) -> list[bytes]:
    chunks, pos = [], 8
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        chunks.append(data[pos + 4 : pos + 8])
        pos += 12 + length
    return chunks


def test_icon_is_a_square_png_within_limits():
    data = (LITE / ".claude-plugin" / "icon.png").read_bytes()
    assert data[:8] == PNG_SIGNATURE
    width, height = struct.unpack(">II", data[16:24])
    assert width == height
    assert 512 <= width <= 2048
    assert len(data) < 2 * 1024 * 1024
    chunks = png_chunks(data)
    assert chunks[0] == b"IHDR" and chunks[-1] == b"IEND"
    assert not {b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME"} & set(chunks)


def test_lint_checklist_names_every_rule():
    source = (PLUGIN / "scripts" / "spec-lint.py").read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(source))
    ids = set(re.findall(r"\b[LP]\d+-[a-z]+(?:-[a-z]+)*", doc))
    assert len(ids) >= 20
    checklist = LITE / "references" / "spec-lint-checks.md"
    text = checklist.read_text(encoding="utf-8")
    assert sorted(i for i in ids if i not in text) == []


def test_lite_manifest_matches_the_full_plugin():
    path = LITE / ".claude-plugin" / "plugin.json"
    lite = json.loads(path.read_text(encoding="utf-8"))
    full_path = PLUGIN / ".claude-plugin" / "plugin.json"
    full = json.loads(full_path.read_text(encoding="utf-8"))
    assert lite["name"] == "agent-kit-lite"
    assert lite["version"] == full["version"]
    assert lite["license"] == "MIT"
    for key in ("description", "author", "homepage", "repository", "keywords"):
        assert lite.get(key), key
    assert "icon" not in lite
    assert "hooks" not in lite


def test_lite_ships_exactly_the_d3_skills_and_commands():
    skills = {p.name for p in (LITE / "skills").iterdir() if p.is_dir()}
    assert skills == LITE_SKILLS
    commands = {p.name for p in (LITE / "commands").iterdir()}
    assert commands == LITE_COMMANDS
    assert (LITE / "skills" / "present" / "template.html.txt").is_file()
    assert not (LITE / "skills" / "audit" / "user-mode.md").exists()


def test_relative_links_resolve_inside_lite():
    root = LITE.resolve()
    broken = []
    for path in LITE.rglob("*.md"):
        prose = FENCE_RE.sub("", path.read_text(encoding="utf-8"))
        prose = CODE_SPAN_RE.sub("", prose)
        for match in LINK_RE.finditer(prose):
            href = match.group(1).split("#", 1)[0]
            if not href or "://" in href or href.startswith("mailto:"):
                continue
            target = (path.parent / href).resolve()
            if not target.exists() or not target.is_relative_to(root):
                broken.append(f"{rel(path)} -> {href}")
    assert not broken, broken


def find_bash() -> tuple[str, dict[str, str]] | None:
    env = dict(os.environ)
    if os.name != "nt":
        bash = shutil.which("bash")
        return (bash, env) if bash else None
    out = subprocess.run(["git", "--exec-path"], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    root = Path(out.stdout.strip()).parents[2]
    bin_dir = root / "usr" / "bin"
    if not (bin_dir / "bash.exe").is_file():
        return None
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    return str(bin_dir / "bash.exe"), env


def id_command() -> str:
    text = (LITE / "references" / "spec-lint-checks.md").read_text("utf-8")
    [line] = [x.strip() for x in text.splitlines() if "hash-object --stdin" in x]
    assert "<document>" in line
    return line


def lite_id(tmp_path: Path, text: str, newline: str = "\n") -> str:
    found = find_bash()
    if found is None:
        pytest.skip("no bash with tr, grep and sed")
    bash, env = found
    doc = tmp_path / "doc.md"
    doc.write_bytes(text.replace("\n", newline).encode("utf-8"))
    command = id_command().replace("<document>", "doc.md")
    result = subprocess.run(
        [bash, "-c", command], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    value = result.stdout.strip()
    assert re.fullmatch(r"[0-9a-f]{40}", value), value
    return value


SPEC = (
    "# Sample spec\n\n- **Status:** draft\n- **Date:** 2026-11-27\n\n"
    "## Purpose\n\nText.\n\n```\n- **Status:** draft\n- [x] fenced box\n```\n\n"
    "- [ ] open box\n"
)
PLAN = (
    "# Sample plan\n\n- **Status:** draft\n- **Date:** 2026-11-27\n\n"
    "### Task 1: One\n\n- [ ] **Step 1: Write it**\n  - [ ] nested\n\n"
    "~~~\n- [ ] fenced step\n~~~\n"
)


def test_lite_id_ignores_status_ticks_and_line_endings(tmp_path):
    base = lite_id(tmp_path, SPEC)
    approved = SPEC.replace("draft\n- **Date", "approved\n- **Date")
    assert lite_id(tmp_path, approved) == base
    assert lite_id(tmp_path, SPEC.replace("- [ ] open", "- [x] open")) == base
    assert lite_id(tmp_path, SPEC, newline="\r\n") == base
    assert lite_id(tmp_path, SPEC.rstrip("\n")) == base
    plan = lite_id(tmp_path, PLAN)
    ticked = PLAN.replace("- [ ] **Step", "- [x] **Step")
    assert lite_id(tmp_path, ticked.replace("  - [ ]", "  - [X]")) == plan
    assert lite_id(tmp_path, PLAN.replace("draft", "approved")) == plan


def test_lite_id_catches_other_changes(tmp_path):
    base = lite_id(tmp_path, SPEC)
    assert lite_id(tmp_path, SPEC.replace("Text.", "Text!")) != base
    fenced = SPEC.replace("```\n- **Status:** draft", "```\n- **Status:** done")
    assert lite_id(tmp_path, fenced) != base
    assert lite_id(tmp_path, SPEC.replace("- [x] fenced", "- [ ] fenced")) != base
    plan = lite_id(tmp_path, PLAN)
    assert lite_id(tmp_path, PLAN.replace("- [ ] fenced", "- [x] fenced")) != plan
    assert lite_id(tmp_path, PLAN.replace("Write it", "Write that")) != plan
```

Copy it byte for byte with the Write tool; run `ruff format` on it once
and, if ruff changes anything, keep ruff's version (that is the frozen
content committed in Step 6). After the commit in Step 6 it never changes.

- [ ] **Step 2: Run it to see it fail**

Run: `pytest tests/test_lite_build.py`
Expected: FAIL (no `lite/` yet; the build check reports `missing:` lines).

- [ ] **Step 3: Write `scripts/lite-README.md`**

```text
# agent-kit-lite

agent-kit-lite is the Markdown-only edition of
[agent-kit](https://github.com/alymo8/claude-kit), a spec-driven workflow
for Claude Code. It gates specs and plans with fresh-context reviewers,
takes an approved spec to a merged pull request with /ship (or to an open
pull request with /ship-fast for a proof of concept), writes handoff files
between sessions, reviews a branch against its spec, and ships the
workspace conventions it follows. It has no hooks and no scripts: every
step is done by Claude reading these files and running git and gh.

## Requires

- The superpowers plugin: see its install page at
  https://github.com/obra/superpowers. The skills here call its skills.
- git and gh, signed in, for /ship, /ship-fast and pr-review-respond.

## What's inside

- Skills: spec-gate, plan-gate, grill, review, capture-learnings,
  lean-context, present, pr-review-respond, audit, teach, and
  workspace-rules (the conventions as one skill).
- Commands: /ship, /ship-fast and /handoff.
- The six convention playbooks in the plugin's ./conventions/ folder.

## Lite and full

The full agent-kit, on the repository's own marketplace, adds session
hooks (handoff injection, a context nudge, the workspace rules at every
session start), scripts behind the lint, frozen and citation checks,
parallel plan tasks, a runner that ships several specs at once, project
scaffolding and more. In lite,
those checks are done by reading, tasks run one at a time, and a new
session reads its handoff when you ask it to.

## Always-on rules

Nothing loads the workspace rules on its own in lite. Claude loads the
workspace-rules skill for feature work; to keep the rules in every
session, import that skill's SKILL.md from your own CLAUDE.md with an @
line pointing at the installed plugin's skills/workspace-rules/SKILL.md.

## Data and network

No telemetry, and nothing is sent to the plugin's authors. The commands
and skills reach GitHub only through your own git and gh when you run
them. Handoff files are written under .claude/handoffs/ in your repository
when you run /handoff.

## License

MIT, see LICENSE.
```

(In the real file, put command names, skill names, paths and `CLAUDE.md`
in backticks. It must hold no install command, no excluded `/<command>`
name and no `conventions/` without a `/` or `.` before it.)

- [ ] **Step 4: Generate `lite/` and check it**

Run: `python scripts/build-lite.py`
Expected: `wrote lite/ (<n> files)`, exit 0.

Run: `python scripts/build-lite.py --check`
Expected: `ok`.

Run: `claude plugin validate ./lite --strict`
Expected: exit 0 (Success criterion 1). If `claude` is not installed in
this environment, stop and report it: the main session runs it.

- [ ] **Step 5: Marketplace, `test_publish`, CI and AGENTS.md**

- `.claude-plugin/marketplace.json`: add a second entry after `agent-kit`:
  `{"name": "agent-kit-lite", "source": "./lite", "description": "Markdown-only agent-kit for Anthropic's plugin directory: gated specs and plans, /ship, /ship-fast and /handoff, with no hooks or scripts."}`.
- `tests/test_publish.py::test_marketplace_fields`: replace the line
  `[entry] = data["plugins"]` with
  `entries = {e["name"]: e for e in data["plugins"]}` and
  `entry = entries["agent-kit"]` (the existing four `entry` assertions
  stay), then add:

```python
    lite = entries["agent-kit-lite"]
    assert lite["source"] == "./lite"
    assert lite["description"].strip()
    assert "version" not in lite
```

- `.github/workflows/ci.yml`: `ruff check plugin tests scripts` and
  `ruff format --check plugin tests scripts`.
- `AGENTS.md`, Developing the kit: the code line becomes
  `ruff check plugin tests scripts; ruff format --check plugin tests scripts`,
  and add the bullet `- After editing `plugin/` or bumping its version, rerun
  `python scripts/build-lite.py` and commit `lite/`.` after the Vibe
  paragraph.

- [ ] **Step 6: Run everything and commit**

Run: `pytest; ruff check plugin tests scripts; ruff format --check plugin tests scripts`
Expected: no failures (including `tests/test_lite_build.py`, every
`tests/test_publish.py` test and `tests/test_docs.py::test_relative_markdown_links_resolve`);
ruff clean.

```bash
git add scripts/lite-README.md lite tests/test_lite_build.py tests/test_publish.py .claude-plugin/marketplace.json .github/workflows/ci.yml AGENTS.md
git commit -m "Generate lite/ (agent-kit-lite), its frozen test and marketplace entry"
```

---

### Task 7: Docs and ADR 0058

**Files:**
- Create: `knowledge/decisions/0058-directory-lite-plugin.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `knowledge/decisions/0055-directory-listing.md`
- Modify: `docs/directory-submission.md`
- Modify: `README.md`

**Depends on:** Task 6

- [ ] **Step 1: Write ADR 0058**

`# ADR 0058: A Markdown-only agent-kit-lite plugin, generated from plugin/, is what the directory lists`,
`- **Status:** accepted`, `- **Date:** 2026-11-28`, then `## Context`
(the portal's Validate on `main @ b0d0a63`: hooks only from Verified
organizations; only Markdown, text, JSON, YAML and images from unverified
ones; both unappealable), `## Decision` (spec D1 to D11 in one bullet
each: lite plugin, generated and drift-checked, scope, name, icon by the
agent with the user's approval, shared version, full-only and lite-only
comment blocks with a description override table, `agent-kit:` rewrite,
`template.html.txt` and `LICENSE`, frozen test, superpowers prerequisite),
`## Consequences` (every `plugin/` edit reruns the build and commits
`lite/`; lite gate records carry `lite-git:` ids the full kit treats as
stale; ADR 0055's decisions still hold for `plugin/`; only the submitted
path changes to `lite`). Link ADR 0055 as `[ADR 0055](0055-directory-listing.md)`.

- [ ] **Step 2: Index and ADR 0055**

Add the row
`| [0058](0058-directory-lite-plugin.md) | A Markdown-only agent-kit-lite plugin, generated from plugin/, is what the directory lists | accepted | 2026-11-28 |`
after the 0057 row in `knowledge/decisions/README.md`. In ADR 0055, below
its Date bullet, add
`- **See:** [ADR 0058](0058-directory-lite-plugin.md) (the directory is submitted the generated lite plugin; this ADR still holds for plugin/)`.
Its Status stays `accepted`.

- [ ] **Step 3: `docs/directory-submission.md`**

- Title: `# Submitting agent-kit-lite to Anthropic's plugin directory`; the
  intro says the directory lists `agent-kit-lite`, built into `lite/` from
  `plugin/` (ADR 0058), because the directory takes hooks and scripts only
  from Verified organizations.
- Before you start: the two checks become
  `claude plugin validate ./lite --strict` and
  `pytest tests/test_lite_build.py tests/test_directory_ready.py`; add the
  icon note: "The portal takes the icon (`lite/.claude-plugin/icon.png`)
  only the first time you save or submit the plugin; after that it is
  final."
- Source: `**Plugin path:** lite`, and a new bullet
  `**Plugin name:** agent-kit-lite`.
- Listing details: one-line summary `Spec-driven workflow for Claude Code:
  gated specs and plans, review, and /ship from spec to pull request.`;
  short description for lite (gates specs and plans, builds in git
  worktrees, reviews against the spec, ships with `/ship` and
  `/ship-fast`, writes handoffs; no hooks and no scripts; the full kit
  with hooks is on the repository's marketplace). Keywords unchanged.
- Data handling: rewrite the answers for lite: no telemetry; no hooks, so
  nothing runs on its own; `/ship` and `/ship-fast` fetch, push and open
  pull requests through the user's `git` and `gh` (`/ship` also merges);
  `pr-review-respond` runs one `gh api graphql` query and posts replies;
  local storage is handoff files under `.claude/handoffs/` written by
  `/handoff`; no credentials read or stored. Point to
  `[lite/README.md](../lite/README.md)` instead of `plugin/README.md`.
- After publishing: keep `tests/test_lite_build.py` passing; rerun the
  build after each `plugin/` change.

- [ ] **Step 4: `README.md`**

Under `## Install`, after the first paragraph's code block and before
"You need:", add a `### Two plugins` subsection: the full `agent-kit`
(this marketplace: hooks, scripts, every command) and `agent-kit-lite`
(Markdown only, generated into `lite/`, for Anthropic's plugin directory
once listed; `/plugin install agent-kit-lite@agent-kit` installs it from
this marketplace meanwhile), with a link to
`[ADR 0058](knowledge/decisions/0058-directory-lite-plugin.md)`.

- [ ] **Step 5: Run the docs tests and commit**

Run: `pytest tests/test_docs.py tests/test_publish.py`
Expected: pass (links resolve, ADR indexed, no bare `claude-kit`).

```bash
git add knowledge/decisions docs/directory-submission.md README.md
git commit -m "ADR 0058 and the directory guide for agent-kit-lite"
```

---

### Task 8: Manual checks (main session)

**Files:** none

**Depends on:** Task 6

This task changes no file and dispatches no subagent of its own beyond the
skills it runs; it runs in the main session and reports evidence.

- [ ] **Step 1: Lite in an isolated config (Success criterion 4)**

In Git Bash, with `<cfg>` and `<sample>` new folders in the scratchpad.
A new config folder has no sign-in: before the `claude -p` runs below, ask
the user to run `claude` once with `CLAUDE_CONFIG_DIR=<cfg>` set and log
in (never write a credential into the plan, the report or a file), then
continue.
`git init <sample>`, write a small valid spec
`<sample>/docs/superpowers/specs/2026-11-28-sample-design.md` (Status
`draft`, Date, Purpose, Scope with In and Out, Design, Decisions, Success
criteria with a `pytest` criterion) and commit it. Then:

Run: `CLAUDE_CONFIG_DIR=<cfg> claude plugin marketplace add <repo-root>/.worktrees/directory-lite` and `CLAUDE_CONFIG_DIR=<cfg> claude plugin install agent-kit-lite@agent-kit`
Expected: both exit 0; `<cfg>/plugins/installed_plugins.json` lists only
`agent-kit-lite@agent-kit`, and its install folder has no `hooks/`.

Run (in `<sample>`): `CLAUDE_CONFIG_DIR=<cfg> claude -p "/agent-kit-lite:spec-gate docs/superpowers/specs/2026-11-28-sample-design.md"`
Expected: the transcript shows the checklist applied by reading, no
`python` command, no hook output; `docs/superpowers/gates/2026-11-28-sample-design.md`
holds `- **Spec SHA-256:** lite-git:` followed by 40 hex characters.

Then set the spec's Status to `approved` and
Run: `CLAUDE_CONFIG_DIR=<cfg> claude -p "Run the Gate record check from agent-kit-lite's references/spec-lint-checks.md on docs/superpowers/specs/2026-11-28-sample-design.md, as /ship step 0 does, and print its result line."`
Expected: a line starting `ok:`.

- [ ] **Step 2: Full kit unchanged (Success criterion 5)**

In a fresh copy `<sample2>` of the same sample repo (Status back to
`draft`, no gate record), load this branch's full plugin, not the
session's own `agent-kit` (that one points at the main checkout's
`plugin/`): use a second new config folder `<cfg2>`, signed in by the user
as in Step 1, and run
`CLAUDE_CONFIG_DIR=<cfg2> claude plugin marketplace add <repo-root>/.worktrees/directory-lite`
and `CLAUDE_CONFIG_DIR=<cfg2> claude plugin install agent-kit@agent-kit`.

Run (in `<sample2>`): `CLAUDE_CONFIG_DIR=<cfg2> claude -p "/agent-kit:spec-gate docs/superpowers/specs/2026-11-28-sample-design.md"` then `python <repo-root>/.worktrees/directory-lite/plugin/scripts/spec-lint.py --verify-record docs/superpowers/specs/2026-11-28-sample-design.md`
Expected: `<cfg2>/plugins/installed_plugins.json` lists `agent-kit@agent-kit`
installed from the worktree's marketplace; the transcript shows
`spec-lint.py` running; the record's `Spec SHA-256` is 64 hex characters;
the last command prints `ok:`.

- [ ] **Step 3: Report**

Put a short transcript excerpt of each check in the run's report (and the
PR body), and delete `<cfg>`, `<cfg2>`, `<sample>` and `<sample2>`. Success criterion
6 (the portal's Validate at the merge commit) is the user's, after merge.
