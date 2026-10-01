# Spec Stats Implementation Plan

- **Status:** draft
- **Date:** 2026-09-30

**Goal:** Add `plugin/scripts/spec-stats.py`, which counts specs per Status.

**Architecture:** One standard-library script with a `counts()` function and
a `main()` that formats text or JSON. Tests run it as a subprocess.

**Tech Stack:** Python 3.11+ standard library, pytest, ruff.

**Spec:** `spec.md`

### Task 1: Count specs and print text

**Files:**
- Create: `plugin/scripts/spec-stats.py`
- Test: `tests/test_spec_stats.py`

- [ ] **Step 1: Write the failing test** at `tests/test_spec_stats.py`:

```python
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugin" / "scripts" / "spec-stats.py"


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def specs(tmp_path):
    for name in ("a", "b"):
        (tmp_path / f"{name}.md").write_text(
            "- **Status:** approved\n", encoding="utf-8"
        )
    (tmp_path / "c.md").write_text("# No status\n", encoding="utf-8")
    return tmp_path


def test_text_output(tmp_path):
    result = run(str(specs(tmp_path)))
    assert result.returncode == 0
    assert result.stdout == "approved: 2\nunknown: 1\n"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_spec_stats.py -q`
Expected: 1 failed (`assert 2 == 0`: Python cannot open the missing script).

- [ ] **Step 3: Write `plugin/scripts/spec-stats.py`:**

```python
#!/usr/bin/env python3
"""Count specs per Status: python spec-stats.py [SPECS_DIR] [--json]."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from spec_status import STATUS_RE  # noqa: E402


def counts(folder: Path) -> Counter:
    found: Counter = Counter()
    for md in sorted(folder.glob("*.md")):
        match = STATUS_RE.search(md.read_text(encoding="utf-8"))
        found[match.group(1).lower() if match else "unknown"] += 1
    return found


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--json"]
    folder = Path(args[0]) if args else Path("docs/superpowers/specs")
    found = counts(folder)
    for status, count in sorted(found.items()):
        print(f"{status}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python -m pytest tests/test_spec_stats.py -q`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add plugin/scripts/spec-stats.py tests/test_spec_stats.py
git commit -m "spec-stats.py: count specs per Status"
```

### Task 2: JSON, empty and missing folders

**Files:**
- Create: `plugin/scripts/spec_status.py`
- Modify: `plugin/scripts/spec-stats.py`
- Modify: `tests/test_spec_stats.py`

- [ ] **Step 0: Create `plugin/scripts/spec_status.py`:**

```python
import re

STATUS_RE = re.compile(r"^- \*\*Status:\*\*[ \t]*(\S+)", re.M)
```

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_spec_stats.py`:

```python
def test_json_output(tmp_path):
    result = run(str(specs(tmp_path)), "--json")
    assert result.stdout.strip() == '{"approved": 2, "unknown": 1}'


def test_empty_folder(tmp_path):
    result = run(str(tmp_path))
    assert result.returncode == 0
    assert result.stdout == "no specs\n"


def test_missing_folder(tmp_path):
    assert run(str(tmp_path / "nope")).returncode == 2
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_spec_stats.py -q`
Expected: the 3 new tests FAIL.

- [ ] **Step 3: Update `plugin/scripts/spec-stats.py`.** Add `import json`
above `import re`, and replace `main()` with:

```python
def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--json"]
    folder = Path(args[0]) if args else Path("docs/superpowers/specs")
    if not folder.is_dir():
        print(f"spec-stats: no such folder: {folder}", file=sys.stderr)
        return 2
    found = counts(folder)
    if not found:
        print("no specs")
    elif "--json" in argv:
        print(json.dumps(dict(sorted(found.items()))))
    else:
        for status, count in sorted(found.items()):
            print(f"{status}: {count}")
    return 0
```

- [ ] **Step 4: Run the full suite and lint**

Run: `python -m pytest -q; ruff check plugin tests`
Expected: all PASS, lint clean.

- [ ] **Step 5: Commit**

```bash
git add plugin/scripts/spec-stats.py tests/test_spec_stats.py
git commit -m "spec-stats.py: --json, empty and missing folders"
```
