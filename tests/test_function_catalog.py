"""Tests for plugin/scripts/function-catalog.py."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "function-catalog.py"
FIXTURES = Path(__file__).parent / "fixtures" / "function_catalog"

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

COMMIT = ["-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q"]


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def write_extra(repo: Path, extra: dict[str, str | bytes]) -> None:
    for rel, content in extra.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8", newline="\n")


def commit_all(repo: Path) -> None:
    git("init", "-q", cwd=repo)
    git("add", "-A", "-f", cwd=repo)
    git(*COMMIT, "-m", "init", cwd=repo)


def make_repo(tmp_path: Path, extra: dict[str, str | bytes] | None = None) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES, repo)
    write_extra(repo, extra or {})
    commit_all(repo)
    return repo


def make_bare_repo(tmp_path: Path, files: dict[str, str | bytes]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    write_extra(repo, files)
    commit_all(repo)
    return repo


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_script(SCRIPT, str(repo), *args)


def names(entries: list[dict]) -> list[tuple[str, int, str]]:
    return [(e["file"], e["line"], e["name"]) for e in entries]


def test_every_language_yields_expected_names_and_lines(tmp_path):
    out = run(make_repo(tmp_path))
    assert out.returncode == 0, out.stderr
    assert names(json.loads(out.stdout)) == EXPECTED


def test_private_and_dunder_names_are_skipped(tmp_path):
    entries = json.loads(run(make_repo(tmp_path)).stdout)
    assert entries
    assert not [e for e in entries if e["name"].startswith("_")]


def test_language_labels(tmp_path):
    entries = json.loads(run(make_repo(tmp_path)).stdout)
    first: dict[str, str] = {}
    for e in entries:
        first.setdefault(e["file"], e["language"])
    assert first == {
        "sample.py": "Python",
        "sample.js": "JavaScript/TypeScript",
        "sample.ts": "JavaScript/TypeScript",
        "sample.go": "Go",
        "sample.rs": "Rust",
        "Sample.java": "Java/C#",
        "Sample.cs": "Java/C#",
        "sample.kt": "Kotlin",
        "sample.rb": "Ruby",
        "sample.sh": "Shell",
        "sample.ps1": "PowerShell",
    }


def test_tests_excluded_by_default_and_included_on_request(tmp_path):
    extra = {
        "tests/test_thing.py": "def case_one():\n    pass\n",
        "pkg/test_helpers.py": "def case_two():\n    pass\n",
        "pkg/widget_test.go": "package pkg\n\nfunc CaseThree() {}\n",
        "web/widget.spec.ts": "function caseFour() {}\n",
        "web/widget.test.js": "function caseFive() {}\n",
        "src/__tests__/a.js": "function caseSix() {}\n",
        "spec/b.rb": "def case_seven\nend\n",
    }
    repo = make_repo(tmp_path, extra)
    wanted = {
        "case_one",
        "case_two",
        "CaseThree",
        "caseFour",
        "caseFive",
        "caseSix",
        "case_seven",
    }
    default = {e["name"] for e in json.loads(run(repo).stdout)}
    assert not wanted & default
    included = {e["name"] for e in json.loads(run(repo, "--include-tests").stdout)}
    assert wanted <= included


def test_vendored_and_build_paths_always_excluded(tmp_path):
    extra = {
        "node_modules/pkg/index.js": "function vendoredA() {}\n",
        "vendor/x.go": "package x\n\nfunc VendoredB() {}\n",
        "dist/out.js": "function builtC() {}\n",
        "build/gen.py": "def built_d():\n    pass\n",
        ".venv/lib.py": "def venv_e():\n    pass\n",
        "third_party/t.rs": "fn third_f() {}\n",
        "app/lib.min.js": "function minifiedG() {}\n",
    }
    repo = make_repo(tmp_path, extra)
    unwanted = {
        "vendoredA",
        "VendoredB",
        "builtC",
        "built_d",
        "venv_e",
        "third_f",
        "minifiedG",
    }
    for args in ((), ("--include-tests",)):
        found = {e["name"] for e in json.loads(run(repo, *args).stdout)}
        assert not unwanted & found


def test_context_limits_snippet(tmp_path):
    entries = json.loads(run(make_repo(tmp_path), "--context", "2").stdout)
    entry = next(e for e in entries if e["name"] == "read_config")
    assert entry["snippet"].split("\n") == [
        "def read_config(path):",
        "    return path",
        "",
    ]


def test_snippet_capped_at_1200_chars(tmp_path):
    body = "def long_one():\n" + ("    x = '" + "a" * 200 + "'\n") * 20
    repo = make_repo(tmp_path, {"long.py": body})
    entries = json.loads(run(repo).stdout)
    entry = next(e for e in entries if e["name"] == "long_one")
    assert len(entry["snippet"]) == 1200
    assert all(len(e["snippet"]) <= 1200 for e in entries)


def test_output_sorted_and_o_writes_same_json(tmp_path):
    repo = make_repo(tmp_path)
    first = run(repo)
    entries = json.loads(first.stdout)
    assert entries == sorted(entries, key=lambda e: (e["file"], e["line"]))
    target = tmp_path / "out" / "cat.json"
    out = run(repo, "-o", str(target))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == str(len(entries))
    assert json.loads(target.read_text(encoding="utf-8")) == entries


def test_split_writes_batches_in_order(tmp_path):
    funcs = "".join(f"def f{i}():\n    pass\n\n" for i in range(1, 6))
    repo = make_bare_repo(tmp_path, {"a.py": funcs})
    batches = tmp_path / "batches"
    batches.mkdir()
    (batches / "batch-009.json").write_text("[]", encoding="utf-8")
    out = run(repo, "--split", str(batches), "--batch-size", "2")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "3"
    assert sorted(p.name for p in batches.iterdir()) == [
        "batch-001.json",
        "batch-002.json",
        "batch-003.json",
    ]
    got = [
        [e["name"] for e in json.loads((batches / n).read_text(encoding="utf-8"))]
        for n in ("batch-001.json", "batch-002.json", "batch-003.json")
    ]
    assert got == [["f1", "f2"], ["f3", "f4"], ["f5"]]


def test_split_with_no_functions_prints_zero(tmp_path):
    repo = make_bare_repo(tmp_path, {"README.md": "# hi\n"})
    batches = tmp_path / "batches"
    out = run(repo, "--split", str(batches))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "0"
    assert batches.is_dir()
    assert list(batches.iterdir()) == []


def test_non_git_directory_exits_2(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
    assert run(plain).returncode == 2


def test_bad_usage_exits_2(tmp_path):
    repo = make_repo(tmp_path)
    assert run(repo, "-o", "x", "--split", "y").returncode == 2
    assert run(repo, "--batch-size", "0", "--split", "y").returncode == 2


def test_non_utf8_file_skipped_with_stderr_line(tmp_path):
    extra = {"bad.py": b"def broken():\n    s = '\xff\xfe'\n"}
    out = run(make_repo(tmp_path, extra))
    assert out.returncode == 0, out.stderr
    assert "bad.py" in out.stderr
    entries = json.loads(out.stdout)
    assert not [e for e in entries if e["file"] == "bad.py"]
    assert any(e["name"] == "read_config" for e in entries)


def test_java_keyword_names_dropped():
    fc = load_module(SCRIPT, "function_catalog")
    assert fc.function_name("    public return(x);", "Java/C#") is None
    line = "    public int compute(int x) {"
    assert fc.function_name(line, "Java/C#") == "compute"


def test_js_function_keyword_needs_a_boundary():
    fc = load_module(SCRIPT, "function_catalog")
    lang = "JavaScript/TypeScript"
    assert fc.function_name("functionCall(x);", lang) is None
    assert fc.function_name("function* gen() {", lang) == "gen"
    assert fc.function_name("function *gen() {", lang) == "gen"
    assert fc.function_name("function foo(a) {", lang) == "foo"


def test_unwritable_split_target_is_one_line_exit_2(tmp_path):
    repo = make_repo(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("not a folder", encoding="utf-8")
    out = run(repo, "--split", str(blocker))
    assert out.returncode == 2
    assert "Traceback" not in out.stderr
    assert len(out.stderr.strip().splitlines()) == 1
    assert out.stderr.startswith("function-catalog:")


def test_unwritable_output_target_is_one_line_exit_2(tmp_path):
    repo = make_repo(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("not a folder", encoding="utf-8")
    out = run(repo, "-o", str(blocker / "catalog.json"))
    assert out.returncode == 2
    assert "Traceback" not in out.stderr
    assert len(out.stderr.strip().splitlines()) == 1


def test_paths_with_spaces_and_non_ascii(tmp_path):
    extra = {"my dir/café.py": "def brew():\n    pass\n"}
    entries = json.loads(run(make_repo(tmp_path, extra)).stdout)
    entry = next(e for e in entries if e["name"] == "brew")
    assert entry["file"] == "my dir/café.py"
