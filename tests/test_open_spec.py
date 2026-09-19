import os
import time

from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "open-spec.py"


def make_repo(tmp_path):
    specs = tmp_path / "docs" / "superpowers" / "specs"
    plans = tmp_path / "docs" / "superpowers" / "plans"
    specs.mkdir(parents=True)
    plans.mkdir(parents=True)
    return specs, plans


def test_explicit_path_is_rendered_and_returned(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# A\n", encoding="utf-8")
    result = run_script(SCRIPT, "--no-open", str(md), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    html = md.with_suffix(".html")
    assert html.exists()
    assert str(html) in result.stdout


def test_html_path_is_mapped_back_to_markdown(tmp_path):
    md = tmp_path / "b.md"
    md.write_text("# B\n", encoding="utf-8")
    result = run_script(SCRIPT, "--no-open", str(md.with_suffix(".html")), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert md.with_suffix(".html").exists()


def test_no_argument_picks_most_recent_spec_or_plan(tmp_path):
    specs, plans = make_repo(tmp_path)
    old = specs / "2026-01-01-old.md"
    old.write_text("# Old\n", encoding="utf-8")
    newest = plans / "2026-02-02-new.md"
    newest.write_text("# New\n", encoding="utf-8")
    now = time.time()
    os.utime(old, (now - 100, now - 100))
    os.utime(newest, (now, now))
    result = run_script(SCRIPT, "--no-open", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert newest.with_suffix(".html").exists()
    assert not old.with_suffix(".html").exists()


def test_no_spec_found_fails_with_message(tmp_path):
    result = run_script(SCRIPT, "--no-open", cwd=tmp_path)
    assert result.returncode == 1
    assert "no spec" in (result.stdout + result.stderr).lower()


def test_open_uses_platform_opener(tmp_path, monkeypatch):
    mod = load_module(SCRIPT, "open_spec")
    opened = []
    monkeypatch.setattr(mod, "_launch", lambda p: opened.append(p))
    md = tmp_path / "c.md"
    md.write_text("# C\n", encoding="utf-8")
    assert mod.main([str(md)]) == 0
    assert opened == [md.with_suffix(".html")]
