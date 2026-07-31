# Knowledge layer

A project's **knowledge layer** is a version-controlled, human-readable knowledge
base that lives inside the repo. It is the organized, single-source-of-truth home
for everything the project knows — research, findings, domain context, market and
product understanding, technical mechanics — synthesized from raw sources into
clean topic docs. It is the foundation the rest of the work builds on: specs draw
from it, and the [decision log](decision-log.md) records the choices made against
it.

## Principles

1. **Markdown for humans, in the repo.** Plain markdown, versioned alongside the
   code. Not a runtime component and not a machine/RAG store — but structured so it
   *could* be made queryable later without a rewrite.
2. **Synthesize into canonical docs.** Merge and dedupe overlapping raw sources into
   single-source-of-truth topic docs. **Each fact has exactly one home.** Keep the
   raw originals verbatim in an `archive/` folder for traceability.
3. **Organize by domain, not by feature.** Group docs by how the team reasons about
   the problem (e.g. Technical / Market / Business / Product). Domain organization
   isolates concerns and scales; organizing by product capability is premature
   before the architecture exists, and a flat topic list gets unwieldy.
4. **Make gaps visible.** Every canonical doc carries an **Open questions** section
   so what is *not yet known* is explicit rather than silently missing.

## Structure

Adapt the domains to the project; the shape stays the same:

```
<repo>/
  README.md                 # one-liner + a map into the knowledge base
  knowledge/
    README.md               # index: what lives where + suggested reading order
    <domain-a>/             # e.g. technical/
      <topic>.md            # canonical single-source-of-truth doc
    <domain-b>/             # e.g. market/, business/, product/
      <topic>.md
    decisions/              # ADRs — see decision-log.md
    archive/                # raw source docs, preserved verbatim
```

For a small project this may collapse to a single `knowledge/` folder with a
handful of topic docs and no domain subfolders — but keep the README index and the
archive discipline.

## Conventions

- **Frontmatter on every canonical doc:** `title`, `status` (`draft` | `stable`),
  `last_updated`, and `sources` (which raw docs it draws from).
- **Cross-link** related docs so a reader can navigate the web of knowledge in one
  hop, rather than re-deriving connections.
- **The `knowledge/README.md` index** is the front door: a Map (table of docs +
  one-line summaries, grouped by domain) plus a suggested reading order. A new
  contributor should reach any topic in one hop from it.
- **`archive/` is append-only and verbatim.** Never edit an archived source; it is
  the traceable record of where synthesized knowledge came from.
- **Keep it current.** When new research arrives, fold it into the relevant
  canonical doc (updating `last_updated`) instead of appending a new parallel doc.

## Definition of done

- Every raw source is digested into canonical docs; nothing is lost, and originals
  are preserved verbatim in `archive/`.
- No duplication across canonical docs — each fact has one home.
- `knowledge/README.md` maps the whole base; any topic is one hop away.
- Open questions are visible, not hidden.
