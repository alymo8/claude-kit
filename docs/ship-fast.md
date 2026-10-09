# `/ship-fast`: the light path

An hour-sized proof of concept skips the gates. The human still makes
every product call, through a capped number of questions, and the run stops
at an open PR with green CI and the POC running. The human merges it. The
command itself is [`plugin/commands/ship-fast.md`](../plugin/commands/ship-fast.md).

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 8}}}%%
flowchart LR
  classDef you fill:#fde68a,stroke:#b45309,stroke-width:2px,color:#1c1917
  classDef gate fill:#bfdbfe,stroke:#1d4ed8,stroke-width:2px,color:#1c1917

  start([Idea or spec.md])

  subgraph specp["0 · Spec (only from an idea)"]
    direction TB
    design["Brainstorm<br/>2–3 approaches, one design"]
    grill{{"Human answers the grill<br/>at most 7 questions"}}:::you
    sok{{"Human confirms the summary<br/>= spec approved"}}:::you
    write["Write the spec<br/>no gate"]
    design --> grill --> sok --> write
  end

  subgraph build["1 · Build"]
    direction TB
    repo["Repo<br/>new private repo, or fetch"]
    wt["Worktree poc/slug<br/>from origin/main"]
    tasks["Task list<br/>1–5 tasks, no gate"]
    dec{{"Human answers the decisions round<br/>≤ 3 product · ≤ 3 engineering · every risky one"}}:::you
    impl["Build test-first<br/>independent tasks in parallel"]
    repo --> wt --> tasks --> dec --> impl
  end

  subgraph check["2 · Check and open the PR"]
    direction TB
    smoke["Smoke run<br/>every acceptance criterion"]:::gate
    rev["Quick AI review<br/>keep correctness fixes only"]:::gate
    pr["Open the PR<br/>CI green"]:::gate
    hand(["Hand over<br/>POC left running from the worktree"])
    smoke --> rev --> pr --> hand
  end

  subgraph after["3 · After the run"]
    direction TB
    test{{"Human tests or presents<br/>the POC"}}:::you
    merge{{"Human reviews and<br/>merges the PR"}}:::you
    clean(["Clean up on the human's OK<br/>worktree · branch · Docker"])
    test --> merge
    test --> clean
  end

  start -- idea --> specp
  start -- spec.md --> build
  specp --> build --> check --> after
```

Amber: a human decision. Blue: an automatic check. A product or risky
question that comes up later is asked inline and the run continues. The run
stops only on the rules in the command: no acceptance criteria, a red
baseline, or a smoke run or CI still red after two fixes.
