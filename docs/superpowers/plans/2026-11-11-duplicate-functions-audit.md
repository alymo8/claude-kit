# Duplicate-intent pass in `audit` and `audit-deep` Implementation Plan

- **Status:** approved
- **Date:** 2026-11-11

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a duplicate-intent pass to `claude-kit:audit` (Pass 4) and `claude-kit:audit-deep` (Phase H): a regex function catalog script, a shared procedure file that groups functions by domain on Haiku and compares them per domain on the session's model, and report sections for both audits.

**Architecture:** One standard-library script, `plugin/scripts/function-catalog.py`, lists functions from `git ls-files` as JSON (or as batch files). One Markdown procedure, `plugin/skills/audit/duplicates.md`, is followed by the session that runs either audit. The two skills, one phase file each, docs, and a minor version bump (0.28.0 → 0.29.0) finish the change. Skill text is pinned by string assertions in `tests/test_audit_skills.py`.

**Tech Stack:** Python 3.11+ standard library (`argparse`, `re`, `json`, `subprocess`), pytest, ruff, Markdown, git.

**Spec:** `docs/superpowers/specs/2026-11-10-duplicate-functions-audit-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-10-duplicate-functions-audit-design.md`

## Context for the executor

This repo is claude-kit: a Claude Code plugin under `plugin/`. `tests/helpers.py`
exports `PLUGIN` (`REPO / "plugin"`), `REPO`, `load_module(path, name)` and
`run_script(script, *args, cwd=None, env=None)` (runs `sys.executable script
args`, returns a `CompletedProcess` with text `stdout`/`stderr`, UTF-8).
Scripts follow `plugin/scripts/docker-disk.py`: module docstring with usage,
`from __future__ import annotations`, `argparse`, `main(argv: list[str] | None
= None) -> int`, `if __name__ == "__main__": sys.exit(main())`, and
`sys.stdout.reconfigure(encoding="utf-8")` guarded by `hasattr`.

Gotchas (from `knowledge/kit-dev-gotchas.md`): test code must fit ruff's
88-character lines; edit test files with the Edit tool, not bash heredocs;
run plain `pytest` (not `-q`) to see the pass count; CI runners have no git
identity, so test repos commit with `-c user.name=t -c user.email=t@example.com`.
The audit skills' findings use the block format in `plugin/skills/audit/rules.md`
section 2; `check-findings.py` counts `### [Severity] title` blocks only, so the
LOW table and skip lines are never written as `### [` headings.

Setup: `pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks:
`pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`.

## Global Constraints

- Script: standard library only, Python 3.11; `sys.stdout.reconfigure(encoding="utf-8")` before printing.
- Snippet: the matched line and the next N lines (default 15), at most 1,200 characters.
- Default `--batch-size` 150. Exit 0 on success (empty array included); exit 2 on bad usage, a root that is not a git repo, or a git failure.
- Thresholds (D3): skip under 20 or over 3,000 functions; group in batches of 150; compare domains with 3 or more functions, in units of at most 150 entries; at most 12 compare subagents.
- Skip lines, verbatim: `Skipped: <n> functions, below the 20-function threshold.` and `Skipped: <n> functions, above the 3,000-function limit; audit a smaller repo.`
- Counts line, verbatim: `<n> functions catalogued; <u> of <t> compare units dispatched; groups: <h> HIGH, <m> MEDIUM, <l> LOW`.
- Grouping subagents use `model: haiku`, with a re-dispatch with no model override when refused; compare subagents use no model override (D2).
- The audits stay read-only; scratch files only in the `audit-scratch` folder that `rules.md` section 1 allows. `rules.md` and `check-findings.py` are not changed.
- No copied text or scripts from obra/superpowers-lab.
- Public repo: no machine username or private repo names in tracked files.
- Version: `0.29.0` (next minor above `origin/main`'s `0.28.0`). On a rebase conflict with the review-and-guardrails spec, take the next minor above `origin/main`'s and keep both description additions and both README sentences (D1).

## Plan-level answers to the spec gate's plan questions

- **`other: <subdomain>` labels:** each distinct label (trimmed, lowercased) is its own domain for the 3-function threshold, the 150-entry units and the cap of 12. (Task 2)
- **Test-like fixtures:** files whose names the catalog treats as tests (`test_*.py`, `*.spec.ts`, a `node_modules` path) are written into the temporary repo by the test at run time, never committed under `tests/fixtures/`; the committed fixtures are named `sample.*` / `Sample.*`, so pytest does not collect them, and `sample.py` is valid ruff-clean Python. No config exclusions. (Task 1)
- **Subagent types and catalog failure:** grouping subagents are `general-purpose` (they write a file) with `model: haiku`; compare subagents are `general-purpose` with no model override and are told to read only. When `function-catalog.py` exits non-zero, the pass writes `Skipped: function-catalog.py exited <code>: <first stderr line>.` in place of the counts line and ends; the rest of the audit continues. (Task 2)
- **Leading whitespace:** every pattern allows leading spaces or tabs. The fixtures include an indented definition for every language except Go, whose functions and methods are top-level declarations. (Task 1)
- **Java/C# regex:** `^[ \t]*(?:public|protected|private|internal)\b[^=;(\n]*?\b([A-Za-z_]\w*)[ \t]*\(`. The name is the identifier immediately before the first `(`; a line with `=` or `;` before that `(` does not match. A captured name in `{if, else, for, foreach, while, do, switch, case, catch, try, return, new, throw, using, lock, synchronized, typeof, sizeof, nameof}` is dropped. Negative fixtures: an indented `if (x > 0) {` line and a field `private int count = compute(1);` in `Sample.java`; an `if (text == null)` line and a `private readonly Func<int> factory = () => 1;` field in `Sample.cs`. Those lines never reach the keyword filter (no modifier, or `=` first), so the filter itself is pinned by `test_java_keyword_names_dropped`, which calls `function_name` on `    public return(x);`. (Task 1)
- **`--batch-size` without `--split`:** ignored. `--batch-size` below 1 is a usage error (exit 2). `-o` and `--split` together are a usage error (exit 2). `--split` with 0 entries creates DIR, writes no batch file and prints `0`. `--split` first deletes any `batch-*.json` already in DIR. (Task 1)
- **Severity:** the session sets it from its own reading. Step 4 already makes it open every function in a HIGH or MEDIUM group to mark the finding `verified`; it then sets `Medium` when the functions return or do different things for the same input, else `Low`. Where it could not open a function, the finding is `inferred (from: duplicate-intent subagent)` and severity follows the subagent's "how they differ": `Medium` when that names a different result for the same input, else `Low`. (Task 2)
- **Join gap:** yes. After the re-dispatch, catalog entries with no matching `file`+`line` in any categorized output count as uncategorized; categorized entries with no catalog match are dropped. The report gets one line `Grouping gap: <k> of <n> functions not categorized (batches: <NNN, ...>).` when `k > 0`. (Task 2)

## Review Focus

- A catalog run on a repo with non-ASCII or space-containing paths: `git ls-files -z` is used, so such files are still catalogued with their real repo-relative path (test in Task 1).
- A tracked source file that is not UTF-8: skipped with one stderr line naming it, the run still exits 0 with the other files' entries (test in Task 1).
- `--split` into a folder left over from an earlier run with more batches: stale `batch-*.json` files are deleted first, so the session never reads an old batch (test in Task 1).
- `--split` on a repo with no functions: prints `0` and writes no batch files, rather than an empty `batch-001.json` (test in Task 1).
- A Windows checkout with CRLF fixtures: lines are split with `str.splitlines()`, so a trailing `\r` never reaches a name or a snippet (covered by every Task 1 test on Windows CI; snippets assert exact lines).

---

### Task 1: `function-catalog.py` and its tests

**Files:**
- Create: `plugin/scripts/function-catalog.py`
- Create: `tests/test_function_catalog.py`
- Create: `tests/fixtures/function_catalog/sample.py`, `sample.js`, `sample.ts`, `sample.go`, `sample.rs`, `Sample.java`, `Sample.cs`, `sample.kt`, `sample.rb`, `sample.sh`, `sample.ps1`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: CLI `python function-catalog.py <repo-root> [-o FILE | --split DIR] [--batch-size N] [--context N] [--include-tests]`. Entry JSON: `{"file": str, "line": int, "name": str, "language": str, "snippet": str}`. With no `-o`/`--split` the JSON array goes to stdout; with `-o FILE` the array goes to FILE (parents created) and stdout gets the entry count; with `--split DIR` stdout gets the batch-file count. Python API: `catalog(root: Path, *, context: int = 15, include_tests: bool = False) -> list[dict]` (raises `CatalogError(Exception)` on git failure); `function_name(line: str, language: str) -> str | None` (the name the line defines after the `_` and Java/C# keyword filters, else `None`); `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the fixtures**

Each file exactly as below (line numbers matter; tests assert them). Keep a final newline.

`sample.py`:
```python
"""Fixture for function-catalog tests."""


def read_config(path):
    return path


async def fetch_user(user_id):
    return user_id


def _private_helper():
    return None


class Store:
    def __init__(self):
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    async def save_all(self):
        return self.items
```

`sample.js`:
```javascript
export default async function loadData(url) {
  return url;
}

const formatName = (first, last) => `${first} ${last}`;

let parseDate = function (text) {
  return new Date(text);
};

function _hidden() {
  return 0;
}

export function normalizePath(p) {
  const trimSlashes = (s) => s.replace(/\/+$/, "");
  if (p) {
    return trimSlashes(p);
  }
  return p;
}
```

`sample.ts`:
```typescript
export const sumAll = (values: number[]): number =>
  values.reduce((a, b) => a + b, 0);
```

`sample.go`:
```go
package sample

func ParseConfig(path string) string {
	return path
}

type Server struct{}

func (s *Server) HandleRequest(name string) string {
	return name
}

func helperLower() {}
```

`sample.rs`:
```rust
pub fn parse_args(input: &str) -> String {
    input.to_string()
}

pub(crate) async fn fetch_remote(url: &str) -> String {
    url.to_string()
}

struct Cache;

impl Cache {
    fn get_entry(&self) -> u32 {
        0
    }
}

fn _unused() {}
```

`Sample.java`:
```java
public class Sample {
    private int count = compute(1);

    public static int compute(int x) {
        if (x > 0) {
            return x;
        }
        return 0;
    }

    protected <T> java.util.List<T> wrapAll(T item) {
        return java.util.List.of(item);
    }

    private void _skipMe() {}
}
```

`Sample.cs`:
```csharp
namespace Fixture
{
    public class Sample
    {
        internal static string FormatLabel(string text)
        {
            if (text == null) return "";
            return text.Trim();
        }

        public async Task<int> CountAsync() => await Task.FromResult(1);

        private readonly Func<int> factory = () => 1;
    }
}
```

`sample.kt`:
```kotlin
fun String.shout(): String = uppercase()

class Greeter {
    suspend fun greet(name: String): String {
        return name
    }

    private fun _internal() {}
}

internal fun <T> List<T>.second(): T = this[1]
```

`sample.rb`:
```ruby
class Formatter
  def self.build(options)
    new(options)
  end

  def render(text)
    text
  end

  def valid?
    true
  end
end
```

`sample.sh`:
```bash
#!/usr/bin/env bash

log_info() {
  echo "$1"
}

function cleanup_tmp {
  rm -rf "$1"
}

if true; then
  indented_task() {
    echo ok
  }
fi
```

`sample.ps1`:
```powershell
function Get-Report {
    param($Path)
    $Path
}

function _Hidden { }

    FUNCTION Set-Indented { }
```

- [ ] **Step 2: Write the failing tests in `tests/test_function_catalog.py`**

Module setup: `SCRIPT = PLUGIN / "scripts" / "function-catalog.py"`,
`FIXTURES = Path(__file__).parent / "fixtures" / "function_catalog"`, a
`git(*args, cwd)` helper (`subprocess.run(["git", *args], cwd=cwd, check=True,
capture_output=True, text=True)`), and a `make_repo(tmp_path, extra=None)`
helper that copies FIXTURES to `tmp_path / "repo"` (`shutil.copytree`),
writes each `extra` mapping `relative path -> str | bytes` (creating parents),
then `git init -q`, `git add -A -f` (`-f` so a global gitignore cannot
leave `node_modules`, `dist` or `.venv` extras untracked), and
`git -c user.name=t -c user.email=t@example.com commit -q -m init`, returning
the repo path. A `run(repo, *args)` helper returns `run_script(SCRIPT,
str(repo), *args)`; a `names(entries)` helper returns
`[(e["file"], e["line"], e["name"]) for e in entries]`.

Tests (names and assertions):

```python
EXPECTED = [
    ("Sample.cs", 5, "FormatLabel"),
    ("Sample.cs", 11, "CountAsync"),
    ("Sample.java", 4, "compute"),
    ("Sample.java", 11, "wrapAll"),
    ("sample.go", 3, "ParseConfig"),
    ("sample.go", 9, "HandleRequest"),
    ("sample.go", 13, "helperLower"),
    ("sample.js", 1, "loadData"),
    ("sample.js", 5, "formatName"),
    ("sample.js", 7, "parseDate"),
    ("sample.js", 15, "normalizePath"),
    ("sample.js", 16, "trimSlashes"),
    ("sample.kt", 1, "shout"),
    ("sample.kt", 4, "greet"),
    ("sample.kt", 11, "second"),
    ("sample.ps1", 1, "Get-Report"),
    ("sample.ps1", 8, "Set-Indented"),
    ("sample.py", 4, "read_config"),
    ("sample.py", 8, "fetch_user"),
    ("sample.py", 20, "add_item"),
    ("sample.py", 23, "save_all"),
    ("sample.rb", 2, "build"),
    ("sample.rb", 6, "render"),
    ("sample.rb", 10, "valid?"),
    ("sample.rs", 1, "parse_args"),
    ("sample.rs", 5, "fetch_remote"),
    ("sample.rs", 12, "get_entry"),
    ("sample.sh", 3, "log_info"),
    ("sample.sh", 7, "cleanup_tmp"),
    ("sample.sh", 12, "indented_task"),
    ("sample.ts", 1, "sumAll"),
]
```

- `test_every_language_yields_expected_names_and_lines`: `run(repo)` exits 0
  and `names(json.loads(out.stdout)) == EXPECTED` (this list is in sorted
  order: Python string sort puts uppercase `Sample.*` first). This also proves
  `_private` names and `__init__` are skipped and the Java/C# `if (` and
  `=` lines are not matched.
- `test_private_and_dunder_names_are_skipped`: no entry name starts with `_`.
- `test_language_labels`: the `language` of the first entry per file is
  `{"sample.py": "Python", "sample.js": "JavaScript/TypeScript",
  "sample.ts": "JavaScript/TypeScript", "sample.go": "Go", "sample.rs": "Rust",
  "Sample.java": "Java/C#", "Sample.cs": "Java/C#", "sample.kt": "Kotlin",
  "sample.rb": "Ruby", "sample.sh": "Shell", "sample.ps1": "PowerShell"}`.
- `test_tests_excluded_by_default_and_included_on_request`: `make_repo` with
  extra `{"tests/test_thing.py": "def case_one():\n    pass\n",
  "pkg/test_helpers.py": "def case_two():\n    pass\n",
  "pkg/widget_test.go": "package pkg\n\nfunc CaseThree() {}\n",
  "web/widget.spec.ts": "function caseFour() {}\n",
  "web/widget.test.js": "function caseFive() {}\n",
  "src/__tests__/a.js": "function caseSix() {}\n",
  "spec/b.rb": "def case_seven\nend\n"}`. Default run: none of
  `case_one … case_seven` (`case_one`, `case_two`, `CaseThree`, `caseFour`,
  `caseFive`, `caseSix`, `case_seven`) appear. With `--include-tests`: all
  seven appear.
- `test_vendored_and_build_paths_always_excluded`: extra
  `{"node_modules/pkg/index.js": "function vendoredA() {}\n",
  "vendor/x.go": "package x\n\nfunc VendoredB() {}\n",
  "dist/out.js": "function builtC() {}\n",
  "build/gen.py": "def built_d():\n    pass\n",
  ".venv/lib.py": "def venv_e():\n    pass\n",
  "third_party/t.rs": "fn third_f() {}\n",
  "app/lib.min.js": "function minifiedG() {}\n"}`; neither the default run
  nor `--include-tests` returns any of those seven names.
- `test_context_limits_snippet`: `run(repo, "--context", "2")`; the
  `read_config` entry's `snippet.split("\n") == ["def read_config(path):",
  "    return path", ""]`.
- `test_snippet_capped_at_1200_chars`: extra
  `{"long.py": "def long_one():\n" + ("    x = '" + "a" * 200 + "'\n") * 20}`;
  the `long_one` snippet has `len(...) == 1200`, and every entry in the run
  has `len(snippet) <= 1200`.
- `test_output_sorted_and_o_writes_same_json`: stdout run parses; entries
  equal `sorted(entries, key=lambda e: (e["file"], e["line"]))`;
  `run(repo, "-o", str(tmp_path / "out" / "cat.json"))` exits 0, its stdout
  stripped is `str(len(entries))`, and the file's parsed JSON equals the
  stdout run's.
- `test_split_writes_batches_in_order`: a fresh git repo (not `make_repo`)
  with only `a.py` holding five functions `def f1():` … `def f5():`
  (each followed by `    pass` and a blank line); first create
  `batches/batch-009.json` holding `[]`; then
  `run(repo, "--split", str(tmp_path / "batches"), "--batch-size", "2")`
  exits 0 with stdout stripped `"3"`; the folder holds exactly
  `batch-001.json`, `batch-002.json`, `batch-003.json` (the stale 009 is
  gone); their names are `["f1", "f2"]`, `["f3", "f4"]`, `["f5"]`.
- `test_split_with_no_functions_prints_zero`: a git repo with only
  `README.md`; `--split DIR` exits 0, prints `0`, DIR exists and is empty.
- `test_non_git_directory_exits_2`: `run(tmp_path / "plain")` on a plain
  folder holding `a.py` → returncode 2.
- `test_bad_usage_exits_2`: `-o x --split y` → 2; `--batch-size 0` with
  `--split y` → 2.
- `test_non_utf8_file_skipped_with_stderr_line`: extra
  `{"bad.py": b"def broken():\n    s = '\xff\xfe'\n"}`; returncode 0,
  `"bad.py"` in stderr, no entry from `bad.py`, `read_config` still present.
- `test_java_keyword_names_dropped`: load the script with
  `load_module(SCRIPT, "function_catalog")`;
  `fc.function_name("    public return(x);", "Java/C#") is None` and
  `fc.function_name("    public int compute(int x) {", "Java/C#") == "compute"`.
- `test_paths_with_spaces_and_non_ascii`: extra
  `{"my dir/café.py": "def brew():\n    pass\n"}`; the `brew` entry's
  `file == "my dir/café.py"`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pytest tests/test_function_catalog.py -o addopts=""`
Expected: FAIL (the script does not exist; nonzero returncodes).

- [ ] **Step 4: Implement `plugin/scripts/function-catalog.py`**

Signatures from the Interfaces block. Files come from
`git -C <root> ls-files -z` run with `encoding="utf-8"` (so non-ASCII paths
decode on Windows) and split on `\0`; a missing root, a non-repo, a
non-zero git exit or a missing `git` raises `CatalogError`, which `main`
reports on stderr with exit 2. Skip rules exactly as the spec's Design
lists them (path components and file-name globs via `fnmatch`). Read each
file as bytes and decode UTF-8 (`UnicodeDecodeError` → stderr line
`skipped (not UTF-8): <path>` and continue), split with `splitlines()`,
and match each line against its language's patterns with `re.match`
(per-line, equivalent to multiline `^`). First matching pattern wins; one
entry per line. Snippet: `"\n".join(lines[i : i + context + 1])[:1200]`.
Sort by `(file, line)`. JSON with `ensure_ascii=False, indent=1`.

Extension map: every extension in the spec's Design language table
(`.py`; `.js .jsx .mjs .cjs .ts .tsx`; `.go`; `.rs`; `.java .cs`; `.kt .kts`;
`.rb`; `.sh .bash`; `.ps1 .psm1`), with the language labels as in
`test_language_labels`. Patterns (the
algorithm the tests do not fully determine):

| Language | Patterns (name = group 1, or the non-empty group) |
|---|---|
| Python | `^[ \t]*(?:async[ \t]+)?def[ \t]+([A-Za-z_]\w*)[ \t]*\(` |
| JavaScript/TypeScript | `^[ \t]*(?:export[ \t]+)?(?:default[ \t]+)?(?:async[ \t]+)?function\*?[ \t]*([A-Za-z_$][\w$]*)[ \t]*\(` and `^[ \t]*(?:export[ \t]+)?(?:const\|let)[ \t]+([A-Za-z_$][\w$]*)[ \t]*(?::[^=\n]+)?=[ \t]*(?:async[ \t]+)?(?:function\b\|\([^)\n]*\)[^=\n]*=>\|[A-Za-z_$][\w$]*[ \t]*=>)` |
| Go | `^[ \t]*func[ \t]+(?:\([^)]*\)[ \t]*)?([A-Za-z_]\w*)[ \t]*[\[(]` |
| Rust | `^[ \t]*(?:pub(?:\([^)]*\))?[ \t]+)?(?:const[ \t]+)?(?:async[ \t]+)?(?:unsafe[ \t]+)?fn[ \t]+([A-Za-z_]\w*)` |
| Java/C# | the regex and keyword set from the plan questions above |
| Kotlin | `^[ \t]*(?:(?:public\|private\|protected\|internal\|override\|open\|suspend\|inline\|operator\|infix\|tailrec\|abstract\|final)[ \t]+)*fun[ \t]+(?:<[^>\n]*>[ \t]*)?(?:[\w.<>?, ]+\.)?([A-Za-z_]\w*)[ \t]*\(` |
| Ruby | `^[ \t]*def[ \t]+(?:self\.)?([A-Za-z_]\w*[?!=]?)` |
| Shell | `^[ \t]*function[ \t]+([A-Za-z_][\w-]*)` and `^[ \t]*([A-Za-z_][\w-]*)[ \t]*\(\)[ \t]*\{?` |
| PowerShell | `^[ \t]*function[ \t]+([A-Za-z_][\w-]*)` with `re.IGNORECASE` |

(`\|` in the table is a literal `|` in the regex.) Drop names starting with `_`.

`argparse`: `-o/--output` and `--split` in a mutually exclusive group;
`--batch-size` (int, default 150; below 1 → `parser.error`, exit 2);
`--context` (int, default 15, below 0 → `parser.error`); `--include-tests`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_function_catalog.py -o addopts=""`
Expected: all pass.

- [ ] **Step 6: Check spec success criterion 3 and lint**

Run: `python plugin/scripts/function-catalog.py . > %TEMP%/fc.json` (bash:
`python plugin/scripts/function-catalog.py . > "$TMPDIR/fc.json"` or use the
scratchpad), then
`python -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(len(d), all(e['file'].startswith('plugin/') for e in d))" <that file>`
Expected: a number of at least 50, then `True`. Delete the temp file.
Run: `ruff check plugin tests` and `ruff format --check plugin tests`; expected clean.

- [ ] **Step 7: Commit**

```bash
git add plugin/scripts/function-catalog.py tests/test_function_catalog.py tests/fixtures/function_catalog
git commit -m "Add function-catalog.py: a regex function catalog for the duplicate-intent pass"
```

### Task 2: `duplicates.md` and `audit` Pass 4

**Files:**
- Create: `plugin/skills/audit/duplicates.md`
- Modify: `plugin/skills/audit/SKILL.md` (Pass 3 Design bullet; new Pass 4 after Pass 3; Output list; chat report)
- Test: `tests/test_audit_skills.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: Task 1's CLI (`-o FILE` prints the entry count; `--split DIR` prints the batch count; exit 2 on failure) and the entry fields `file`, `line`, `name`.
- Produces: `plugin/skills/audit/duplicates.md`, which Task 3 points at as `../audit/duplicates.md` from `audit-deep`'s folder. Its output (counts line or a skip line, findings, LOW table, not-compared list, gap line) is the content both audits put in their duplicate-intent section.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_audit_skills.py`:

```python
DUPES = AUDIT / "duplicates.md"
CATALOG_REL = "../../scripts/function-catalog.py"
COUNTS_LINE = (
    "<n> functions catalogued; <u> of <t> compare units dispatched; "
    "groups: <h> HIGH, <m> MEDIUM, <l> LOW"
)


def flat(path):
    return " ".join(read(path).split())


def test_audit_skill_has_pass_4_and_section():
    body = read(AUDIT / "SKILL.md")
    assert "## Pass 4: duplicate intent" in body
    assert "duplicates.md" in body
    assert body.index("## Pass 3") < body.index("## Pass 4")
    assert body.index("`## Duplicate intent`") < body.index("`## What is missing`")
    assert "duplicated blocks inside functions" in flat(AUDIT / "SKILL.md")


def test_duplicates_procedure_names_its_limits():
    text = flat(DUPES)
    for phrase in (
        "function-catalog.py",
        "model: haiku",
        "no model override",
        "general-purpose",
        "20-function threshold",
        "3,000-function limit",
        "batches of 150",
        "at most 150",
        "at most 12",
        "audit-scratch",
        "HIGH",
        "MEDIUM",
        "LOW",
        COUNTS_LINE,
        "Skipped: <n> functions, below the 20-function threshold.",
        "Skipped: <n> functions, above the 3,000-function limit; "
        "audit a smaller repo.",
        "Skipped: function-catalog.py exited <code>",
        "Grouping gap:",
        "other: <subdomain>",
        "Duplicate intent: <intent>",
    ):
        assert phrase in text, phrase


def test_catalog_path_from_duplicates_resolves():
    assert CATALOG_REL in read(DUPES)
    assert (AUDIT / CATALOG_REL).resolve().is_file()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_audit_skills.py -o addopts=""`
Expected: the three new tests FAIL; the rest pass.

- [ ] **Step 3: Write `plugin/skills/audit/duplicates.md`**

A `# Duplicate-intent pass` heading, one paragraph saying who follows it
(Pass 4 of `audit`, Phase H of `audit-deep`, always the session running the
audit, because subagents cannot start subagents), then the spec's steps 1–5
(Design, "`plugin/skills/audit/duplicates.md`") in its own words, with these
plan decisions written in:

- Names: CATALOG is the absolute path of `../../scripts/function-catalog.py`
  from this file's folder; SCRATCH is the `audit-scratch` folder from
  `rules.md` section 1.
- Step 1: `python CATALOG <repo> -o SCRATCH/catalog.json` prints the entry
  count. Non-zero exit → the line `Skipped: function-catalog.py exited <code>:
  <first stderr line>.` and end. Then the two skip lines from Global
  Constraints, verbatim.
- Step 2: `--split SCRATCH/batches`; one `general-purpose` subagent per batch,
  all in one message, each with `model: haiku`; refused → that batch again
  with no model override. The prompt content as the spec lists it (the domain
  list verbatim, including `other: <subdomain>`, judge by what not how,
  one-sentence `purpose`, every entry, Write tool, `{file, line, name,
  domain, purpose}` only). Parse/count check and one re-dispatch as the spec
  says; then the join-gap rule and the `Grouping gap: <k> of <n> functions
  not categorized (batches: <NNN, ...>).` line.
- Step 3: domains are exact labels after trim and lowercase, so each
  `other: <subdomain>` is its own domain; 3 or more functions; largest
  first; over 150 split into chunks of at most 150 sorted by file then line;
  at most 12 units; one `general-purpose` subagent per unit, all in one
  message, no model override, told to read only; prompt and return shape as
  the spec lists (intent, `HIGH`/`MEDIUM`/`LOW` with their meanings,
  `path:line` with quoted definition line, how they differ, survivor and
  reason, or `none`). Units not dispatched are listed under "Not compared".
- Step 4: the finding mapping exactly as the spec lists (title
  `Duplicate intent: <intent>`, Where, Evidence, Confidence, Impact, Fix with
  its quoted sentence and effort S or M), and the severity rule from the plan
  questions above. LOW groups go in one table `| Intent | Functions |`, not
  findings.
- Output order, which the audits copy into their section: the counts line
  (verbatim template from Global Constraints) or the one skip line; the gap
  line if any; the findings; the LOW table; the "Not compared" list.
- Step 5: delete the scratch files this pass made.

Keep it under 150 lines.

- [ ] **Step 4: Edit `plugin/skills/audit/SKILL.md`**

- Pass 3, Design bullet: replace `duplication` with `duplicated blocks inside
  functions (duplicate functions are Pass 4's, so one root cause gets one
  finding)`.
- After Pass 3, add `## Pass 4: duplicate intent` with one paragraph: read
  `duplicates.md` in this skill's directory and follow it, with the target
  repo as `<repo>`.
- Output list: insert after item 3 (area sections) a new item 4:
  `` `## Duplicate intent` ``: Pass 4's output, opening with its counts line
  (or the skip line), then its findings, the LOW table, the domains not
  compared and any grouping gap; renumber `## What is missing` to 5 and
  `## Fix first` to 6, and add that Pass 4's findings enter `## Fix first`
  like any other.
- Chat paragraph: add "Pass 4's counts line (or skip line)" after the counts
  by severity.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_audit_skills.py tests/test_skill_size.py -o addopts=""`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/audit/duplicates.md plugin/skills/audit/SKILL.md tests/test_audit_skills.py
git commit -m "Add the duplicate-intent pass to the audit skill (Pass 4)"
```

### Task 3: `audit-deep` Phase H

**Files:**
- Modify: `plugin/skills/audit-deep/SKILL.md` (names list, Setup step 3, new Phase H, Phase G prompt, Report)
- Modify: `plugin/skills/audit-deep/phases/G-report.md`
- Modify: `plugin/skills/audit-deep/phases/E-design.md` (Antipatterns bullet)
- Test: `tests/test_audit_skills.py`

**Depends on:** Task 2

**Interfaces:**
- Consumes: `plugin/skills/audit/duplicates.md` (Task 2) and its output order.
- Produces: `REPO/docs/audit/07-duplicates.md` as a Phase G input.

- [ ] **Step 1: Write the failing tests**

In `tests/test_audit_skills.py`, add `"07-duplicates.md"` to `OUTPUTS`
(before `"report.html"`), then append:

```python
def test_deep_has_phase_h_between_e_and_f():
    body = read(DEEP / "SKILL.md")
    h = body.index("## Phase H: duplicate intent (this session)")
    assert body.index("Wait for all four") < h < body.index("## Phase F")
    assert "../audit/duplicates.md" in body
    assert (DEEP / "../audit/duplicates.md").resolve().is_file()


def test_deep_overwrite_list_and_g_inputs_name_duplicates():
    body = read(DEEP / "SKILL.md")
    setup = body.split("## Setup", 1)[1].split("## Phase A", 1)[0]
    assert "07-duplicates.md" in setup
    assert "00-repo-map.md to 06-onboarding.md and 07-duplicates.md" in (
        " ".join(body.split())
    )
    assert "07-duplicates.md" in read(DEEP / "phases" / "G-report.md")


def test_design_phase_leaves_duplicate_functions_to_phase_h():
    text = flat(DEEP / "phases" / "E-design.md")
    assert "Phase H" in text
    assert "duplicated blocks inside functions" in text
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_audit_skills.py -o addopts=""`
Expected: the three new tests and `test_deep_names_every_output` FAIL.

- [ ] **Step 3: Edit `plugin/skills/audit-deep/SKILL.md`**

- Names list: add `- DUPES: the absolute path of ../audit/duplicates.md from
  SKILL_DIR.` (with the path in backticks as RULES has).
- Setup step 3: add `` `07-duplicates.md` `` to the overwrite list (before
  `` `report.html` ``).
- After "Wait for all four. Rerun CHECKER on `02` to `05`. …" and before
  `## Phase F`, add `## Phase H: duplicate intent (this session)`: subagents
  cannot dispatch subagents, so this session runs it; read DUPES
  (`../audit/duplicates.md` from SKILL_DIR) and follow it with REPO as the
  repo; write `REPO/docs/audit/07-duplicates.md`: a `# Duplicate intent`
  heading, BAR, the date, then the counts line or the skip line, then the
  rest of the pass's output in DUPES's order; run CHECKER on it as for the
  other files.
- Phase G prompt: `The inputs are the files 00-repo-map.md to 06-onboarding.md
  and 07-duplicates.md in REPO/docs/audit/; ignore every other file there.`
- Report: add Phase H's counts line (or skip line) after the counts by
  severity per area.
- Phase F stays unchanged.

- [ ] **Step 4: Edit the phase files**

- `phases/G-report.md`: after the opening paragraph, add one line: the inputs
  include `07-duplicates.md` (duplicate intent), an area like the others; its
  LOW table and counts line are not findings.
- `phases/E-design.md`, Antipatterns bullet: replace `copy-paste duplication`
  with `duplicated blocks inside functions (duplicate functions, the same
  intent written twice, are left to Phase H)`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_audit_skills.py tests/test_skill_size.py -o addopts=""`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/audit-deep tests/test_audit_skills.py
git commit -m "Add Phase H (duplicate intent) to audit-deep"
```

### Task 4: Version, description, README and index

**Files:**
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `tests/test_plugin_manifest.py`
- Modify: `README.md` (the `plugin/` bullet, around line 86)
- Modify: `docs/superpowers/README.md` (regenerated)

**Depends on:** Task 1, Task 2, Task 3

Task 4 runs last so its full-suite run and the criterion 5 diff check see
every task's changes.

**Interfaces:**
- Consumes: nothing.
- Produces: version `0.29.0`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_plugin_manifest.py`, rename `test_version_is_0_28_0` to
`test_version_is_0_29_0` asserting `data["version"] == "0.29.0"`, and append:

```python
def test_description_mentions_duplicate_intent():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert "duplicate-intent pass" in data["description"]
    assert "function-catalog.py" in data["description"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_plugin_manifest.py -o addopts=""`
Expected: the two tests FAIL.

- [ ] **Step 3: Edit `plugin.json` and `README.md`**

- `plugin.json`: `"version": "0.29.0"`; in `description` replace the ending
  `CLAUDE_KIT_VAULT is set)."` with `CLAUDE_KIT_VAULT is set), and a
  duplicate-intent pass in audit and audit-deep (function-catalog.py lists
  the functions, Haiku subagents group them by domain, and the session's
  model compares each domain)."`
- `README.md`: in the `plugin/` bullet, replace `(the audits share a citation
  checker, `check-findings.py`)` (it wraps across lines; match the text, not
  the line breaks) with `(the audits share a citation checker,
  `check-findings.py`, and a duplicate-intent pass that lists functions with
  `function-catalog.py` and compares them by domain)`.

- [ ] **Step 4: Regenerate the index and run the full checks**

Run: `python plugin/scripts/spec-index.py docs/superpowers`
Expected: `docs/superpowers/README.md` has rows for this spec and this plan
(the spec-index hook may have added them already, so no change is fine).
Run: `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`.
Expected: all pass, both ruff commands clean.

- [ ] **Step 5: Check spec success criterion 5**

Run (bash): `git diff origin/main | grep -i -E "<pattern>"` where `<pattern>`
is the machine's username plus every name from
`gh repo list --visibility private --json name -q ".[].name"`, joined with `|`.
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py README.md docs/superpowers/README.md
git commit -m "Bump to 0.29.0 and document the duplicate-intent pass"
```

## After the tasks

- **Spec success criterion 4 (live check after merge).** Nothing in `/ship`'s
  finish steps runs it, so the executor does it explicitly: during `/ship`
  step 10 ("Verify main"), after the suite and lint pass in the detached
  `<tmp>` worktree at the squash commit and before `git worktree remove`, run
  `claude-kit:audit` with `<tmp>` as its target (answer its overwrite
  question with yes; the folder is throwaway), then
  `python plugin/scripts/check-findings.py <tmp> <tmp>/docs/audit/audit.md`
  from `<tmp>`. Expected: exit 0, and `audit.md` has a `## Duplicate intent`
  section opening with the counts line (or a skip line). Copy that line
  verbatim into the step 12 report, labelled "Pass 4 counts line". Never
  commit `docs/audit/`; it goes away with `<tmp>`.
- **Spec success criterion 6** (squash-merge with green CI) is covered by
  `/ship` steps 8–10.
