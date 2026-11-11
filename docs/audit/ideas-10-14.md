# Ideas 10–14: which are worth adding

Read-only evaluation, 2026-11-10. Nothing installed, no tracked file edited. Sources read through `gh api`; kit files read in the main checkout. Estimates are labelled as estimates.

## Verdicts

| # | Idea | Verdict | Smallest change | Cost |
|---|---|---|---|---|
| 10 | episodic-memory | **Skip** | none | high setup, 1.7 GB duplicate archive, open Windows bugs |
| 11 | Keep failed approaches through compaction | **Borrow the hook design** (not the plugin) | one new PreCompact hook | ~0 tokens, ~40 lines of Python |
| 12 | Stop-judge for `/ship` (double-shot-latte) | **Skip** | none | a Claude call every turn, needs `jq` |
| 13 | Wayfinder | **Skip** (revisit if a project outgrows one spec) | none | needs a tracker setup |
| 14a | Rejected-ideas record | **Borrow, tiny**: ADR status `rejected` | 3 files | ~0 |
| 14b | GLOSSARY.md + domain-modeling | **Borrow, lazy**: optional glossary rule | 2 files | ~0 until a repo has one |

## Ranked shortlist

1. **11. PreCompact hook** that tells the compaction summary to keep dead ends. Cheapest, no new moving parts, fixes a real (if infrequent) loss.
2. **14a. `rejected` ADR status.** Gives "we looked at X and said no" a home, which is exactly what this survey produces. Three one-line edits.
3. **14b. Optional glossary rule.** Worth it only for domain-heavy repos. Lazy, so costs nothing elsewhere.
4. Skip 10, 12 and 13, for the reasons below.

---

## 10. episodic-memory — skip

**What it is** (`obra/episodic-memory` v1.6.0, README, `hooks/hooks.json`, `src/paths.ts`): a Node/TypeScript plugin. A `SessionStart` hook (`startup|resume|clear`) runs `episodic-memory sync --background`. Sync copies every transcript from `~/.claude/projects` (and Codex, Cursor, opencode, OMP dirs) into `~/.config/superpowers/conversation-archive`, writes a SQLite index at `…/db.sqlite` with `sqlite-vec` embeddings (local model `Xenova/bge-small-en-v1.5` via Transformers.js), and calls Haiku to write a summary per conversation (up to 10 per sync). An MCP server exposes `search` and `read`; the `remembering-conversations` skill and a `search-conversations` subagent drive it.

**Windows 11 with this setup: shaky.**
- Native deps (`better-sqlite3`, `onnxruntime-node`) need a working prebuild or a compiler. `scripts/postinstall.js` exists because the install path was broken on Windows (issues #95, #100). I did not install it to test.
- This machine runs Node through **nvm** (several versions on PATH). Open issue #49: "MCP server fails to start/connect in Claude Code on Windows with nvm".
- Other open Windows issues: #202 (same conversation indexed under two path spellings, `C--` vs `c--`), #199 (orphan `.jsonl.tmp.<pid>` copies pile up), #211 and #182 (child processes pop up console windows), #186 (test suite fails on Windows).

**What it indexes and the privacy footprint.**
- Everything: this machine has about 1,256 transcript files (211 top-level sessions plus subagent files), 1.7 GB under `~/.claude/projects`. The archive is a second full copy, outside the repo and outside any project's gitignore.
- Transcripts here include job-application material, personal vault planning and private-repo work. The archive is plain text.
- Secret redaction is **not merged**: PR #187 ("Redact secrets before they reach the archive, index, embeddings and summaries") is open. Until then pasted keys sit in the archive and go to the summariser.
- Summaries run through Claude on your subscription (it warns if `ANTHROPIC_API_KEY` is set and bills metered). Set `EPISODIC_MEMORY_SKIP_SUMMARIES=1` to avoid that; embeddings and search stay local.

**Token cost per session (estimates, not measured).**
- A skill entry whose description says "You MUST invoke this skill before saying 'I don't know'": about 100 tokens listed, but it encourages a subagent search whenever the model is unsure. Each search is a subagent run, plausibly 5–20k tokens.
- Two MCP tool definitions, a few hundred tokens.
- A background Node process on every start, resume and clear, next to the six SessionStart hooks the kit already runs.

**Overlap with what you have.**
- Auto-memory (`MEMORY.md`, 22 entries) holds the durable facts and corrections.
- `/handoff` (`plugin/hooks/handoff_inject.py`, 7-day window, per branch) carries state between sessions.
- ADRs hold decisions with context; `capture-learnings` at `/ship` step 7 writes the "why" at feature finish.
- episodic-memory would fill one gap: reasons that were never written down anywhere. That is real, but the kit's own answer is to write them down at the moment (ADR triggers, ADR 0027).
- [ADR 0009](../../knowledge/decisions/0009-no-service-backed-memory.md) already decided "files plus Python hooks, no index service, no ingestion cost", and says to revisit only if re-measurement shows recall, not carry-over, is the dominant cost. Nothing here shows that.
- This Claude desktop app already has transcript search (`search_session_transcripts`) with no install. If you want to recover a past decision once in a while, use that.

**Verdict: skip.** Revisit if (a) #187 and the nvm and path-spelling issues close, and (b) you can name two or three real cases where you needed a lost rationale that no ADR or memory held. A cheap alternative if you want recall: `Grep` over `~/.claude/projects/<project>/*.jsonl` on demand.

---

## 11. Keep failed approaches through compaction — borrow the design, skip the plugin

**What it is** (`obra/cc-plugin-decision-log`, README, `.claude-plugin/hooks.json`, `server/src/hook-helpers.ts`): an MCP server with seven tools (`log_decision`, `open_problem`, `log_approach`, `close_problem`, `get_context`, …) that write JSON under `~/.claude/decision-log/<project-slug>/`, plus two hooks. `PreCompact` reads the latest session's problems and decisions and emits them; `SessionStart` says prior decisions exist.

**Why not install it.**
1. It only helps if the model **chooses to call** `open_problem` and `log_approach` while working. Nothing captures dead ends automatically.
2. Its PreCompact hook returns `{continue, suppressOutput, systemMessage}`. Per the current Claude Code hooks reference, PreCompact **discards `systemMessage` and `continue`**; what counts is plain stdout, which becomes "instructions for the compaction summary" (cap 10,000 chars). So the injection path is likely dead as written. I read the docs and the source but did not run it.
3. It picks "the latest session dir by mtime", not the current session, so parallel sessions can cross over.
4. The README says "barely tested in real Claude Code sessions". Eight commits, last push 2026-02-17, 25 stars.
5. Runs through `bash` plus a committed `dist/` Node build; seven MCP tool definitions in every session.

**What the kit has** (`plugin/hooks/`):
- `handoff_snapshot.py` (SessionEnd): refreshes the branch handoff's State only. No dead ends.
- `context_nudge.py` (UserPromptSubmit): at 300k tokens, suggests `/handoff` then `/clear`.
- `lean_context_inject.py` (SessionStart): static token-discipline rule.
- There is **no PreCompact hook**. Compaction is left entirely to the default summary.

**How often it matters.** On this machine, 22 of 211 top-level sessions (about 10%) contain a compaction, 54 events in total. The nudge already steers long sessions toward `/handoff` + `/clear`. So the loss is real but small. That argues for the cheapest possible fix.

**Smallest change: a PreCompact hook that steers the summary** (the supported mechanism):
- New `plugin/hooks/precompact_keep.py`, same shape as `lean_context_inject.py` (always exit 0, ADR 0007). It prints a short instruction to stdout, for example: *"When summarising, keep: approaches already tried and why each failed or was rejected; open problems; decisions the user confirmed; the branch handoff path."* Optional: also print the branch handoff's Next section if one exists, via `handoff.py` as `handoff_inject.py` does.
- `plugin/hooks/hooks.json`: add a `PreCompact` entry.
- `tests/`: one test that the hook prints under 10,000 characters and exits 0.
- Optional line in `conventions/session-hygiene.md` naming the hook.
- Cost: no model call, no storage, about 60 tokens injected into the compaction prompt only. Env switch `CLAUDE_KIT_PRECOMPACT=0` for parity with ADR 0014 if you want one.
- Risk to check when building: whether `hooks.json` in the parallel session's worktree is being edited (merge conflict), and one live compaction to see the summary actually keeps the dead-ends list. Dead ends in the summary are only as good as the summariser; this raises the odds, it does not guarantee them.

**Verdict: borrow the design, not the plugin.**

---

## 12. Stop-judge for `/ship` — skip

**What it is** (`obra/double-shot-latte` v1.2.0, `hooks/claude-judge-continuation`, `hooks/hooks.json`, `hooks/run-hook.cmd`): a Stop hook, in bash. On every stop it reads the last four transcript lines, runs `claude --print` with Haiku as a classifier, and blocks the stop if the judge says to continue. Throttled to 3 continuations per 5 minutes; 30 s timeout; needs `jq`.

**Do `/ship` runs stall that way? No evidence.** I scanned all 54 sessions on this machine that ran `/ship` or `/ship-many`: 3,719 assistant text messages, **zero** ending in a "shall I continue / proceed / go ahead?" pattern. `plugin/commands/ship.md` already says "Do not ask for confirmation at any step" and that its Stop rules override any ask inside the skills it calls. `/ship-many` children run headless, where nobody could answer anyway. The scan used a phrase list, so a differently worded stall would not show, but the volume makes a real stall problem unlikely.

**Why it would be a bad fit anyway.**
- Cost: a Claude call and several seconds on **every** turn end in every session where the plugin is on, not only in `/ship`. Estimate, not measured.
- It is "aggressive continuation" by design. The workspace rule (`CLAUDE.md`, "Verify key decisions with me") wants the agent to stop on key decisions. A judge that errs toward continuing works against that. Its own prompt says default to stop when uncertain, but its README says the opposite stance.
- Windows needs: `jq` (**not installed here**; Git Bash is) plus the `run-hook.cmd` wrapper. Its 1.2.0 changelog lists a string of Windows hook fixes.

**How to fold it into `/ship` if it ever becomes a problem** (not recommended now): a Stop hook in `plugin/hooks/hooks.json` that does nothing unless `/ship` has written a marker such as `.claude/ship-active` (and removes it in its cleanup step). It would use `stop_hook_active` to avoid loops and `hookSpecificOutput.additionalContext` to continue. Python, no `jq`. Touches `plugin/hooks/hooks.json`, a new `plugin/hooks/ship_continue.py`, `plugin/commands/ship.md` (set and clear the marker), and ship.md is near its 20,000-character cut after #51, so the edit would need room.

**Verdict: skip.** Revisit only if you see a real stall in `/ship`; then fix the wording in `ship.md` first.

---

## 13. Wayfinder — skip

**What it is** (`mattpocock/skills`, `skills/engineering/wayfinder/SKILL.md`, `disable-model-invocation: true`): a map issue labelled `wayfinder:map` with Destination, Notes, Decisions so far, **Not yet specified** (fog) and Out of scope; child tickets typed `research`, `prototype`, `grilling` or `task`, each sized for one ~100K-token session, blocked through the tracker's native dependencies. One ticket resolved per session (research excepted); the map ends when the way is clear and you hand off to a spec. It depends on a configured issue tracker (`/setup-matt-pocock-skills`), defaulting to local markdown.

**Against the kit's flow.**
- The kit already has the pieces: brainstorming and `claude-kit:grill` for the open decisions, a spec with explicit `## Out of scope` (`conventions/spec-driven-development.md` lines 68 and 97–100), and `/handoff` between sessions.
- The knowledge layer's "make gaps visible" rule (`conventions/knowledge-layer.md`, principle 4) gives every canonical doc an **Open questions** section. That is the kit's version of the fog.
- Wayfinder's unique value is coordinating many sessions on one effort too large for a spec. The kit's answer to size is `/ship-many` over several specs.

**Would your larger projects use it today?** No. The investment project already has two specs; the run-pipeline spec is approved and gated, and the next step is `/ship`. The benchmark effort has approved task files and a defined next run. Both are past the fog stage. There is no map-shaped problem on the list right now.

**Cost if adopted:** an issue-tracker setup per repo, a new vocabulary, and a second place to hold decisions beside ADRs and specs. The map "is an index, not a store" and each decision lives in one ticket, which is a different home than the kit's one-home-per-fact in `knowledge/`.

**Cheap borrow I considered and rejected:** a "Not yet specified" heading in spec templates. The Open questions rule covers it.

**Verdict: skip.** Revisit when an effort needs more than three or four specs and you cannot say what the later ones are.

---

## 14. Rejected-ideas folder and glossary — borrow two small pieces

**What Pocock has** (`mattpocock/skills`): `.out-of-scope/*.md` (one file per rejected concept, with reasoning and a "Prior requests" list; read during triage to de-duplicate new issues; `skills/engineering/triage/OUT-OF-SCOPE.md`), `GLOSSARY.md` (opinionated terms with `_Avoid_` aliases, no implementation detail, created lazily; `skills/engineering/domain-modeling/GLOSSARY-FORMAT.md`) and a `domain-modeling` skill that challenges terms during design and offers an ADR only when a decision is hard to reverse, surprising and a real trade-off.

**What the kit has.**
- ADRs (`knowledge/decisions/`, `conventions/decision-log.md`) with MUST/SHOULD/NOT REQUIRED triggers (ADR 0027). ADR status is `proposed | accepted | superseded` (`0000-template.md`).
- Specs record rejected alternatives under **Decisions** and out-of-scope work under **Scope**.
- The knowledge layer (`conventions/knowledge-layer.md`) and the project scaffold (`plugin/templates/project/knowledge/`) have no glossary.
- `plugin/skills/teach/GLOSSARY-FORMAT.md` is a glossary format for teaching workspaces only.
- `claude-kit:grill` is already adapted from Pocock's `grilling` skill and says so.

### 14a. Rejected ideas: use ADRs with status `rejected`, not a new folder

Gap: a feature or idea that was considered and refused has no ADR when it is not a decision that changes the repo. This survey is a live example: ten-odd ideas, several skipped, nothing recording why. Pocock's folder exists mainly to de-duplicate outside issue reporters; your repos are solo and private, so the dedup value is thin. The reasoning-preservation value is real and the ADR log already does that.

**Smallest change:**
- `knowledge/decisions/0000-template.md` and `plugin/templates/project/knowledge/decisions/0000-template.md`: Status line becomes `proposed | accepted | rejected | superseded`.
- `conventions/decision-log.md`: one sentence: "Record an idea that was seriously considered and refused as an ADR with status `rejected`; check the log before reopening one." Also in `plugin/templates/project/knowledge/decisions/README.md` (a test keeps the trigger sections identical, so edit both the same way).
- Cost: nothing at runtime; ADRs are read only when relevant. Maintenance: one file per refused idea, written only when it was a real trade-off.

### 14b. Glossary: optional, lazy, read by grill

Worth it for domain-heavy repos (the halal-screen vocabulary in the investment project, the clinic domain terms in a client repo). Not worth a scaffold file everywhere: an empty glossary is noise, and Pocock's own skill creates it lazily.

**Smallest change:**
- `conventions/knowledge-layer.md`: a short "Glossary (optional)" section: `knowledge/GLOSSARY.md`, terms specific to this project only, one or two sentence definitions, an `_Avoid_` line per term, no implementation detail; create it when the first term is resolved.
- `plugin/skills/grill/SKILL.md`: one line telling the interviewer to read `knowledge/GLOSSARY.md` if it exists and to challenge terms that conflict with it.
- No new template file, no new skill. The `domain-modeling` skill itself is skipped: its "offer an ADR only when" test duplicates ADR 0027, and the rest is what `grill` already does.
- Cost: about nothing on repos without a glossary; on repos with one, the file size (keep it short) whenever grill runs.

**Verdict:** 14a borrow (tiny), 14b borrow (lazy). Neither is urgent.

---

## Files each build would touch

- **11:** `plugin/hooks/precompact_keep.py` (new), `plugin/hooks/hooks.json`, a test under `tests/`, optionally `conventions/session-hygiene.md`.
- **14a:** `knowledge/decisions/0000-template.md`, `plugin/templates/project/knowledge/decisions/0000-template.md`, `conventions/decision-log.md`, `plugin/templates/project/knowledge/decisions/README.md`.
- **14b:** `conventions/knowledge-layer.md`, `plugin/skills/grill/SKILL.md`.

Overlap warning: the parallel session is building items 3–5 and 7–9. I did not read its worktree, so check `plugin/hooks/hooks.json` and `conventions/` for conflicts before starting 11 or 14.

## What I could not verify

- episodic-memory's install on this machine (not installed, per instructions); the Windows verdict rests on its open issues and the nvm setup.
- Token costs for 10 and 12 are estimates.
- Whether decision-log's PreCompact output works in practice; the docs say `systemMessage` is discarded.
- The stall scan matches a phrase list over 54 `/ship` sessions; other wordings would slip through.
