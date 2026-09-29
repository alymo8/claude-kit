# jev offline labelling and baseline Implementation Plan

- **Status:** implemented
- **Date:** 2026-09-28

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user label prompts and measure a no-jev baseline before they have a `TYPESAFE_API_KEY`: `replay --no-judge`, `replay --since`, `replay --rescore`, a `session_id` column, and a `baseline` subcommand in `plugin/scripts/jev-eval.py`.

**Architecture:** All changes are in the existing stdlib-only script `plugin/scripts/jev-eval.py` (it imports the hook module `plugin/hooks/jev_triage.py` as `triage`) and its tests in `tests/test_jev_eval.py`. Row building is split into `empty_row` (no network) and `score_row` (calls `triage.judge`), so replay, `--no-judge` and `--rescore` share one code path. `baseline` reuses the report's `turns`, `match` and `Outcome` definitions, with the user's labels in place of jev's scores.

**Tech Stack:** Python ≥ 3.11 stdlib, pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-09-28-jev-offline-baseline-design.md` (extends `docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md`)

## Global Constraints

- No change to `plugin/hooks/jev_triage.py`, its questions or its log format.
- Every new path (`--no-judge`, `--since`, `baseline`) makes no network call and needs no key and no SDK. Tests never call the real API.
- `--rescore` never damages `labels.csv`: it writes to a temporary file and renames it, and on `missing_key`/`missing_sdk` the file stays byte-for-byte unchanged.
- `labels.csv` columns, in order: `id, project, session_id, prompt, s_underspecified, s_new_feature, s_key_decision, latency_ms, input_tokens, output_tokens, label_underspecified, label_new_feature, label_key_decision`. Written as UTF-8 with BOM, comma-delimited.
- Outputs live in `~/.claude/claude-kit/jev/` (`triage.jev_dir()`); `baseline.csv` goes next to the labels file it reads. The repo is public: no real prompts, private repo names or usernames in tracked files.
- Ruff `E, F, I, UP, B`, line length 88 (E501 applies; run `ruff format plugin tests`, then rewrap anything `ruff check` still flags). In tests, `from helpers import ...` sits in the same import block as `pytest` (ruff I001).
- Before every commit: `pytest` and `ruff check plugin tests; ruff format --check plugin tests`, all green. Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- The developer shell may set `CLAUDE_KIT_*` variables. The tests' `dirs` fixture clears the threshold overrides; tests that need no key patch `triage.judge` and block `typesafe_sdk`.

## Review Focus

1. **`labels.csv` re-saved by Excel** (semicolons, cp1252, a smart quote) and then `--rescore`d: labels and prompt text must survive. Covered in Task 2 by `test_rescore_keeps_labels_from_an_excel_file`.
2. **A key that fails on the first call** (`missing_key`) during `--rescore`: the file must stay untouched. Covered in Task 2 by `test_rescore_missing_key_leaves_file_untouched`.
3. **Records without a `timestamp`** when `--since` is given must be dropped, and kept when it isn't. Covered in Task 1 by `test_iter_prompts_since`.
4. **Labelled rows whose transcript was deleted, or whose prompt no longer matches** (for example text altered by an ANSI save) must be counted as skipped, not crash `baseline`. Covered in Task 3 by `test_baseline_end_to_end`.
5. **`baseline` on a file with no labels yet** (the state right after `--no-judge`) must exit 0 and report every row as skipped. Covered in Task 3 by `test_baseline_unlabelled_file`.

---

### Task 1: `session_id`, `--since` and `--no-judge`

**Files:**
- Modify: `plugin/scripts/jev-eval.py` (`LABEL_FIELDS`, `iter_prompts`, `sample`, `label_row` → `empty_row` + `score_row`, `cmd_replay`, `main`)
- Modify: `tests/test_jev_eval.py` (update `test_iter_prompts_keeps_only_typed_prompts`, `test_sample_is_stratified_and_deduplicated`, `test_replay_writes_labels`; add new tests)

**Interfaces:**
- Produces: `iter_prompts(files, since: str = "") -> Iterator[tuple[str, str, str]]` yielding `(project, session_id, text)`; `sample(prompts: list[tuple[str, str, str]], n, seed) -> list[tuple[str, str, str]]`; `empty_row(i: int, project: str, session_id: str, text: str) -> dict`; `score_row(row: dict) -> dict` (fills `s_*`, `latency_ms`, `input_tokens`, `output_tokens` in place and returns the row; re-raises `JevError` for `missing_key`/`missing_sdk`, otherwise prints and leaves them empty).

- [ ] **Step 1: Update and add tests** in `tests/test_jev_eval.py`. Add `import sys` to the imports.

Replace the body of `test_iter_prompts_keeps_only_typed_prompts` and `test_sample_is_stratified_and_deduplicated` with:

```python
def test_iter_prompts_keeps_only_typed_prompts(tmp_path):
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", FIXTURE, junk=True)
    assert list(ev.iter_prompts([path])) == [
        ("proj-a", "s1", "add a dark mode toggle to settings"),
        ("proj-a", "s1", "why does the login test fail"),
    ]


def test_sample_is_stratified_and_deduplicated():
    prompts = [
        ("a", "s1", "p1 x y"),
        ("a", "s1", "p1 x y"),
        ("a", "s2", "p2 x y"),
        ("b", "s3", "q1 x y"),
    ]
    three = ev.sample(prompts, 3, 0)
    assert len(three) == 3
    assert len({t for _, _, t in three}) == 3
    assert {p for p, _, _ in ev.sample(prompts, 2, 0)} == {"a", "b"}
```

In `test_replay_writes_labels`, add after `assert rows[0]["label_new_feature"] == ""`:

```python
    assert rows[0]["session_id"] == "s1"
```

Append:

```python
def dated(text, day):
    return user(text, timestamp=f"{day}T10:00:00.000Z")


def test_iter_prompts_since(tmp_path):
    records = [
        dated("an old prompt from july", "2026-07-15"),
        dated("a prompt from the first day", "2026-08-01"),
        user("a prompt with no timestamp"),
    ]
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", records)
    assert [t for _, _, t in ev.iter_prompts([path], "2026-08-01")] == [
        "a prompt from the first day"
    ]
    assert len(list(ev.iter_prompts([path]))) == 3


def must_not_call(prompt):
    raise AssertionError("judge must not be called")


def test_replay_no_judge_needs_no_key(monkeypatch, dirs):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", FIXTURE)
    monkeypatch.setattr(triage, "judge", must_not_call)
    monkeypatch.setitem(sys.modules, "typesafe_sdk", None)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert ev.main(["replay", "--no-judge"]) == 0
    rows = read_rows(jev / "labels.csv")
    assert list(rows[0]) == ev.LABEL_FIELDS
    assert [r["session_id"] for r in rows] == ["s1", "s1"]
    for row in rows:
        assert row["s_new_feature"] == row["latency_ms"] == row["input_tokens"] == ""
    assert ev.main(["replay", "--no-judge"]) == 1  # the overwrite guard holds


def test_replay_since_filters_the_sample(monkeypatch, dirs):
    projects, jev = dirs
    records = [
        dated("an old prompt from july", "2026-07-15"),
        dated("a prompt from august", "2026-08-02"),
    ]
    write_jsonl(projects / "proj-a" / "s1.jsonl", records)
    assert ev.main(["replay", "--no-judge", "--since", "2026-08-01"]) == 0
    assert [r["prompt"] for r in read_rows(jev / "labels.csv")] == [
        "a prompt from august"
    ]
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_eval.py -v` → the 2 updated tests and the new ones FAIL (tuples of 2; `--no-judge`/`--since` unknown, argparse exits 2; `session_id` missing).

- [ ] **Step 3: Implement** in `plugin/scripts/jev-eval.py`.

In `LABEL_FIELDS`, insert `"session_id",` between `"project",` and `"prompt",`.

Replace `iter_prompts` and `sample` with:

```python
def iter_prompts(
    files: Iterable[Path], since: str = ""
) -> Iterator[tuple[str, str, str]]:
    """(project, session_id, text) for every prompt the hook would judge."""
    for path in files:
        for record in read_jsonl(path):
            if since and str(record.get("timestamp") or "")[:10] < since:
                continue
            text = prompt_text(record)
            if text:
                yield path.parent.name, path.stem, text


def sample(
    prompts: list[tuple[str, str, str]], n: int, seed: int
) -> list[tuple[str, str, str]]:
    """Up to n distinct prompts, round-robin across projects."""
    rng = random.Random(seed)
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    seen: set[str] = set()
    for project, session_id, text in prompts:
        if text not in seen:
            seen.add(text)
            groups[project].append((session_id, text))
    for entries in groups.values():
        rng.shuffle(entries)
    order = sorted(groups)
    rng.shuffle(order)
    chosen: list[tuple[str, str, str]] = []
    while len(chosen) < n and any(groups[p] for p in order):
        for project in order:
            if groups[project] and len(chosen) < n:
                session_id, text = groups[project].pop()
                chosen.append((project, session_id, text))
    return chosen
```

Replace `label_row` with:

```python
SCORE_FIELDS = (
    *(f"s_{k}" for k in triage.KEYS),
    "latency_ms",
    "input_tokens",
    "output_tokens",
)


def empty_row(i: int, project: str, session_id: str, text: str) -> dict:
    """A labels.csv row with no scores and no labels."""
    row = dict.fromkeys(LABEL_FIELDS, "")
    row.update(id=i, project=project, session_id=session_id, prompt=text)
    return row


def score_row(row: dict) -> dict:
    """Judge row["prompt"] and fill the score columns; raises JevError when jev
    cannot be reached at all (missing key or SDK)."""
    for name in SCORE_FIELDS:
        row[name] = ""
    start = time.perf_counter()
    try:
        judgment = triage.judge(str(row.get("prompt") or ""))
    except triage.JevError as exc:
        if exc.code in ("missing_key", "missing_sdk"):
            raise
        print(f"prompt {row.get('id')}: {exc.code}", file=sys.stderr)
        return row
    usage = judgment.usage or {}
    for key in triage.KEYS:
        if key in judgment.scores:
            row[f"s_{key}"] = f"{judgment.scores[key]:.4f}"
    row["latency_ms"] = round((time.perf_counter() - start) * 1000)
    row["input_tokens"] = usage.get("input_tokens") or ""
    row["output_tokens"] = usage.get("output_tokens") or ""
    return row
```

Replace `cmd_replay` with (Task 2 adds `--rescore` at the top):

```python
def write_labels(path: Path, rows: list[dict]) -> None:
    """Write via a temporary file and a rename, so a failure never truncates."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=LABEL_FIELDS, restval="", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def cmd_replay(args: argparse.Namespace) -> int:
    out = triage.jev_dir() / "labels.csv"
    if out.exists() and not args.force:
        print(f"{out} exists; pass --force to overwrite", file=sys.stderr)
        return 1
    files = sorted(projects_dir().glob("*/*.jsonl"))
    chosen = sample(list(iter_prompts(files, args.since)), args.n, args.seed)
    rows = [empty_row(i, p, s, t) for i, (p, s, t) in enumerate(chosen, 1)]
    if not args.no_judge:
        try:
            rows = [score_row(row) for row in rows]
        except triage.JevError as exc:
            print(f"cannot judge: {exc.code}", file=sys.stderr)
            return 1
    write_labels(out, rows)
    print(f"wrote {len(rows)} prompts to {out}")
    print("fill the label_* columns with 1 or 0, then run: jev-eval.py baseline")
    return 0
```

Add `import os` to the imports. In `main`, after `replay.add_argument("--force", action="store_true")`, add:

```python
    replay.add_argument("--since", default="", help="YYYY-MM-DD")
    replay.add_argument("--no-judge", action="store_true")
```

- [ ] **Step 4: Verify.** `pytest tests/test_jev_eval.py -v` → PASS; full `pytest`; `ruff format plugin tests`; `ruff check plugin tests`.

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-eval.py tests/test_jev_eval.py
git commit -m "jev-eval: replay --no-judge and --since; session_id column

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `replay --rescore`

**Files:**
- Modify: `plugin/scripts/jev-eval.py` (`cmd_replay`, `main`)
- Modify: `tests/test_jev_eval.py` (append)

**Interfaces:**
- Consumes: `read_labels(path) -> list[dict]` (existing tolerant reader), `score_row`, `write_labels`, `LABEL_FIELDS` from Task 1.
- Produces: `cmd_rescore(path: Path) -> int`. The `replay` parser rejects `--rescore` together with `--no-judge` (argparse mutually exclusive group, exit 2) and together with `--n`, `--seed` or `--since` (`parser.error`, exit 2). The `--n` and `--seed` defaults become `None`, resolved to 60 and 0.

- [ ] **Step 1: Write the failing tests** by appending to `tests/test_jev_eval.py`:

```python
def labelled_file(monkeypatch, dirs, delimiter=",", encoding="utf-8-sig"):
    """Run replay --no-judge, label row 1 as a feature, and save in a given format."""
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", FIXTURE)
    monkeypatch.setattr(triage, "judge", must_not_call)
    assert ev.main(["replay", "--no-judge"]) == 0
    rows = read_rows(jev / "labels.csv")
    rows[0].update(label_underspecified="0", label_new_feature="1",
                   label_key_decision="0")  # fmt: skip
    rows[1]["prompt"] = rows[1]["prompt"] + " – “quoted”"
    path = jev / "labels.csv"
    with path.open("w", encoding=encoding, newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ev.LABEL_FIELDS, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    return path, rows


def test_rescore_keeps_labels_from_an_excel_file(monkeypatch, dirs):
    path, before = labelled_file(monkeypatch, dirs, delimiter=";", encoding="cp1252")
    monkeypatch.setattr(triage, "judge", fake)
    assert ev.main(["replay", "--rescore"]) == 0
    after = read_rows(path)
    assert [r["prompt"] for r in after] == [r["prompt"] for r in before]
    assert [r["session_id"] for r in after] == ["s1", "s1"]
    assert after[0]["label_new_feature"] == "1"
    assert after[1]["label_new_feature"] == ""
    assert {r["s_new_feature"] for r in after} == {"0.9000"}
    assert {r["input_tokens"] for r in after} == {"10"}
    assert not path.with_name("labels.csv.tmp").exists()


def test_rescore_missing_key_leaves_file_untouched(monkeypatch, dirs):
    path, _ = labelled_file(monkeypatch, dirs)
    original = path.read_bytes()

    def no_key(prompt):
        raise triage.JevError("missing_key")

    monkeypatch.setattr(triage, "judge", no_key)
    assert ev.main(["replay", "--rescore"]) == 1
    assert path.read_bytes() == original


def test_rescore_without_labels_file(dirs, capsys):
    assert ev.main(["replay", "--rescore"]) == 1
    assert "not found" in capsys.readouterr().err


@pytest.mark.parametrize(
    "extra", [["--no-judge"], ["--n", "5"], ["--seed", "1"], ["--since", "2026-08-01"]]
)
def test_rescore_rejects_sampling_options(dirs, extra):
    with pytest.raises(SystemExit) as info:
        ev.main(["replay", "--rescore", *extra])
    assert info.value.code == 2
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_eval.py -v` → the new tests FAIL (`--rescore` unknown, argparse exits 2 where 0/1 is expected).

- [ ] **Step 3: Implement.** Add above `cmd_replay`:

```python
def cmd_rescore(path: Path) -> int:
    """Fill jev scores into an existing labels.csv, keeping every label."""
    if not path.is_file():
        print(f"{path} not found; run: jev-eval.py replay --no-judge", file=sys.stderr)
        return 1
    rows = read_labels(path)
    try:
        rows = [score_row(row) for row in rows]
    except triage.JevError as exc:
        print(f"cannot judge: {exc.code}; {path} left unchanged", file=sys.stderr)
        return 1
    write_labels(path, rows)
    print(f"rescored {len(rows)} prompts in {path}; next: jev-eval.py score")
    return 0
```

At the top of `cmd_replay`, before the `out.exists()` check:

```python
    if args.rescore:
        return cmd_rescore(triage.jev_dir() / "labels.csv")
```

Then resolve the defaults after the `out.exists()` check: replace `args.n, args.seed` in the `sample(...)` call with `60 if args.n is None else args.n, 0 if args.seed is None else args.seed`.

In `main`, replace the replay arguments with:

```python
    replay = sub.add_parser("replay", help="sample past prompts into labels.csv")
    replay.add_argument("--n", type=int, default=None, help="default 60")
    replay.add_argument("--seed", type=int, default=None, help="default 0")
    replay.add_argument("--force", action="store_true")
    replay.add_argument("--since", default="", help="YYYY-MM-DD")
    how = replay.add_mutually_exclusive_group()
    how.add_argument("--no-judge", action="store_true", help="no key needed")
    how.add_argument("--rescore", action="store_true", help="score labels.csv")
```

and, right after `args = parser.parse_args(argv)`:

```python
    if args.command == "replay" and args.rescore:
        if args.n is not None or args.seed is not None or args.since:
            replay.error("--rescore keeps the existing sample; drop --n/--seed/--since")
```

- [ ] **Step 4: Verify.** `pytest tests/test_jev_eval.py -v` → PASS; full `pytest`; ruff format and check.

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-eval.py tests/test_jev_eval.py
git commit -m "jev-eval: replay --rescore fills scores and keeps labels

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `baseline`

**Files:**
- Modify: `plugin/scripts/jev-eval.py` (new functions after `cmd_report`; `main`)
- Modify: `tests/test_jev_eval.py` (append)

**Interfaces:**
- Consumes: `read_labels`, `parse_label`, `transcript_for`, `turns`, `match`, `Outcome`, `ratio`, `fmt`, `triage.KEYS`.
- Produces: `baseline_rows(rows) -> tuple[list[tuple[dict, dict[str, int], Outcome]], Counter]`, returning the matched rows with their labels and outcome, plus skip counts keyed `unlabelled`, `no transcript`, `not found`; `baseline_stats(results) -> dict[str, tuple[int, int]]` with keys `preflight_miss`, `not_asked`, `corrected_positive`, `corrected_other`, each `(k, n)`; `cmd_baseline(args) -> int`.
- `baseline.csv` columns: `id, session_id, label_underspecified, label_new_feature, label_key_decision, asked, preflight, corrected`.

- [ ] **Step 1: Write the failing tests** by appending to `tests/test_jev_eval.py`. They reuse `SESSION`, `P1`–`P4`, `write_jsonl`, `read_rows` and `dirs`, which are already defined above.

```python
def label_rows(entries):
    """entries: (session_id, prompt, (u, f, k)) with "" for a blank label."""
    rows = []
    for i, (session_id, prompt, (u, f, k)) in enumerate(entries, 1):
        row = ev.empty_row(i, "proj-a", session_id, prompt)
        row.update(label_underspecified=u, label_new_feature=f, label_key_decision=k)
        rows.append(row)
    return rows


def test_baseline_end_to_end(dirs, capsys):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", SESSION, junk=True)
    rows = label_rows(
        [
            ("s1", P1, ("0", "1", "0")),  # feature, edited before the check: miss
            ("s1", P2, ("0", "1", "0")),  # feature, check then Write: ok
            ("s1", P3, ("1", "0", "0")),  # vague, Claude asked: ok
            ("s1", P4, ("0", "0", "0")),  # neither
            ("s1", P4, ("", "", "")),  # unlabelled
            ("gone", P1, ("0", "1", "0")),  # transcript missing
            ("s1", "never typed here", ("1", "0", "0")),  # not in the transcript
        ]
    )
    ev.write_labels(jev / "labels.csv", rows)

    results, skipped = ev.baseline_rows(ev.read_labels(jev / "labels.csv"))
    assert dict(skipped) == {"unlabelled": 1, "no transcript": 1, "not found": 1}
    stats = ev.baseline_stats(results)
    assert stats["preflight_miss"] == (1, 2)
    assert stats["not_asked"] == (0, 1)
    assert stats["corrected_positive"] == (1, 3)
    assert stats["corrected_other"] == (0, 1)

    assert ev.main(["baseline"]) == 0
    out = capsys.readouterr().out
    assert "1/2 (50%)" in out
    assert "unlabelled 1" in out
    spot = read_rows(jev / "baseline.csv")
    assert len(spot) == 4
    assert spot[0]["preflight"] == "False"


def test_baseline_unlabelled_file(monkeypatch, dirs, capsys):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", FIXTURE)
    monkeypatch.setattr(triage, "judge", must_not_call)
    assert ev.main(["replay", "--no-judge"]) == 0
    assert ev.main(["baseline"]) == 0
    out = capsys.readouterr().out
    assert "unlabelled 2" in out
    assert "n/a" in out


def test_baseline_missing_file(tmp_path, dirs, capsys):
    assert ev.main(["baseline", str(tmp_path / "nope.csv")]) == 1
    assert "not found" in capsys.readouterr().err
```

- [ ] **Step 2: Run them.** `pytest tests/test_jev_eval.py -v` → the new tests FAIL (`baseline` unknown; `baseline_rows` missing).

- [ ] **Step 3: Implement.** Add `from collections import Counter, defaultdict` (replacing the `defaultdict` import). Add after `cmd_report`:

```python
BASELINE_FIELDS = [
    "id",
    "session_id",
    *(f"label_{k}" for k in triage.KEYS),
    "asked",
    "preflight",
    "corrected",
]
Labelled = tuple[dict, dict[str, int], Outcome]


def baseline_rows(rows: list[dict]) -> tuple[list[Labelled], Counter]:
    """Labelled rows matched to their transcript turn, and why others were skipped."""
    results: list[Labelled] = []
    skipped: Counter = Counter()
    cache: dict[str, list[Turn]] = {}
    for row in rows:
        labels = {k: parse_label(row.get(f"label_{k}", "")) for k in triage.KEYS}
        if any(v is None for v in labels.values()):
            skipped["unlabelled"] += 1
            continue
        session_id = str(row.get("session_id") or "")
        path = transcript_for(session_id)
        if path is None:
            skipped["no transcript"] += 1
            continue
        if session_id not in cache:
            cache[session_id] = turns(path)
        found = match([{"prompt": row.get("prompt")}], cache[session_id])
        if not found:
            skipped["not found"] += 1
            continue
        results.append((row, labels, found[0][1]))  # type: ignore[arg-type]
    return results, skipped


def baseline_stats(results: list[Labelled]) -> dict[str, tuple[int, int]]:
    """(k, n) per measure; the user's labels decide which prompts count."""
    feature = [o for _, lab, o in results if lab["new_feature"] and o.preflight is not None]
    ask = [o for _, lab, o in results if lab["underspecified"] or lab["key_decision"]]
    positive = [o for _, lab, o in results if any(lab.values())]
    other = [o for _, lab, o in results if not any(lab.values())]
    return {
        "preflight_miss": (sum(1 for o in feature if not o.preflight), len(feature)),
        "not_asked": (sum(1 for o in ask if not o.asked), len(ask)),
        "corrected_positive": (sum(1 for o in positive if o.corrected), len(positive)),
        "corrected_other": (sum(1 for o in other if o.corrected), len(other)),
    }


BASELINE_LABELS = {
    "preflight_miss": "pre-flight skipped (new feature, code edited)",
    "not_asked": "did not ask (underspecified or key decision)",
    "corrected_positive": "corrected or interrupted (any label = 1)",
    "corrected_other": "corrected or interrupted (all labels = 0)",
}


def cmd_baseline(args: argparse.Namespace) -> int:
    path = Path(args.labels) if args.labels else triage.jev_dir() / "labels.csv"
    if not path.is_file():
        print(f"{path} not found; run: jev-eval.py replay --no-judge", file=sys.stderr)
        return 1
    results, skipped = baseline_rows(read_labels(path))
    print(f"baseline (no jev): {len(results)} labelled prompts matched")
    for key, (k, n) in baseline_stats(results).items():
        print(f"  {BASELINE_LABELS[key]}: {k}/{n} ({fmt(ratio(k, n), True)})")
    print(
        "  skipped: "
        + ", ".join(f"{why} {skipped[why]}" for why in ("unlabelled", "no transcript", "not found"))
    )
    out = path.parent / "baseline.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=BASELINE_FIELDS)
        writer.writeheader()
        for row, labels, result in results:
            writer.writerow(
                {
                    "id": row.get("id"),
                    "session_id": row.get("session_id"),
                    **{f"label_{k}": labels[k] for k in triage.KEYS},
                    "asked": result.asked,
                    "preflight": "n/a" if result.preflight is None else result.preflight,
                    "corrected": result.corrected,
                }
            )
    print(f"per-prompt outcomes in {out}")
    return 0
```

In `main`, add before `args = parser.parse_args(argv)`:

```python
    baseline = sub.add_parser("baseline", help="no-jev baseline from your labels")
    baseline.add_argument("labels", nargs="?")
```

and add `"baseline": cmd_baseline` to the `handler` dict.

- [ ] **Step 4: Verify.** `pytest tests/test_jev_eval.py -v` → PASS; full `pytest`; ruff format and check (rewrap the long lines above).

- [ ] **Step 5: Commit.**

```bash
git add plugin/scripts/jev-eval.py tests/test_jev_eval.py
git commit -m "jev-eval: baseline subcommand measures the rules without jev

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Docs, statuses and the manual check

**Files:**
- Modify: `plugin/scripts/jev-eval.py` (module docstring)
- Modify: `README.md` ("Trying jev" code block)
- Modify: `knowledge/decisions/0012-jev-triage-pilot.md` (Consequences)
- Modify: the spec and this plan (Status → `implemented`)

- [ ] **Step 1: Docstring.** Replace the usage lines at the top of `jev-eval.py` with:

```
  replay [--n 60] [--seed 0] [--since YYYY-MM-DD] [--force] [--no-judge]
                                        sample past prompts into labels.csv
  replay --rescore                      fill jev scores into labels.csv
  score [labels.csv]                    precision/recall vs your labels; Replay gate
  baseline [labels.csv]                 no-jev baseline from your labels and history
  report [--since YYYY-MM-DD]           shadow vs active outcomes from the hook log
```

and change `replay needs typesafe-sdk and TYPESAFE_API_KEY` to `Only replay (without --no-judge) and --rescore call jev; they need typesafe-sdk and TYPESAFE_API_KEY`.

- [ ] **Step 2: README.** Replace the code block under `## Trying jev (opt-in pilot)` with:

````markdown
```
# no key needed
python plugin/scripts/jev-eval.py replay --no-judge --since 2026-08-01
#    fill label_* in ~/.claude/claude-kit/jev/labels.csv with 1/0
python plugin/scripts/jev-eval.py baseline   # how often the rules slip today
# with a key (https://console.typesafe.ai/keys)
python -m pip install "typesafe-sdk>=0.7"    # once, into the python hooks run
setx TYPESAFE_API_KEY <key>                  # restart Claude Code afterwards
python plugin/scripts/jev-eval.py replay --rescore
python plugin/scripts/jev-eval.py score      # Replay gate PASS/FAIL
setx CLAUDE_KIT_JEV shadow                   # log only, 1-2 weeks
setx CLAUDE_KIT_JEV active                   # add hints, 1-2 weeks
python plugin/scripts/jev-eval.py report --since 2026-10-01
setx CLAUDE_KIT_JEV off                      # stop
```
````

- [ ] **Step 3: ADR 0012.** Append to its `## Consequences` list:

```markdown
- Labelling and a no-jev baseline need no key (`replay --no-judge`, `baseline`;
  `docs/superpowers/specs/2026-09-28-jev-offline-baseline-design.md`). The
  active stage is still compared with shadow; the baseline is a reference.
```

- [ ] **Step 4: Statuses.** In the spec (currently `approved`) and in this plan (currently `draft`), change the first `- **Status:**` line of each (and only that line) to `- **Status:** implemented`. Run `python plugin/scripts/spec-index.py docs/superpowers`.

- [ ] **Step 5: Verify.** Full `pytest`, ruff. Grep the branch's changed files for the repo owner's username and email: none may appear.

- [ ] **Step 6: Manual check** (uses the real transcripts, no key; report row counts only, never prompt text):

```
python plugin/scripts/jev-eval.py replay --no-judge --n 60 --since 2026-08-01
python plugin/scripts/jev-eval.py baseline
```

Expected: the first prints `wrote N prompts` with N ≤ 60. The second prints `unlabelled N` with every measure `n/a`, and exits 0. If `labels.csv` already exists, stop and ask the user before passing `--force`: it may hold their labels.

- [ ] **Step 7: Commit.**

```bash
git add plugin/scripts/jev-eval.py README.md knowledge/decisions/0012-jev-triage-pilot.md docs/superpowers
git commit -m "Docs for jev offline labelling and baseline; mark implemented

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
