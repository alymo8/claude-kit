# `/ship-fast`: the light path

The path for an hour-sized proof of concept, from an idea to a pull request
the human merges. The command itself is
[`plugin/commands/ship-fast.md`](../plugin/commands/ship-fast.md).

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 8}}}%%
flowchart LR
  classDef you fill:#fde68a,stroke:#b45309,stroke-width:2px,color:#1c1917
  classDef gate fill:#bfdbfe,stroke:#1d4ed8,stroke-width:2px,color:#1c1917

  idea([Idea])

  subgraph specp["1 · Spec"]
    direction TB
    design["Brainstorm<br/>2–3 approaches, one design"]
    grill{{"Human answers<br/>the grill"}}:::you
    write["Write the spec"]
    sok{{"Human approves<br/>the spec"}}:::you
    design --> grill --> write --> sok
  end

  subgraph build["2 · Build"]
    direction TB
    wt["Create a worktree"]
    tasks["Task list"]
    dec{{"Human answers<br/>pending decisions"}}:::you
    impl["Build test-first<br/>independent tasks in parallel"]
    wt --> tasks --> dec --> impl
  end

  subgraph check["3 · Check and open the PR"]
    direction TB
    smoke["Smoke run"]:::gate
    rev["AI code review"]:::gate
    pr["Open the PR<br/>CI green"]:::gate
    run(["Run the system"])
    smoke --> rev --> pr --> run
  end

  subgraph after["4 · After the run"]
    direction TB
    test{{"Human tests"}}:::you
    merge{{"Human reviews<br/>and merges"}}:::you
    test --> merge
  end

  idea --> specp --> build --> check --> after
```

Amber: a human decision. Blue: an automatic check.
