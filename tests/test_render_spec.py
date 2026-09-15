from helpers import PLUGIN, load_module, run_script

RENDERER = PLUGIN / "scripts" / "render-spec.py"


def render(md):
    return load_module(RENDERER, "render_spec").render(md)


def test_title_from_h1(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("# Hello Spec\n\nbody\n", encoding="utf-8")
    render(md)
    assert "<title>Hello Spec</title>" in (tmp_path / "x.html").read_text("utf-8")


def test_title_falls_back_to_filename(tmp_path):
    md = tmp_path / "fallback.md"
    md.write_text("no heading here\n", encoding="utf-8")
    render(md)
    assert "<title>fallback</title>" in (tmp_path / "fallback.html").read_text("utf-8")


def test_html_written_next_to_md(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("# T\n", encoding="utf-8")
    out = render(md)
    assert out == md.with_suffix(".html")
    assert out.exists()


def test_arabic_survives_and_bidi_rule_present(tmp_path):
    md = tmp_path / "ar.md"
    md.write_text("# عنوان\n\nهذا نص عربي.\n\n- بند\n", encoding="utf-8")
    html = render(md).read_text("utf-8")
    assert "unicode-bidi: plaintext" in html
    assert "هذا نص عربي." in html


def test_cli_renders_given_file(tmp_path):
    md = tmp_path / "cli.md"
    md.write_text("# CLI\n", encoding="utf-8")
    result = run_script(RENDERER, str(md), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "cli.html").exists()


def test_cli_with_nothing_to_render_exits_1(tmp_path):
    result = run_script(RENDERER, cwd=tmp_path)
    assert result.returncode == 1
    assert "No Markdown files" in result.stdout


def test_module_exposes_main():
    mod = load_module(RENDERER, "render_spec_main")
    assert callable(mod.main)
