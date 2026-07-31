#!/usr/bin/env python3
"""Render spec Markdown files to co-located, self-contained HTML.

Shared across all repos under Desktop/Github. Run it from inside a repo:

    python ../scripts/render-spec.py <file.md>     # render one file
    python ../scripts/render-spec.py               # render all specs in ./docs/superpowers/specs

Each <name>.md produces a <name>.html next to it. The HTML is standalone
(inline CSS, no external requests), mobile-first, and RTL-aware so Arabic
content in the specs renders correctly.

Requires: pip install markdown
"""
import sys
from pathlib import Path

import markdown

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #ffffff; --fg: #1a1a1a; --muted: #666; --border: #e2e2e2;
    --code-bg: #f5f5f5; --accent: #0b6b5f; --card: #fafafa;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #16181c; --fg: #e6e6e6; --muted: #9aa0a6; --border: #2c2f36;
      --code-bg: #22262c; --accent: #4fd1c5; --card: #1c1f24;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--fg);
    font: 16px/1.65 -apple-system, "Segoe UI", system-ui, sans-serif;
  }}
  main {{ max-width: 820px; margin: 0 auto; padding: 2rem 1.15rem 5rem; }}
  h1, h2, h3 {{ line-height: 1.25; }}
  h1 {{ font-size: 1.9rem; margin: .2em 0 .6em; }}
  h2 {{ font-size: 1.35rem; margin: 2em 0 .5em; padding-top: .6em; border-top: 1px solid var(--border); }}
  h3 {{ font-size: 1.1rem; margin: 1.4em 0 .4em; }}
  a {{ color: var(--accent); }}
  code {{ background: var(--code-bg); padding: .12em .4em; border-radius: 4px; font-size: .9em; }}
  pre {{ background: var(--code-bg); padding: 1rem; border-radius: 8px; overflow-x: auto; }}
  pre code {{ background: none; padding: 0; }}
  blockquote {{ margin: 1em 0; padding: .2em 1em; border-inline-start: 3px solid var(--accent); color: var(--muted); }}
  table {{ border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }}
  th, td {{ border: 1px solid var(--border); padding: .5em .7em; text-align: start; }}
  th {{ background: var(--card); }}
  ul, ol {{ padding-inline-start: 1.4em; }}
  li {{ margin: .2em 0; }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 2em 0; }}
  /* Arabic runs read right-to-left inside an otherwise LTR document */
  :lang(ar) {{ direction: rtl; }}
  .doc-meta {{ color: var(--muted); font-size: .9rem; }}
</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def render(md_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "toc", "sane_lists", "attr_list"],
        output_format="html5",
    )
    # Derive a title from the first H1, falling back to the filename.
    title = md_path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    out_path = md_path.with_suffix(".html")
    out_path.write_text(TEMPLATE.format(title=title, body=html_body), encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    if argv:
        targets = [Path(a) for a in argv]
    else:
        # Default: the current repo's spec folder.
        specs_dir = Path.cwd() / "docs" / "superpowers" / "specs"
        targets = sorted(specs_dir.glob("*.md"))
    if not targets:
        print("No Markdown files to render.")
        return 1
    for md in targets:
        out = render(md)
        print(f"rendered {md} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
