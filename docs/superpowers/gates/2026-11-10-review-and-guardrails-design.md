# Gate: Two-axis review, surgical diffs, frozen evaluators, Merge Danger and a hardening retro

- **Spec:** docs/superpowers/specs/2026-11-10-review-and-guardrails-design.md
- **Spec SHA-256:** 6fc05b191b1b9fbad2436eca0cfc63d7193e2cb959132ad02e3958a8d6d422c4
- **Verdict:** pass
- **Date:** 2026-11-10
- **Rounds:** 3 discovery + 1 verification

## Key decisions

- One spec carries the five items (two-axis review, surgical diffs, frozen evaluator, Merge Danger, hardening retro); the duplicate-function audit is a separate spec; both ship in one `/ship-many` run, in successive waves because they share `plugin.json`, `README.md` and the manifest test (D1)
- The retro is a Harden step inside `capture-learnings`, not a separate skill (D2, ADR 0043)
- Mechanical fixes are only proposed under `/ship`, `/ship-fast` and `/ship-many` children; a hand run builds them only after one yes (D3)
- The steering-bloat scan of `CLAUDE.md` reports only and never edits (Scope Out, Design §1)
- `claude-kit:review` runs on every `/ship` step 6 in addition to the superpowers final review, at an extra token cost; it amends ADR 0037 (D4, ADR 0041)
- The standards reviewer judges frozen files only from `frozen-check.py` output, never from the raw diff; process files are never scope creep (Design §2)
- Frozen files are enforced by a pre-push diff check and a stop rule, not a hook; frozen files not yet created are created once exactly as the plan gives them; deletion after creation is a violation (D5, Design §4, ADR 0042)
- The snapshot moves only on a `Frozen-change-approved:` trailer written by the main session after the user approves (D7)
- Reviewer-only standards live in `knowledge/review-standards.md` (with knowledge-layer frontmatter), never linked from `CLAUDE.md`; not created in this repo now (D8)
- Reviewers run on the session's model with no override (D9); nothing is frozen in this change (D10)
- `/ship-fast` gets Merge Danger and the frozen check (inert unless the user adds a Frozen bullet) and keeps its quick `code-review` (D6)
- The surgical-diff and simplicity rules become a workspace convention, part of the Definition of done and a PR-template checkbox; "ask when ambiguous" is limited to design and adds no check-in to `/ship` (Design §3, ADR 0044)
- PR bodies and both PR templates state the door, the blast radius and the smallest visual; one-way uses step 3a's irreversible test (Design §5, ADR 0045)
- No third-party plugin is installed and superpowers skills are not changed (Scope Out)
- The spec-gate rubric gains a minor check for a missing `Frozen:` bullet (Design §4)
- Minor version bump; ADRs 0041–0045, renumbered if any is taken on `origin/main` (Version, ADRs)

## Findings fixed

- round 1 [blocking] The reviewer's frozen rule would make `/ship` revert approved or newly created frozen files: the reviewer now gets `frozen-check.py` output and flags only its `changed` lines
- round 1 [blocking] Spec too large: D1 restated with the real reason (one coherent change; the user chose the split)
- round 1 [blocking] Surgical-diffs convention had no ADR: ADR 0044 added
- round 1 [blocking] Merge Danger convention had no ADR: ADR 0045 added
- round 1 [minor] `ship-fast` pushes live in `ship-fast-finish.md`; Scope lines moved
- round 1 [minor] ADR 0041 amends ADR 0037
- round 1 [minor] Dead-code rule versus the Definition of done qualified
- round 1 [minor] PR template wording aligned; D1 numbering fixed; D10 says nothing is frozen; typo and report reference fixed
- round 2 [blocking] Step 4's read-only constraint blocked creating frozen files the plan writes: files not yet existing are created once, exactly as the plan gives them
- round 2 [blocking] D1's parallel claim was false (shared Scope paths): successive `/ship-many` waves
- round 2 [minor] `knowledge/review-standards.md` frontmatter and index row; §2 bullet and PR template checkbox qualified; the kit's own PR template added to Scope; hardening reports through the Learnings summary; ADR renumbering wording; `/ship-many` children named
- round 3 [blocking] Deleting a frozen file created on the branch went undetected: the frozen set includes paths added anywhere in `base..HEAD`, with a test
- round 3 [minor] PR template Scope names the checkbox changes; D6 says `/ship-fast` Frozen bullets are added by hand; Scope lines for the step 12 and step 9 reports aligned
- after verify 1 [minor] Design §3 and `test_templates.py` now name the "diff is surgical" checkbox that Scope In listed

## Plan questions

- Does a single `*` stay inside one path segment, and does `**/` match zero directories? Add a test for each answer. (Design §4, Script)
- When several `Frozen-change-approved:` trailer commits name one path, does the last one win? (Design §4, Script)
- What does `/ship` (and `/ship-fast`) do when `frozen-check.py` exits 2: debug it with systematic-debugging and rerun? (Design §4)
- Is the approval an `--allow-empty` commit with one trailer per path, made after the change commit? (Design §4)
- Does the frozen check also run before the step 7 push and inside step 8's fix loop? (Design §4)
- Which path and fallback does `claude-kit:review` use for `frozen-check.py`; does it pass `--base <base>`; and with no spec or plan found, is the frozen check skipped and reported as such? (Design §2)
- Does the spec reviewer also treat files from the `Capture learnings` commit (CLAUDE.md, knowledge/) as process files? (Design §2)
- How does `pr-body.md` keep the existing `_step(7)` assertions in `tests/test_ship_command.py` passing (no column-0 numbered lists), and which ship-fast assertions read the reference directly, given `command_text` inlines only references named in the command file? (Design §5; Testing)
- How does `capture-learnings` tell a hand run from a run under `/ship`, `/ship-fast` or a `/ship-many` child (an argument passed by the commands, or another signal)? (Design §1)
- Where does the post-merge live check of `claude-kit:review` run (step 10's detached worktree before removal, or a fresh one), and is the skill followed from its file when the loaded plugin does not have it yet? (Success criterion 5)
- Is the rubric check a new numbered item under "What to check"? (Design §4, spec-gate)

## Open

- none
