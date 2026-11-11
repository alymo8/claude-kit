"""Tests for plugin/scripts/vault-pending.py."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from helpers import PLUGIN, REPO, run_script

SCRIPT = PLUGIN / "scripts" / "vault-pending.py"
FIXTURES = REPO / "tests" / "fixtures" / "vault"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_vault(root: Path) -> Path:
    (root / "raw").mkdir(parents=True)
    (root / "wiki" / "sources").mkdir(parents=True)
    (root / "vault.toml").write_text('profile = "personal"\n', encoding="utf-8")
    return root


def raw(vault: Path, rel: str, data: bytes = b"hello") -> str:
    path = vault / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def source(
    vault: Path, name: str, rel: str, sha: str, nl: str = "\n", bom: bool = False
) -> None:
    text = nl.join(
        [
            "---",
            "type: source",
            f"raw: {rel}",
            f"sha256: {sha}",
            "---",
            "## Summary",
            "",
        ]
    )
    data = ("﻿" if bom else "") + text
    (vault / "wiki" / "sources" / name).write_bytes(data.encode("utf-8"))


def run(vault: Path, *args: str):
    return run_script(SCRIPT, str(vault), *args)


def test_new_changed_uptodate_missing(tmp_path):
    v = make_vault(tmp_path)
    raw(v, "raw/web/a-new.md")
    old = raw(v, "raw/docs/b-changed.md", b"v1")
    raw(v, "raw/docs/b-changed.md", b"v2")
    source(v, "2026-11-01-b.md", "raw/docs/b-changed.md", old)
    same = raw(v, "raw/notes/c-same.txt")
    source(v, "2026-11-01-c.md", "raw/notes/c-same.txt", same)
    source(v, "2026-11-01-d.md", "raw/web/d-gone.md", same)
    result = run(v)
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "changed\traw/docs/b-changed.md",
        "new\traw/web/a-new.md",
        "missing\traw/web/d-gone.md",
    ]


def test_json_shape(tmp_path):
    v = make_vault(tmp_path)
    raw(v, "raw/web/a.md")
    old = raw(v, "raw/docs/b.md", b"v1")
    raw(v, "raw/docs/b.md", b"v2")
    source(v, "2026-11-01-b.md", "raw/docs/b.md", old)
    source(v, "2026-11-01-c.md", "raw/web/c-gone.md", old)
    data = json.loads(run(v, "--json").stdout)
    assert data == [
        {
            "path": "raw/docs/b.md",
            "status": "changed",
            "source": "wiki/sources/2026-11-01-b.md",
            "sha256": hashlib.sha256(b"v2").hexdigest(),
        },
        {
            "path": "raw/web/a.md",
            "status": "new",
            "source": None,
            "sha256": hashlib.sha256(b"hello").hexdigest(),
        },
        {
            "path": "raw/web/c-gone.md",
            "status": "missing",
            "source": "wiki/sources/2026-11-01-c.md",
            "sha256": None,
        },
    ]


def test_nothing_pending_prints_nothing(tmp_path):
    v = make_vault(tmp_path)
    sha = raw(v, "raw/web/a.md")
    source(v, "2026-11-01-a.md", "raw/web/a.md", sha)
    result = run(v)
    assert (result.returncode, result.stdout) == (0, "")
    assert json.loads(run(v, "--json").stdout) == []


def test_gitkeep_dotfiles_and_dotdirs_skipped_nested_listed(tmp_path):
    v = make_vault(tmp_path)
    raw(v, "raw/web/.gitkeep", b"")
    raw(v, "raw/.DS_Store")
    raw(v, "raw/.obsidian/x.json")
    raw(v, "raw/web/2026/page.md")
    assert run(v).stdout.splitlines() == ["new\traw/web/2026/page.md"]


def test_crlf_bom_quotes_and_uppercase_sha_match(tmp_path):
    v = make_vault(tmp_path)
    sha = raw(v, "raw/web/a.md")
    source(v, "2026-11-01-a.md", "raw/web/a.md", sha, nl="\r\n", bom=True)
    sha_b = raw(v, "raw/web/b.md", b"other")
    source(v, "2026-11-01-b.md", '"raw/web/b.md"', f'"{sha_b.upper()}"')
    sha_c = raw(v, "raw/web/c.md", b"third")
    source(v, "2026-11-01-c.md", "./raw\\web\\c.md", sha_c)
    assert run(v).stdout == ""


def test_extract_is_exclusive_with_vault_and_json(tmp_path):
    v = make_vault(tmp_path)
    doc = tmp_path / "t.docx"
    assert run_script(SCRIPT, str(v), "--extract", str(doc)).returncode == 2
    assert run_script(SCRIPT, "--json", "--extract", str(doc)).returncode == 2
    assert run_script(SCRIPT).returncode == 2


def test_no_vault_toml_exits_2(tmp_path):
    result = run(tmp_path)
    assert result.returncode == 2
    assert result.stderr


def test_unparsable_vault_toml_exits_2(tmp_path):
    v = make_vault(tmp_path)
    (v / "vault.toml").write_text("profile = \n", encoding="utf-8")
    assert run(v).returncode == 2


def test_extract_docx_paragraphs_in_order(tmp_path):
    doc = tmp_path / "t.docx"
    xml = (
        f'<w:document xmlns:w="{W}"><w:body>'
        "<w:p><w:r><w:t>Mara Quint: </w:t></w:r><w:r><w:t>hello</w:t></w:r></w:p>"
        "<w:p></w:p>"
        "<w:p><w:r><w:t>Second line</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(doc, "w") as z:
        z.writestr("word/document.xml", xml)
    result = run_script(SCRIPT, "--extract", str(doc))
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["Mara Quint: hello", "Second line"]


def test_extract_rejects_non_docx(tmp_path):
    fake = tmp_path / "fake.docx"
    fake.write_text("not a zip", encoding="utf-8")
    result = run_script(SCRIPT, "--extract", str(fake))
    assert result.returncode == 1
    assert result.stderr
    empty_zip = tmp_path / "empty.docx"
    with zipfile.ZipFile(empty_zip, "w") as z:
        z.writestr("other.txt", "x")
    assert run_script(SCRIPT, "--extract", str(empty_zip)).returncode == 1


def test_fixtures_are_listed_new_and_declare_fictional_names(tmp_path):
    v = make_vault(tmp_path)
    shutil.copytree(
        FIXTURES,
        v / "raw",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("EXPECTED.md"),
    )
    data = json.loads(run(v, "--json").stdout)
    samples = [
        "docs/atlas-brief.md",
        "transcripts/2026-11-03-atlas-sync.vtt",
        "web/atlas-launch-notes.md",
    ]
    assert [d["path"] for d in data] == [f"raw/{s}" for s in samples]
    assert {d["status"] for d in data} == {"new"}
    for path in FIXTURES.rglob("*.*"):
        head = path.read_text("utf-8")[:600].lower()
        assert "fictional" in head, path
    expected = (FIXTURES / "EXPECTED.md").read_text("utf-8")
    for sample in samples:
        assert f"`{sample}`" in expected, sample
