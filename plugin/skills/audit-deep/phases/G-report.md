# Phase G: HTML report

A formatting task. Do not read the source code or any file outside
`docs/audit/`. Every fact in the output comes from the input markdown files;
do not add, infer, reword or re-derive any finding.

Produce one self-contained file, `docs/audit/report.html`:

- **One file.** No CDN links, no external scripts, fonts, stylesheets or
  images. All CSS and JS inline. It must render correctly from the local
  filesystem with no network.
- **Sidebar navigation:** one section per input file, with anchor links to
  each finding.
- **Landing view:** the report title; a one-paragraph summary assembled only
  from the summaries already in the markdown; a severity count table; and a
  merged Top 10 across all areas. Deduplicate findings that appear in more
  than one area, and note when a finding was raised by several audits.
- **Finding cards:** collapsible, collapsed by default, showing title,
  severity badge and file path in the header. Expanding shows evidence,
  confidence, impact and fix.
- **Severity colours** for Critical, High, Medium and Low, and a distinct
  visual treatment for `inferred` confidence so unverified claims are obvious
  at a glance.
- **Filters** by severity, confidence and area, in plain JS with no framework,
  plus a text search box that filters findings by title and file path.
- **Layout:** readable on a laptop and a tablet. A print stylesheet that
  expands all cards.
- **Design:** clean and dense, built for reading many findings quickly.
  Restrained palette, generous line height, monospace for file paths and
  code, no decorative graphics. Escape all text taken from the markdown
  before inserting it into HTML.

At the end, report every finding in the markdown you could not render because
it was malformed or missing required fields.
