# ADR 0058: A Markdown-only agent-kit-lite plugin, generated from plugin/, is what the directory lists

- **Status:** accepted
- **Date:** 2026-11-28

## Context
[ADR 0055](0055-directory-listing.md) made `plugin/` pass the directory's
pre-submission checklist. The portal's Validate step on `main @ b0d0a63`
(2026-11-27) then gave two blocking issues that cannot be fixed inside
`plugin/` and cannot be appealed:

- The directory accepts hooks of any type only from Verified organizations,
  and this account's organization is not Verified.
- From an unverified organization it accepts only Markdown, text, JSON, YAML
  and image files. Scripts must be removed, not renamed.

`plugin/` has 22 hook commands and 36 Python files, and most of its skills
and commands call a script, so it cannot be listed as it is.

## Decision
- **A lite plugin for the directory (D1).** A second plugin, made only of
  allowed files, is what the directory lists. Rejected: getting Verified
  first; not listing; submitting as-is and appealing.
- **Generated, committed and drift-checked (D2).** `scripts/build-lite.py`
  builds `lite/` from `plugin/`; `lite/` is committed and CI fails when it
  drifts from the build. Rejected: a hand-kept `lite/`; making `plugin/`
  itself Markdown-only.
- **Scope (D3).** Ten copied skills plus a generated `workspace-rules`
  skill, and `/ship`, `/ship-fast` (without scaffolding) and `/handoff`.
  Everything that only works with code is left out.
- **Name `agent-kit-lite` (D4).** Rejected: a new name, which is harder to
  connect to the full kit.
- **Icon (D5).** The agent draws the icon; it is committed only after the
  user approves it.
- **Shared version (D6).** The lite plugin carries the full kit's version
  number: one version per release.
- **Comment blocks in the sources (D7).** Lite differences live in
  `plugin/` as full-only and lite-only HTML comment blocks that the build
  applies; lite text never names a script. Frontmatter, where markers
  cannot sit, gets a table of lite `description` overrides in the build.
- **Skill name rewrite (D8).** The build rewrites `agent-kit:` to
  `agent-kit-lite:`, so names stay unambiguous when both plugins are
  installed.
- **Allowed file forms (D9).** `present`'s template ships as
  `template.html.txt`; `LICENSE` files without an extension are kept.
- **Frozen test (D10).** `tests/test_lite_build.py` is frozen, so later
  changes cannot weaken the directory checks to make a build pass.
- **Superpowers prerequisite (D11).** Lite requires the superpowers plugin,
  as the full kit does; `lite/README.md` says so.

## Consequences
- Every `plugin/` edit reruns `python scripts/build-lite.py` and commits the
  regenerated `lite/` in the same change.
- Lite gate records carry `lite-git:` document ids, which the full kit
  treats as stale, so a spec gated in lite is gated again by the full kit.
- ADR 0055's decisions still hold for `plugin/`; only the submitted plugin
  path changes, to `lite`.
