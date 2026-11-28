# Gate: A Markdown-only `agent-kit-lite` plugin for Anthropic's plugin directory

- **Spec:** docs/superpowers/specs/2026-11-27-directory-lite-design.md
- **Spec SHA-256:** e9f8a61fc6ecc31d68fa9b28b1885a694c399ad62c2244e4a3eb87bfa5720295
- **Verdict:** pass
- **Date:** 2026-11-27
- **Rounds:** 3 discovery + 2 verification (rerun; the first run, 3 + 2 rounds and 20 fixes, ended `fail` on one unverified last fix)

## Key decisions

- Ship a second, Markdown-only plugin `agent-kit-lite` for the directory instead of getting Verified or appealing (D1)
- `lite/` is generated from `plugin/` by `scripts/build-lite.py`, committed, and drift-checked in CI through a frozen test; `--check` normalises CRLF for text files (D2, D10, Build)
- Lite scope: 10 skills plus a generated `workspace-rules` skill, and `/ship`, `/ship-fast` (no scaffolding) and `/handoff`; all hooks and code-only features are dropped (D3)
- Name `agent-kit-lite`, expected to clear the "Talentkit" similarity refusal; appeal is the fallback (D4)
- The agent drafts the icon and the user approves it before commit; the portal fixes it at first save (D5)
- Lite carries the full kit's version number (D6)
- Lite differences live in `plugin/` sources as full-only and lite-only comment blocks; every lite-only opener tells agent-kit to ignore it; lite text never names a script; frontmatter differences go through a description override table in the build (`grill`, `audit`, `ship-fast`) (D7)
- The build rewrites `agent-kit:` to `agent-kit-lite:`; names must be a lite skill or command (D8)
- `template.html` ships as `template.html.txt`; extensionless `LICENSE` files are kept (D9)
- Lite requires the superpowers plugin (D11)
- Lite gate records carry `lite-git:<id>` ids (a plan record carries both plan and spec ids); lite `/ship` mirrors `verify_record` / `verify_plan_record`, including `pass-with-decisions` with the ADR 0036 approval line
- In lite, L9-coverage applies only when the spec has a `## Coverage` section
- The built-text check is a fixed list: kit script and hook file names, `hooks.json`, `CLAUDE_KIT_GRILL`, `kit map`, flagged install and variable patterns, excluded `/<command>` names, and paths starting `~/` or `%USERPROFILE%`
- README and icon sources live in `scripts/`, outside `plugin/`
- `tests/test_publish.py` looks up `agent-kit` by name; `.gitignore` whitelists `lite` and `scripts`; ADR 0058 added; ADR 0055 stays accepted with a "See ADR 0058" line

## Findings fixed

- round 1 [blocking] Lite rule for L9-coverage undefined: "L9 in lite" paragraph; lite-only blocks in spec-lint-checks.md and spec-driven-development.md
- round 1 [blocking] Lite `/ship` plan-record check dropped `pass-with-decisions` and the spec id: plan records carry both ids; lite check mirrors `verify_record` and `verify_plan_record`
- round 1 [minor] Marker list omitted known flagged sources: five files added to Scope In
- round 2 [blocking] Lite frontmatter advertised features lite lacks: override table keyed by skill or command with `grill`, `audit`, `ship-fast`; checks for excluded `/<command>` names and home-relative paths
- round 2 [minor] Name refusal assumed cleared; `.claude` folder wording: reworded
- round 3 [blocking] `--check` byte comparison fails on CRLF checkouts: text compared with CRLF normalised; SC2 CRLF-copy assertion
- round 3 [blocking] `plugin/references/lite-README.md` broke an existing test: README and icon sources moved to `scripts/`
- round 3 [minor] ADR 0055 status, AGENTS.md ruff commands, Frontmatter wording: fixed
- verify 1 [blocking] SC2 CRLF copy would convert the icon: only text files are converted

## Plan questions

- `$1` and positional parameters under the `$VAR` ban (Checks on the built text)
- The lite GraphQL query: inline placeholders instead of `$owner`/`$name`/`$number`, and pagination (Design table, `pr-review-respond`)
- The exact portable grep/sed pipeline for the lite id (GNU and BSD sed, Git Bash), fence handling, CR stripping, and fixtures with a fenced Status line and a CRLF file (Lite document id)
- How `spec-lint-checks.md` defines P4 for lite (Design table)
- Where lite `/ship-fast` writes the Docker baseline and new-repo spec, now that `~/` paths are banned (Design table, `/ship-fast`)
- Where lite-only text goes when `ship.md`/`ship-fast.md` near the 20,000-byte limit or lean-context nears 60 lines; keeping exact fallback sentences and existing text tests intact (Scope In)
- Whether the link check accepts a folder target and strips `#anchor` (Rules as a skill)
- Whether a backticked file name the build omits (such as `user-mode.md` in `audit/SKILL.md`) fails the build or is left to the marker edits (Checks on the built text)
- How lite `/handoff` builds the State section and turns a branch name with `/` into a file name (Design table, `/handoff`)
- Where lite `present` and `audit` get the deck and citation rules now in `check-deck.py` and `check-findings.py` (Design table)
- Reference discovery runs on built text, after markers (Build)
- PNG size check with the standard library (Success criteria 2)

## Open

- none
