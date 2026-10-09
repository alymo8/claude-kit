---
name: present
description: Use when the user asks for a presentation, slides or a deck (HTML) about a repository, a POC, a spec or a plan, such as a client demo, a stakeholder update or a timed talk.
argument-hint: "[repo-dir | spec.md [plan.md]]"
---

# Present

Build a timed HTML deck from a repo, a spec or a plan. The deck is
`template.html` (next to this file) with its slides replaced; every claim on it
comes from the sources, and every slide is looked at before hand-over.

## 1. Sources

- **Arguments:** spec and/or plan `.md` paths, or a repo folder. **None:** the
  current repo.
- **For a repo:** read the README, the project `CLAUDE.md`, the newest spec and
  plan under `docs/superpowers/`, and the code. Run its tests if that is cheap
  and writes nothing into the repo.
- **For a spec or plan:** also look for later specs, ADRs, merged PRs or commits
  on the same topic (`git log --oneline -- <paths>`). Any of them that changes
  the design makes the spec superseded.
- PR bodies (`gh pr view <n>`) count as sources, such as for CI results or a
  recorded run.
- **For the closing slides:** the spec's `## Out of scope` section, ADRs and
  the spec's decisions, the first and last commit dates, merged PRs, gate
  records under `docs/superpowers/gates/`, open questions, gate findings, TODOs
  and skipped tests.
- Keep a claim list: each fact with its source. A slide states only facts on
  that list.

## 2. Ask once

One `AskUserQuestion` call, recommended option first:

1. Audience: business, technical, mixed (business arc, technical slides in
   the appendix).
2. Length in minutes (default 10) and whether it includes a live demo
   (default: yes for a runnable repo, about 40% of the time).
3. Where to save: `presentation/index.html` in the repo, left uncommitted
   (recommended), or another path.
4. The ask: what the user wants from this audience (approval to go further,
   funding or resources, feedback, a pilot user, none). No recommended option.
5. Only when the spec was superseded: present the current design (recommended)
   or the version given, with a "Since this spec" slide listing what changed.

Skip a question the user already answered. If the user cannot be reached, take
the recommended options, leave out the Ask slide, and list the questions in
the hand-over. Never invent an ask.

## 3. Build

- Copy `template.html` to the target. Set `<title>`, then replace everything
  between `<!-- SLIDES START -->` and `<!-- SLIDES END -->`; keep the CSS and
  script. Use the template's layouts (title, cards, flow, callout, table, two
  columns).
- Every `<section class="slide">` gets `data-time="m:ss"`, its start time; the
  last starts before the end. Title and Questions get about 30 seconds each,
  content slides about a minute; without a demo its time goes to content.
- Arc: title → problem → what it does → how it works → how we know it works →
  demo → what was built → not in scope → path to production → the ask →
  Questions → appendix.
- **Required slides,** in every deck:
  - **What was built:** only items backed by code, a merged PR or a completed
    plan task.
  - **Not in scope:** the spec's `## Out of scope` items in its words; mark one
    `Deferred` or `Won't do` only when the spec says which. No such section:
    leave the slide out and say so in the hand-over.
  - **Path to production:** a readiness table with one row each for auth, data
    and persistence, security and secrets, observability, deployment and
    hosting, scale and performance, cost, and compliance. Each row is `Done`,
    `Partial`, `Gap` or `Unknown` with its evidence (a file or PR); a row the
    sources do not settle is `Unknown`. The gaps become the next steps, on
    their own slide, labelled `Proposal` unless a source states them.
  - **The ask:** the user's answer, the last slide before Questions. No answer
    or "none": no slide.
- **By audience:** how it was built (method, stack, first to last commit, PRs,
  gates, CI) is one line on the title or "what it does" slide for business and
  its own slide for technical. Decisions and trade-offs (ADRs) and known
  limitations and risks (in scope but weak) go in the appendix for business
  and before "what was built" for technical. Mixed follows business.
- **Over time:** move by-audience slides to the appendix first; never drop a
  required slide.
- **Demo slide:** a numbered script (who, what to type, expected result). The
  results are labelled expected, never shown as recorded.
- **Built vs planned:** when code is present, a spec feature without code is
  labelled `Planned` on its slide. Anything not stated in the sources,
  including next steps you inferred, is labelled `Proposal`.
- Short sentences, no invented numbers, no customer names you were not given.

## 4. Verify

From the plugin root (`${CLAUDE_PLUGIN_ROOT}`, fallback
`~/.claude/skills/claude-kit`), with a new screenshot folder outside the repo
(the session scratchpad when there is one):

    python scripts/check-deck.py <deck.html> --minutes <N> --out <shots-dir>

It checks the times and that nothing loads from the network, then renders
every slide and prints each PNG. Open and look at every slide's PNG: no
overflow, clipping, overlap or unreadable text. After any edit, rerun with
`--slides <changed numbers>` into a new folder and look again. Exit 2 means no
browser was found: say in the hand-over that the slides were not rendered.

## 5. Hand over

Open the deck for the user with the OS opener (`Invoke-Item`, `open`,
`xdg-open`). Reply with the path, a table of slides with start times, anything
labelled Planned or Proposal, the readiness rows marked `Unknown` as
questions to settle before presenting, any required slide left out and why,
presenter notes (such as the demo's starting state), and which checks ran.
