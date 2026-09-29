# Phase C: context engineering and knowledge layer

Audit how the system builds what its models see, and the repo's own Claude
Code setup. If the repo calls no model, say so in one line, cover only the
last bullet, and note which bullets you skipped.

Cover:

- **System prompt construction:** where prompts live, how they are assembled,
  string concatenation vs templates, duplication across call sites, dead or
  contradictory instructions, hardcoded prompts scattered through business
  logic.
- **Tool and function definitions:** inventory every tool exposed to the
  model. For each, assess whether the description is precise enough for
  correct selection, whether parameter schemas are constrained (enums, ranges,
  required fields) or accept free-form strings, and whether tool names and
  descriptions overlap in ways that would cause misrouting.
- **Tool results:** are results shaped for the model or raw API dumps? Is
  there truncation, and does truncation lose the important part?
- **Retrieval:** chunking strategy and chunk size, embedding model and
  version, index freshness and reindexing triggers, ranking and reranking,
  what happens on zero or low-relevance results.
- **Memory and state:** what persists across turns and sessions, where, how it
  is written and read, what governs what gets written, and how conflicts or
  stale entries are handled.
- **Context window management:** how the budget is split across system
  prompt, history, retrieved content and tool results; what is dropped first
  under pressure; whether anything measures actual token usage or it is
  assumed.
- **Prompt versioning and change management:** are prompts versioned,
  reviewable in diffs, tied to releases, or edited in place?
- **Evals:** is there an eval harness, a regression suite, golden datasets,
  scoring (LLM-as-judge, exact match, human), and does CI run any of it? If
  quality is judged by manual spot-checking, say so plainly and rate the risk.
- **The repo's own Claude Code setup:** apply section 4 of the rules
  (the Claude-config checklist) in full. Audit CLAUDE.md for accuracy against
  the current code, staleness, internal contradictions, and instructions that
  would steer a contributor wrong; give its token cost. Audit subagents,
  commands, skills and MCP config as part of the tool surface, to the same
  standard as the tool definitions above.

Be concrete: for each tool definition and prompt template you assess, quote
the text in **Evidence**.

End with `## What is missing` and `## Top 10`, ranked by severity then effort.
