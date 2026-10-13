# Gate: Kit map: make the kit's playbooks and ADRs reachable from child repos

- **Spec:** docs/superpowers/specs/2026-10-13-kit-map-design.md
- **Spec SHA-256:** fdc9b34c89af40a93941f50e9914a014d35aae6fe3085101f1f17b4bcc18ed04
- **Verdict:** pass
- **Date:** 2026-10-13
- **Rounds:** 2 discovery + 0 verification (third gate run, after rewording a link-like span that broke `test_docs.py`; earlier runs passed in 2 and 3 discovery rounds)

## Key decisions

- Inject a map of absolute paths at SessionStart and read playbooks on demand, instead of `@` imports or copying playbooks into child repos.
- No settings change for read access; permission prompts when Claude opens kit files from a child repo are accepted.
- On by default; `CLAUDE_KIT_KIT_MAP=0` switches it off.
- The kit root comes from the hook file's resolved path and is valid only when `<root>/conventions/README.md` exists; otherwise the hook prints nothing.
- The playbook list is parsed from the `conventions/README.md` table, so a new playbook needs no hook change.
- Registered as a no-matcher SessionStart group (startup, resume, clear, compact), after the lean-context group.
- Spec-gate check 8 drops the `../conventions` fallback; the main session passes the decision-log path (or `none`) in the discovery-round dispatch prompt, because subagents get no SessionStart output.
- Workspace `CLAUDE.md` rules for repos cloned outside the kit folder, and the teammate setup, go to a separate "team setup" spec.
- Recorded as ADR 0032 (0031 was taken by capture-learnings), which amends ADR 0027; plugin version 0.23.0.

## Findings fixed

- first gate, round 1 [blocking] Rubric change breaks an existing test the spec does not list: `tests/test_spec_gate_skill.py` added to Scope In and Testing.
- first gate, round 1 [blocking] The spec-gate reviewer subagent never sees the kit map: `spec-gate/SKILL.md` dispatch prompt carries the decision-log path; rubric reads it from the prompt.
- first gate, round 1 [minor] "Keep the main context" is not a heading: Scope says principle 3 under `## Principles`.
- first gate, round 2 [minor] Child repo named in a tracked file: live check says "a child repo under the kit folder".
- first gate, round 2 [minor] Token estimate vs size cap: ADR says 250 to 400 tokens.
- round 1 [blocking] Scope In leaves out files the change has to touch: added `knowledge/decisions/README.md`, `README.md` (hook count and list), `plugin/.claude-plugin/plugin.json` (0.23.0, description).
- round 1 [minor] Map sentence omits `plugin/`: folder list is now "e.g. conventions/, knowledge/, plugin/".
- round 2 [blocking] Version bump breaks an existing test not in Scope: `tests/test_plugin_manifest.py` added to Scope In and Testing (version test renamed, description test added).
- round 3 [minor] Lean-context pointer dangles when the map is off: ADR notes it is accepted.
- round 3 [minor] ADR summary omits the rubric change: ADR summary now mentions it.
- third run, pre-review: a link-like code span in Design step 3 failed `test_relative_markdown_links_resolve`: reworded (and the label rule is now explicit: link text verbatim).
- third run, round 1 [blocking] ADR 0027 is amended but not marked: 0027 file and index row added to Scope In ("accepted; amended by 0032"); ADR 0032 summary says it amends 0027.
- third run, round 1 [minor] "line 45" locator: replaced by a quote of the sentence.
- third run, round 1 [plan, settled in spec] Junction creation and teardown: `cmd /c mklink /J`, skip on non-zero exit or `OSError`, teardown removes only the link (never recursive). Table parse limited to `## The playbooks`.

## Plan questions

- Where does the dispatch-prompt sentence go in the blockquote, and is `none` substituted literally? (Design, Ad-hoc pointers)
- With zero playbook rows, is the "Playbooks ..." sentence omitted? What exact string, including newlines, does the hook build? (Design, The hook)
- Does a test assert the new lean-context pointer wording? (Testing)
- Is `<path>` defined inline in step 2 or also as a Setup entry in `spec-gate/SKILL.md`? (Design, Ad-hoc pointers)
- What regex matches a playbook row? (Design, The hook)
- Does the on-by-default test parse the README independently of the hook's parser? (Testing)
- Where in the README hook-list sentence does the kit-map entry go? (Scope In, README.md)

## Open

- none
