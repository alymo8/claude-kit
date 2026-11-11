# /ship-fast: step 0 (Spec)

Part of `commands/ship-fast.md`, which reads this file when it reaches it. That command's Stop rules and Git lock retry apply here.

0. **Spec.** Only when Input says so. **Budget: at most 7 questions to the
   user in the whole step**, brainstorming and grill together, counting
   each numbered question and each single question (the idea question and
   the approach choice included). Fewer is better: a clear idea may need 2
   or 3.
   1. **Idea.** With no idea text, ask "What are we building, and for
      whom?" and wait for the answer in the user's words. This counts as 1.
   2. **Home.** If the current directory is inside a git repository that
      is not the claude-kit repository itself (the one whose
      `plugin/.claude-plugin/plugin.json` has `"name": "claude-kit"`), that
      repository is the home: state it in one line and read its stack from
      its files; do not ask. Otherwise Home is a grill question: a new
      repository (name, and `node` or `python`) or the path of an existing
      one.
   3. **Design.** Run `superpowers:brainstorming` on the idea, on its
      architectural path, with these overrides: skip its separate
      clarifying questions and its visual-companion offer; read the home
      repository, if there is one, for context; propose 2–3 approaches with
      a recommendation; present the design for the recommended approach
      once, in full, with no per-section approval. The approach choice is
      not asked on its own: it is the first question of the grill's first
      round. Stop there: do not write brainstorming's spec, run any review
      of it, or invoke writing-plans.
   4. **Grill.** Run `claude-kit:grill` on that design with these
      overrides: its tree holds the design's open product choices and the
      areas below **instead of** the `coverage.md` areas, and it asks at
      most the budget left, most important first, aiming for one round and
      two at most.
      - **Users and outcome:** who uses it and what they get.
      - **Core flows:** the steps a user takes, start to finish.
      - **In and cut:** what the POC does, and what it leaves out.
      - **Data:** what it takes in, what it shows, what it keeps.
      - **States and wording:** empty, loading and error screens, and the
        text users read.
      - **Acceptance criteria:** how the user will check the POC works.
      - **Home:** as in item 2, only when it is not settled there.

      Every open product choice that does not fit the budget takes the
      grill's recommended answer and is listed in the grill summary as
      **Assumed (not asked)**. Acceptance criteria are never only assumed:
      when they do not fit as their own question, the summary proposes them
      and the user's confirmation covers them. If the user chose an
      approach other than the recommended one, the summary states the
      chosen approach and what it changes in the design; the design is not
      presented again. The summary's coverage list names the areas above,
      not `coverage.md`'s, and the grill summary names Home (inferred in
      item 2 or answered), so the confirmation covers it. The user's
      confirmation of the summary ends the interview; it is not yet the
      spec's approval (item 6). A correction to an assumption in that reply
      is applied and does not count against the budget.
   5. **Write the spec.** Pick `<slug>`, a short kebab-case name for the
      POC. Write a `# <title>` line (the POC's name; step 7 uses it as the
      PR title), Status `draft`, Date, a
      `- **Repo:** new <name> <stack>` line when Home is a new repository,
      and the sections Purpose, Scope (`**In:**` and `**Out:**`), Design,
      Decisions (each question and the user's answer, then an
      **Assumed (not asked)** list) and Success criteria (the acceptance
      criteria). No `## Coverage` section. The file name is
      `<YYYY-MM-DD>-<slug>-design.md`: in an existing repository, under
      `docs/superpowers/specs/` in its main checkout (step 2 commits it on
      the branch); for a new repository, under `~/.claude/ship-fast-specs/`
      (durable across sessions and outside every repository; step 1 copies
      it in). State the path in one line and go to item 6.
   6. **Approval.** The user reads the spec and approves it; this is the
      spec's only review, and no gate runs. Open the spec's `.md` for the
      user (`Invoke-Item <path>` on Windows, `open` on macOS, `xdg-open`
      elsewhere) and ask them to read it and reply "approve" or with the
      changes they want. Apply changes to the spec, open it again, and ask
      again; these rounds do not count against the budget. On "approve",
      set the spec's Status bullet to `approved` and continue to step 1
      without another pause.
