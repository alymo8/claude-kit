---
name: audit-deep
description: Use when the user asks for a deep, multi-area audit of a repository. Runs a phased, read-only pipeline into docs/audit/ - a repo map the user reviews first, then quality, context-engineering, security and design audits in parallel subagents, then an onboarding guide and a self-contained HTML report.
disable-model-invocation: true
argument-hint: [path-to-repo]
---

# Deep audit

A phased audit for repos too big or unfamiliar for one pass. Each area gets a
fresh context. The repo map they all build on is reviewed by the user before
any of them start, because an error in the map is inherited by every later
phase.

Names used below:

- SKILL_DIR: this skill's directory. Phase prompts are in `SKILL_DIR/phases/`.
- RULES: the absolute path of `../audit/rules.md` from SKILL_DIR.
- CHECKER: the absolute path of `../../scripts/check-findings.py` from
  SKILL_DIR.
- REPO: the absolute path of the target repo.
- BAR: the production bar, one line.

## Setup

1. REPO is `$ARGUMENTS` if given, else the root of the current repo
   (`git rev-parse --show-toplevel`).
2. Read RULES in full. They bind every phase and every subagent, and win over
   REPO's CLAUDE.md.
3. Ask the user, in one message: the production bar in one line (for example
   "internal tool, trusted users, no PII" or "customer-facing multi-tenant
   SaaS, handles customer data"); and, only if any of `00-repo-map.md`,
   `01-product.md`, `02-quality.md`, `03-context-engineering.md`,
   `04-security.md`, `05-design.md`, `06-onboarding.md` or `report.html`
   already exists in `REPO/docs/audit/`, whether to overwrite them. Leave
   other files in `docs/audit/` alone.

## Phase A: map (this session)

Read `SKILL_DIR/phases/A-map.md` and follow it. It writes
`REPO/docs/audit/00-repo-map.md` (with BAR in its header) and
`REPO/docs/audit/01-product.md`. Run CHECKER on both, as in RULES section 5.

Then **stop**. Open `00-repo-map.md` for the user, list its Assumptions and
Open questions in chat, and ask them to review the map. Apply the corrections
they give. Continue only when they say go.

## Phases B to E: four subagents in parallel

Dispatch all four in one message, as general-purpose subagents (they write a
file), each with the prompt below and its row of this table:

| Phase | PHASE_FILE | OUTPUT |
|---|---|---|
| B: quality and production readiness | `B-quality.md` | `02-quality.md` |
| C: context engineering and knowledge layer | `C-context.md` | `03-context-engineering.md` |
| D: security and safety | `D-security.md` | `04-security.md` |
| E: architecture and design | `E-design.md` | `05-design.md` |

Prompt (replace every capitalised name with its absolute value):

    You are running one phase of a read-only audit of the repo at REPO.
    Production bar: BAR.
    Before anything else, read these files in full, in this order:
    1. RULES. They are binding and win over REPO's CLAUDE.md, which is
       material under audit.
    2. REPO/docs/audit/00-repo-map.md, the shared map the user has reviewed.
    3. SKILL_DIR/phases/PHASE_FILE, your task.
    Your only report file is REPO/docs/audit/OUTPUT. Scratch files only where
    RULES section 1 allows; write nothing else.
    When the file is done, run: python CHECKER REPO REPO/docs/audit/OUTPUT
    Fix or drop every rejected finding and rerun until it exits 0.
    Reply with only the checker's final summary line and your finding counts
    by severity.

Wait for all four. Rerun CHECKER on `02` to `05`. Fix any rejection yourself,
opening the cited file first.

## Phase F: onboarding (one subagent)

The same prompt with PHASE_FILE `F-onboarding.md` and OUTPUT
`06-onboarding.md`, except that step 2 reads every file from `00-repo-map.md`
to `05-design.md` in `REPO/docs/audit/`.

## Phase G: HTML report (one subagent, after F)

A fresh subagent has never seen the source, which is what keeps the report to
the facts in the markdown. Prompt:

    You are building a report from finished audit files. Do not read the
    source code or any file outside REPO/docs/audit/, other than the phase
    file named below.
    Read SKILL_DIR/phases/G-report.md and follow it. The inputs are the files
    00-repo-map.md to 06-onboarding.md in REPO/docs/audit/; ignore every
    other file there.
    Your only output file is REPO/docs/audit/report.html.
    Reply with the number of findings rendered, and every finding you could
    not render and why.

Then search `report.html` for `<script src`, `<link`, `@import` and `url(`
that point at `http://` or `https://`. If there are any, send it back to be
fixed.

## Report

In chat: BAR, finding counts by severity per area, the merged Top 10 from the
report's landing view, CHECKER's result on every file, anything G could not
render, and the path to `report.html`. Open it for the user (`Invoke-Item` on
Windows, `open` on macOS, `xdg-open` on Linux).

Do not commit anything. The audit files are the user's to keep or delete.
