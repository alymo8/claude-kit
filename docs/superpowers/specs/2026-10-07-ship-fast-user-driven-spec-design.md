# `/ship-fast`: a spec the user drives, and product decisions asked out loud

- **Status:** approved
- **Date:** 2026-10-07

## Purpose

`/ship-fast` will be run live in front of clients, to show them how a POC is
built. Today it starts from a spec that already exists, assumes any "how"
choice it can and lists it under **Assumptions**, and on a real product
decision it writes a handoff and ends the run. In a client session that
hides the most important part (who decides what the product does) and breaks
the flow.

After this change the user drives spec creation inside `/ship-fast`: a
brainstorming design followed by a short grill interview, where the most
important product decisions (at most 7) are put to the user with options and
a recommendation, and every product choice not asked is written into the
spec as a labelled assumption the user can overrule. Choices that only
appear once the work is split into tasks are asked in one short round
before any code is written: at most 3 product and at most 3 engineering
questions, plus any risky engineering choice (irreversible data, real
credentials or paid services, outside interfaces). One that surfaces
mid-build is asked inline and the run continues. A
one-line progress note at the start of each step lets the client follow
along.

## Scope

**In:**
- `plugin/commands/ship-fast.md`: input rule, new step 0 (Spec), new step 3b
  (Decisions round), inline product questions, progress lines,
  stop rules, `argument-hint`, frontmatter `description`.
- `tests/test_ship_fast_command.py`: assertions for the new pieces.
- `tests/test_parallel_plan.py`: a test that a task list with a
  `## Decisions` section before its tasks still parses into waves.
- `knowledge/decisions/0022-ship-fast-user-driven-spec.md` (new), its row in
  `knowledge/decisions/README.md`, and ADR 0021's Status and README row
  marked "amended by 0022".
- `CLAUDE.md`: the `/ship-fast` paragraph under "Building a new feature".
- `README.md`: the `/ship-fast` sentence.
- `conventions/spec-driven-development.md`: the `/ship-fast` sentence.
- `plugin/.claude-plugin/plugin.json`: version 0.14.0; description says
  `/ship-fast` interviews the user for the spec.
- `tests/test_plugin_manifest.py`: version 0.14.0.

**Out:**
- Any change to `/ship`, `/ship-many`, the gates, `parallel-plan.py`,
  `superpowers:brainstorming`, `claude-kit:grill` or its `coverage.md`, or
  `claude-kit:parallel-tasks`. Every override of their behaviour lives in
  `ship-fast.md`.
- A gate on the spec or task list (ADR 0021 stands: no gates).
- An opt-in flag: the new behaviour is the only behaviour.
- Resuming a half-finished interview: a stop before the spec is written
  restarts the interview.
- Deleting any repository, during the run or as a suggestion afterwards:
  the user deletes repositories themselves.

## Design

### Input

- `$ARGUMENTS` names an existing `.md` file: it is the spec. Step 0 is
  skipped; everything from step 1 on runs, including step 3b.
- An argument that ends in `.md` but names no existing file is a stop rule
  (a mistyped spec path), not an idea.
- Otherwise (free text, or empty): the text is the idea, and step 0 runs.
  This replaces today's "empty means the newest spec" rule.

`argument-hint` becomes `[spec.md | idea]`.

Both starting points stay supported: a new repository from scratch (the
spec's `- **Repo:** new <name> <stack>` line, scaffolded as today) and a
repository the user already cloned from a starter (no `Repo` line; the run
works in the repository that holds the spec, as today).

### Approval wording

The preamble keeps "invoking `/ship-fast` is the user's approval for every
step", and changes "do not ask for confirmation except under the Stop rules"
to: do not ask except in step 0, step 3b, a product or risky engineering
question (below), and
the Stop rules. The "where a skill says ask, take the path this command
names" rule does not apply to brainstorming and grill inside step 0, whose
questions go to the user, within the budget below.

**Non-interactive runs.** In a session nobody can answer (started with
`claude -p`, for example a scripted run): step 0 is a stop rule (the
interview needs the user; pass a spec path). Every product or non-risky
engineering question in step 3b or later takes its recommended answer,
listed as "assumed (not asked)" in the task list's `## Decisions` and the
PR body, and the run continues. A risky engineering choice is a stop rule:
the handoff lists it with its options and recommendation.

### Product and engineering choices

A **product choice** is one a user of the POC would see or feel: behaviour,
scope, data taken in, shown or kept, layout, wording, defaults, sample data.
An **engineering choice** is any other (libraries, file layout, test
approach, data storage, security hardening, interfaces between modules).

A **risky engineering choice** is one that deletes or migrates existing
data, uses real credentials or a paid external service, or changes an
interface that something outside the POC depends on. Risky choices are
always asked, outside every budget: in step 3b's engineering part when the
task list exposes them, inline (as in "Product questions during the build")
when they surface later.

Other engineering choices are asked only in step 3b's engineering part (at
most 3); every one not asked takes the simplest option that fits the
repository and is listed under **Assumptions**. Step 0 asks no engineering
questions except two, both inside its budget: the Home question (repository
name and stack) when Home is not settled from the current directory, and
the choice among brainstorming's approaches.

### Step 0: Spec (only without a spec path)

**Question budget: at most 7 questions to the user in the whole step,**
brainstorming and grill together, counting each numbered question and each
single question (including the idea question and choosing an approach).
Fewer is better; a clear idea may need 2 or 3.

1. **Idea.** With no idea text, ask "What are we building, and for whom?"
   and wait for the answer in the user's words. This counts as 1.
2. **Home.** If the current directory is inside a git repository that is
   not the claude-kit repository itself (the one holding
   `plugin/.claude-plugin/plugin.json` with `"name": "claude-kit"`), that
   repository is the home: state it in one line and read its stack from its
   files; do not ask. Otherwise Home is a grill question (new repository
   name and `node` or `python`, or the path of an existing one).
3. **Design.** Run `superpowers:brainstorming` on the idea, on its
   architectural path, but skip its separate clarifying questions: read the
   home repository for context, propose 2–3 approaches with a
   recommendation, and present the design once, in full (the workspace's
   "Designing a spec" rule: no per-section approval). The approach choice
   joins the grill's first round rather than being asked on its own. Stop
   there: do not write brainstorming's spec, run its spec review, or invoke
   writing-plans.
4. **Grill.** Run `claude-kit:grill` on that design with two overrides
   stated in the command: its tree holds the design's open product choices
   and these product areas **instead of** the `coverage.md` areas, and it
   asks at most the remaining budget, most important first:
   - **Users and outcome:** who uses it and what they get.
   - **Core flows:** the steps a user takes, start to finish.
   - **In and cut:** what the POC does, and what it leaves out.
   - **Data:** what it takes in, what it shows, what it keeps.
   - **States and wording:** empty, loading and error screens, and the
     text users read.
   - **Acceptance criteria:** how the user will check the POC works.
   - **Home:** as in item 2, only when it is not settled there.
   Aim for one round, two at most. Every open product choice that does not
   fit the budget gets the grill's recommended answer and is listed in the
   grill summary as **Assumed (not asked)**. Acceptance criteria are never
   only assumed: when they do not fit as their own question, the summary
   proposes them and the user's confirmation covers them. The user's
   confirmation of the summary is the spec's approval; a correction to an
   assumption in that reply is applied and does not count against the
   budget.
5. **Write the spec.** Status `approved`, Date, a
   `- **Repo:** new <name> <stack>` line when Home is a new repository;
   sections Purpose, Scope (In/Out), Design, Decisions (each question and
   the user's answer, then an **Assumed (not asked)** list), Success
   criteria. Location: in an existing repository,
   `docs/superpowers/specs/<YYYY-MM-DD>-<slug>-design.md` in its main
   checkout (step 2 commits it on the branch, as today); for a new
   repository, the same file name under `~/.claude/ship-fast-specs/`
   (durable across sessions, outside every repository; step 1 copies it
   in).
   State the path in one line, do not open it, and continue to step 1
   without another pause. No gate runs.

### Step 3b: Decisions round

After the task list is committed and before step 4, one round in grill's
question format (numbered, options, recommended answer), in two labelled
parts, then wait for the answers:

- **Product:** the product choices that writing the tasks exposed and that
  the spec neither decides nor lists as assumed. Ask **at most 3**; any
  beyond 3 take their recommended answer and are listed as assumed.
- **Engineering:** every risky engineering choice the task list exposes,
  plus **at most 3** other engineering choices, picked by how much they
  shape the build (data storage, new dependencies or services, structure).
  The rest are assumed and listed under Assumptions.

Write the answers and the assumptions under a `## Decisions` section in the
task list, before its first `### Task`, and commit. If a part has nothing to
ask, it is left out; if both are empty, say so in one line and continue.

### Product questions during the build

A product choice or a risky engineering choice that is still open later is
asked inline in the same format, one question; the run waits for the answer, appends it to the task
list's `## Decisions`, and continues from the same point. No handoff is
written and the run does not end. The current stop rule for unsettled
scope/behaviour/interface/data choices is replaced by this rule.

In parallel waves, `/ship-fast` adds to each subagent's instructions: a
product choice or risky engineering choice the task list's Decisions do not
settle is not guessed; the
subagent reports the task as failed and names the question. The main
session asks the user, records the answer, and implements that task inline,
as `parallel-tasks` already does for a failed task.

Every question the user answered, product or engineering, appears under
**Decisions** in the PR body and the report; product choices taken without
asking appear there as "assumed (not asked)". Only engineering choices
taken without asking go under **Assumptions**.

### Progress lines

At the start of each step 0 to 8, including step 3b, post one plain-language line naming the
step and what it is about to do, e.g. "Step 4: building the upload flow,
tests first." Progress lines are not reports; the single report at the
end (step 9) is unchanged.

### Cleanup and report

Unchanged, with one addition to the command: it never deletes a repository
and never suggests deleting one.

### Unchanged

Repo scaffolding, worktree, task list format, parallel waves, TDD, smoke
run, `code-review low --fix`, PR with green CI, no merge, cleanup, the other
stop rules, git lock retry, and resume from step 1 on, with one added
Resume rule: if the task list on the branch already has a `## Decisions`
section, step 3b is skipped; otherwise it runs. And one stop rule: every
stop after step 0 states the absolute path of the spec to pass on the
rerun, in the stop message and in the handoff: for a new repository, the
in-repository copy once step 1 has committed it, and before that the
`~/.claude/ship-fast-specs/` path.

## Decisions

- **Spec creation lives inside `/ship-fast`** (user's choice): one
  continuous flow for the client to watch.
- **Brainstorming, then grill** (user's choice): brainstorming gives the
  approaches and design without its own clarifying questions; grill closes
  the decisions.
- **At most 7 questions in step 0; at most 3 product and at most 3
  non-risky engineering questions in step 3b** (user's choice):
  a POC interview should be short. Product choices beyond the budget are
  recommended answers listed as "assumed (not asked)".
- **Grill asks product areas only** (follows from the budget): its
  engineering `coverage.md` areas are replaced; engineering choices wait
  for step 3b.
- **Step 3b asks only what the task split newly exposes** (user's choice).
- **Engineering choices get a short round in step 3b** (user's choice):
  after the product part, at most 3 by impact; in step 0 only Home and
  the approach choice, inside its budget.
- **Risky engineering choices are always asked, outside the budgets**
  (user's choice): irreversible data changes, real credentials or paid
  services, interfaces outside the POC; inline if they surface mid-build.
  This replaces the current stop rule's "touches data irreversibly" and
  "public interface" cases.
- **Questions carry options and a recommendation** (user's choice).
- **Non-interactive runs take recommended answers, stop on risky ones**
  (user's choice): step 0 stops without a spec path; product and non-risky
  engineering questions are assumed and listed; a risky engineering choice
  stops with a handoff.
- **Late product questions are asked inline and never end the run** (user's
  choice).
- **Default behaviour, no flag** (user's choice); ADR 0022 amends ADR 0021.
- **One progress line per step** (user's choice).
- **Both starting points supported**: from scratch (`Repo: new`) or inside
  a repository cloned from the user's starter (user's statement).
- **Never delete or suggest deleting a repository** (user's instruction).
- **An empty argument starts the interview** instead of picking the newest
  spec: the interview is the default entry.
- **Grill's confirmation is the spec approval**; no extra pause after the
  spec is written, and no gate (ADR 0021).
- **Subagents report unsettled product choices as a failed task** so the
  existing `parallel-tasks` failure path brings them back to the main
  session, with no change to `parallel-tasks`.

## Success criteria

1. `pytest` passes, and `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean.
2. `tests/test_ship_fast_command.py` asserts that `ship-fast.md` contains
   `superpowers:brainstorming`, `claude-kit:grill`, each product area label
   (`Users and outcome`, `Core flows`, `In and cut`, `Data`,
   `States and wording`, `Acceptance criteria`, `Home`), `at most 7`,
   `at most 3`, `Assumed (not asked)`, `risky engineering choice`,
   `**Engineering:**`, `## Decisions`,
   `Decisions round`, `[spec.md | idea]`, and the phrase
   `does not end`; that it contains neither `gh repo delete` nor
   `changes scope, product behaviour`; and that every existing assertion
   still holds.
3. `tests/test_parallel_plan.py` has a test where a task list with a
   `## Decisions` section before `### Task 1` yields the same waves as
   without it, and it passes.
4. `tests/test_plugin_manifest.py` checks version 0.14.0, and the manifest
   description's text after `/ship-fast` contains `interview`; ADR 0022 exists with a row in
   `knowledge/decisions/README.md`; ADR 0021 and its row say "amended by
   0022"; `grep -n "ship-fast" CLAUDE.md README.md conventions/spec-driven-development.md`
   in each of those files the paragraph containing `/ship-fast` contains
   `interview`; the manifest test asserts only the version.
5. **Live run.** In a fresh session with the branch's command loaded, run
   `/ship-fast a CLI that counts words in a file` from a directory that is
   not a git repository, and choose Home = new repository `ship-fast-demo`,
   `python`. Pass when: brainstorming presents approaches and one full
   design without separate clarifying questions; step 0 asks at most 7
   questions in total, numbered with recommendations, none of them an
   engineering choice other than Home and the approach choice; the spec is written only after the confirmation,
   with Decisions including an **Assumed (not asked)** list and Success
   criteria; step 3b asks at most 3 product and at most 3 non-risky
   engineering questions in two labelled parts, or prints its "none new"
   line, before any task commit; each step 0 to 8, including step 3b, starts with one progress line;
   the PR body's Decisions hold the user's answers and its engineering
   Assumptions hold no product choice; PR CI is green (a known gitleaks permission failure in the scaffolded
   `secret-scan.yml` may be fixed inside `ship-fast-demo` as one of the CI
   fix attempts); and neither the run
   nor its report deletes or suggests deleting `ship-fast-demo`.
