# Plan gate: Agent-agnostic kit Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-18-agent-agnostic-kit.md
- **Plan SHA-256:** 434089f69d586153e84e721d226cf89404b012d3b0331c4e2a8e45047a9515b4
- **Spec:** docs/superpowers/specs/2026-11-18-agent-agnostic-kit-design.md
- **Spec SHA-256:** 9d61bd4a48c1194bd0e57f037ef5aa87d609949fb91e451d3e2087a4acc0b62d
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-22
- **Approved by:** /ship (auto)
- **Date:** 2026-11-22
- **Rounds:** 3 discovery + 2 verification

## Plan-introduced decisions

- `run.py` parses each `hooks.json` command with `shlex.split` (no shell) and swaps a leading `python`/`python3` for `sys.executable`, the installer's `--python` (Task 2)
- Each hook script runs with its process cwd set to the event `cwd` (else `run.py`'s cwd), not the project top level (Task 2)
- The project directory is the git top level of the cwd, else the cwd; it feeds `CLAUDE_PROJECT_DIR` and the project `CLAUDE.md`/`AGENTS.md` lookup (Task 2)
- A missing `source` becomes `startup` for every agent, not only Cursor (Task 2)
- No cap or truncation on the joined context (Task 2)
- The tool mapping and the project `CLAUDE.md` are injected only at SessionStart, never at Stop (Task 2)
- A missing `@path` import in a project `CLAUDE.md` is kept as written; wording of the project-instructions header for `CLAUDE.md`-only repos (Task 2)
- Non-Claude agents get their own workspace-rules header ("Your agent did not load them for this repo; follow them as you would an AGENTS.md") in every repo it injects in, including outside the kit folder; Claude's header changes only in the file name (Task 1)
- `--home` is the base of every default, including `--agent claude` (`<home>/.claude/skills`, `<home>/.claude/settings.json`); explicit `--skills-dir`/`--settings` win (Task 5)
- For non-Claude agents the installer skips the status line and the superpowers warning (Task 5)
- On rerun the installer removes dangling links that point under the kit's three skill roots, and relinks a kit link that points at another kit folder (`Relinked <name>`) (Task 5)
- A malformed JSON hook file aborts the whole agent install with exit 1 and no change, links included (Task 5)
- Managed-block markers in `~/.vibe/hooks.toml` and the user `AGENTS.md`; JSON kit entries identified by a command containing `/plugin/hooks/run.py"` and `--agent ` (Task 5)
- The bundle pins upstream superpowers 7.0.2 from the local plugin cache; the vendor script rebuilds `vendor/superpowers/skills` and exits 1 on an unknown skill name (Task 3)
- Vendored shebang scripts are committed as executable (`100755`) via `git update-index --chmod=+x` (Task 3)
- SC1 captures: each checkout is its own kit-repo project plus one shared temporary repo outside the kit, both checkout roots replaced by `<kit>` (Task 8)
- The executor stops at Task 8 Step 5 for the user to run SC4 to SC6; the branch does not merge until each has a recorded result (SC6 failure with the fallback result counts); only SC7's live check stays pending (Task 8)

## Findings fixed

- round 1 [blocking] Claude header replacement ambiguous: only the path changes to `from {where}/{name})`; "as you would a CLAUDE.md" stays, with a test assertion
- round 1 [blocking] No task checked SC4 to SC6: Task 8 Step 5 now stops for the user to run them and records results before merge; only SC7 pending
- round 1 [blocking] Vendored scripts lose the executable bit from Windows: Task 3 Step 6 sets `+x` on shebang files; new test checks `100755`
- round 1 [minor] Task 1 Step 4 expected-failure list completed
- round 1 [minor] `agent-skills.py --out` default made cwd-independent
- round 1 [minor] ADR number fallback also updates docstrings from Tasks 1 and 2
- round 2 [blocking] `agent-skills.py --check` CRLF comparison: reads with universal newlines; new CRLF test case
- round 2 [minor] Tool mapping must avoid the runner tests' sentinel strings
- round 2 [minor] Task 3 Step 6 command runs in Bash and passes posix paths to git
- round 2 [minor] Existing install tests stay unedited as the guard for today's behaviour
- round 3 [blocking] PowerShell wrapper test now asserts every `Wrote`/`Unchanged` path is under `tmp_path` and the `Linked` count matches the links in `tmp_path/.agents/skills`
- round 3 [minor] `git add CLAUDE.md` added to Task 1 Step 1
- round 3 [minor] Wrapper's first argument stays `(Join-Path $PSScriptRoot "install.py")`
- round 3 [minor] Kit link to another kit folder is relinked (`Relinked <name>`)
- verify 1 [blocking] Task 1 Step 1 expected git status corrected to `new file: AGENTS.md` / `modified: CLAUDE.md`, plus a text-mode check that `AGENTS.md` equals `git show HEAD:CLAUDE.md`; relink behaviour recorded in the plan's decisions

## Open

- none
