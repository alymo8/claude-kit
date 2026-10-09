#!/usr/bin/env python3
"""Check an HTML deck built from the present skill's template, then screenshot it.

Usage: check-deck.py DECK.html [--minutes N] [--slides 2,5] [--out DIR] [--no-render]

Checks: every ``<section class="slide">`` has a ``data-time="m:ss"`` start time,
the times rise, the last slide starts before ``--minutes``, and nothing loads
from the network. Then, unless ``--no-render``, every slide (or only
``--slides``) is rendered at 1920x1080 with headless Chrome or Edge into a new
folder (``--out`` or a fresh temp dir), and each PNG path is printed so it can
be looked at. Exits 1 on a check failure, 2 when no browser is found.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SLIDE = re.compile(r"<section\b[^>]*\bclass=\"[^\"]*\bslide\b[^\"]*\"[^>]*>", re.I)
TIME = re.compile(r"\bdata-time=\"(\d+):([0-5]\d)\"")
EXTERNAL = re.compile(
    r"(?:\b(?:src|href)\s*=\s*[\"']?|@import\s+[\"']?|url\(\s*[\"']?)(?:https?:)?//",
    re.I,
)
COMMENT = re.compile(r"<!--.*?-->", re.S)
BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)
NAMES = ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge")


def slide_times(html: str) -> list[str | None]:
    """Each slide's data-time value in order, or None where it is missing."""
    out = []
    for tag in SLIDE.findall(COMMENT.sub("", html)):
        match = TIME.search(tag)
        out.append(f"{match[1]}:{match[2]}" if match else None)
    return out


def seconds(value: str) -> int:
    minutes, secs = value.split(":")
    return int(minutes) * 60 + int(secs)


def problems(html: str, minutes: float) -> list[str]:
    """Every check failure, as one line each; empty when the deck is fine."""
    found = []
    times = slide_times(html)
    if not times:
        found.append('no <section class="slide"> found')
    for n, value in enumerate(times, 1):
        if value is None:
            found.append(f'slide {n}: missing data-time="m:ss"')
    known = [(n, seconds(v)) for n, v in enumerate(times, 1) if v]
    for (_, a), (n, b) in zip(known, known[1:], strict=False):
        if b <= a:
            found.append(f"slide {n}: start time out of order")
    if known and known[-1][1] >= minutes * 60:
        found.append(
            f"slide {known[-1][0]} starts at {times[known[-1][0] - 1]}, "
            f"not before {minutes:g}:00"
        )
    for match in EXTERNAL.finditer(COMMENT.sub("", html)):
        found.append(f"external resource near: {match.group(0)!r}")
    return found


def find_browser() -> str | None:
    override = os.environ.get("DECK_BROWSER")
    if override:
        return override
    for path in BROWSERS:
        if Path(path).is_file():
            return path
    for name in NAMES:
        if found := shutil.which(name):
            return found
    return None


def render(deck: Path, numbers: list[int], out: Path, browser: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    shots = []
    for n in numbers:
        png = out / f"slide-{n:02d}.png"
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=1920,1080",
                f"--screenshot={png}",
                f"{deck.resolve().as_uri()}#{n}",
            ],
            capture_output=True,
            timeout=60,
        )
        if png.is_file():
            shots.append(png)
        else:
            print(f"slide {n}: no screenshot written", file=sys.stderr)
    return shots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("deck", type=Path)
    parser.add_argument("--minutes", type=float, default=10)
    parser.add_argument("--slides", help="comma-separated slide numbers to render")
    parser.add_argument("--out", type=Path, help="screenshot folder (default: new)")
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args(argv)

    html = args.deck.read_text(encoding="utf-8")
    times = slide_times(html)
    print(f"{len(times)} slides, starts: {', '.join(t or '?' for t in times)}")
    found = problems(html, args.minutes)
    for line in found:
        print(f"FAIL {line}")
    if found:
        return 1
    if args.no_render:
        return 0

    browser = find_browser()
    if not browser:
        print("no Chrome or Edge found; set DECK_BROWSER", file=sys.stderr)
        return 2
    numbers = (
        [int(n) for n in args.slides.split(",")]
        if args.slides
        else list(range(1, len(times) + 1))
    )
    out = args.out or Path(tempfile.mkdtemp(prefix="deck-shots-"))
    shots = render(args.deck, numbers, out, browser)
    for png in shots:
        print(png)
    return 0 if len(shots) == len(numbers) else 1


if __name__ == "__main__":
    sys.exit(main())
