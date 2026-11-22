# Gate: Agent-agnostic kit: run the kit in Mistral Vibe, Codex and Cursor

- **Spec:** docs/superpowers/specs/2026-11-18-agent-agnostic-kit-design.md
- **Spec SHA-256:** 9d61bd4a48c1194bd0e57f037ef5aa87d609949fb91e451d3e2087a4acc0b62d
- **Verdict:** pass
- **Date:** 2026-11-18
- **Rounds:** 3 discovery + 2 verification

## Key decisions

- Approach B: one source adapted per agent, through a cross-agent hook runner (`plugin/hooks/run.py`) that reads `plugin/hooks/hooks.json` as the single hook list (D1, D2)
- The kit root rules move to `AGENTS.md`; `CLAUDE.md` becomes the one-line `@AGENTS.md` stub (Design: Instructions)
- Claude wording is mapped for other agents through one reference file (`plugin/references/agent-tools.md`, with `<plugin>` filled in by the runner, the `~/.claude/skills/claude-kit` rule and `code-review` → `requesting-code-review`); kit skill and command text is not edited (D3)
- A pinned copy of the upstream MIT superpowers skills is vendored under `vendor/superpowers/`, outside `plugin/skills/`, for non-Claude agents only; scan set `plugin/**/*.md`, `AGENTS.md`, `conventions/*.md` (D4)
- Existing project repos keep `CLAUDE.md`, injected by the runner; project-repo instruction files are a later spec (D5, D8)
- `/ship-many`, statusline, token-report, `audit --user`, transcript, precompact and spec-edit hooks stay Claude-only; `/ship` and `/ship-fast` run in one session elsewhere, with subagents per the mapping (D6)
- Vibe, Codex and Cursor all ship in this version; Codex is tested now and checked live once installed (D7)
- Non-Claude agents get the workspace rules injected in child repos inside the kit folder, accepting a duplicate in Vibe sessions that trust the kit folder (D9)
- Nothing is frozen; the Claude-unchanged check diffs against `origin/main` in a scratch directory, never a committed fixture (D10)
- `capture-learnings` writes to `AGENTS.md` when root `CLAUDE.md` is only `@AGENTS.md` (D11)
- Everything installs at user level; `~/.agents/skills/` is the single skills target; agents' user hook files are merged idempotently; `install.ps1` gains `-Agent` and `-Home`
- Generated, committed wrapper skills, one per command except `ship-many`, `disable-model-invocation: true`
- New ADR amending ADRs 0034 and 0035; minor version bump

## Findings fixed

- round 1 [blocking] Baseline fixture embeds machine paths and state: Success criterion 1 now captures from `origin/main` and the branch into a scratch directory, compares with `<kit>` placeholders, summarised in the PR; the fixture was dropped and a stub-equivalence test added
- round 1 [blocking] Rule injection inside the kit folder contradicted Vibe's native loading: rewritten (later superseded by D9); kit root and kit worktrees silent for every agent
- round 1 [blocking] Committed wrappers could not hold an install-time path: wrappers use `<plugin>`, resolved through the injected mapping; installer links them unchanged
- round 1 [blocking] Adopt mode would split instruction files: project-repo instruction-file work moved out to a later spec (D8)
- round 1 [blocking] Spec covered two subsystems: split; project-repo convention changes are Out (D8)
- round 1 [minor] No Frozen bullet: D10 says nothing is frozen and why
- round 1 [minor] Cursor fire-and-forget sessionStart: installer report gives a paste-into-user-rules fallback; SC6 records failure if context does not arrive
- round 1 [minor] "Inline" in D6: reworded to one session, no headless children, subagents per the mapping
- round 2 [blocking] SC4 expected gates from /ship-fast: check is now the PR and subagent use in the transcript
- round 2 [blocking] `~/.claude/skills/claude-kit` fallback covered two files only: mapping rule made general, with a test
- round 2 [blocking] Superpowers closure source undefined: scan set named exactly; script and test use it
- round 2 [blocking] Vibe child repos relied on a trusted kit folder: D9 injects for every non-Claude agent
- round 2 [blocking] `code-review` built-in undefined outside Claude: mapped to `requesting-code-review` on the branch diff
- round 2 [minor] Cursor name rule tested for wrappers only: extended to every linked folder
- round 3 [blocking] install.ps1 forwarded the Claude skills dir: forwards only explicit `-SkillsDir`/`-Settings` for non-Claude agents, with a wrapper test
- round 3 [blocking] Existing tests reading kit CLAUDE.md out of scope: added to Scope In, plus a stub assertion
- round 3 [blocking] capture-learnings target in the kit repo: D11, body-only edit with a test
- round 3 [blocking] Vendor test described as writing files: script copies, test only checks
- round 3 [minor] ADRs 0034/0035 amended but not marked: marked "amended by" the new ADR
- verify 1 [blocking] Wrapper test could write to the real home: `install.ps1 -Home` forwarded as `--home`; test sets `HOME`/`USERPROFILE` to `tmp_path` and asserts all writes stay there

## Plan questions

- Does `run.py` run each `hooks.json` command through a shell or parse it, and does it swap the leading `python` for `sys.executable` or the installer's `--python`? (Design: Hook runner)
- Does `run.py` start each script with `cwd` set to the project directory (`worktree_audit.py` reads `Path.cwd()`)? (Design: Hook runner)
- Is the project directory the event `cwd` or its git top level? (Design: Hook runner)
- Should a missing `source` default to `startup` for every agent, not only Cursor? (Design: Hook runner)
- Does the runner cap or truncate the joined context? (Design: Hook runner)
- What workspace-rules header wording applies for non-Claude agents in repos inside the kit folder, keeping Claude's header byte-identical apart from the file name? (Design: Hook runner)
- Does `make_link` gain a `target` parameter or get a sibling helper? (Design: Installer)
- How do `--skills-dir` defaults derive from `--agent` and `--home`, and does `--home` apply to `--agent claude`? (Design: Installer)
- Are dangling kit-owned links in `~/.agents/skills/` removed on rerun? (Design: Installer)
- How are kit entries found and replaced in `~/.vibe/hooks.toml` (no stdlib TOML writer) and in the JSON hook files; what marker format does the user `AGENTS.md` block use? (Design: Installer)
- For Success criterion 1, do both captures use one fixed project cwd so only the checkout's `plugin/hooks` varies? (Success criteria)

## Open

- none
