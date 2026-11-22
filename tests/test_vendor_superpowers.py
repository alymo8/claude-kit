import json
import subprocess

from helpers import PLUGIN, REPO, load_module

VENDOR = REPO / "vendor" / "superpowers"
mod = load_module(PLUGIN / "scripts" / "vendor-superpowers.py", "vendor_sp")


def names(folder):
    if not folder.is_dir():
        return set()
    return {p.name for p in folder.iterdir() if (p / "SKILL.md").is_file()}


def test_bundle_holds_the_closure():
    start = mod.kit_references(REPO)
    assert {"brainstorming", "writing-plans", "systematic-debugging"} <= start
    want = mod.closure(start, VENDOR / "skills")
    assert names(VENDOR / "skills") == want
    assert "writing-skills" in want


def test_license_and_version():
    assert "MIT License" in (VENDOR / "LICENSE").read_text(encoding="utf-8")
    version = (VENDOR / "VERSION").read_text(encoding="utf-8")
    assert version.startswith("version: ")
    assert "source: " in version


def test_no_name_collision_with_kit_skills_or_wrappers():
    kit = names(PLUGIN / "skills") | names(PLUGIN / "agent-skills")
    assert not names(VENDOR / "skills") & kit


def test_bundle_is_outside_plugin_skills():
    assert PLUGIN not in VENDOR.resolve().parents


def test_shebang_scripts_are_executable_in_git():
    listed = subprocess.run(
        ["git", "ls-files", "-s", "vendor/superpowers"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    scripts = 0
    for line in listed:
        mode, rest = line.split(" ", 1)
        path = REPO / rest.split("\t", 1)[1]
        if path.read_bytes().startswith(b"#!"):
            scripts += 1
            assert mode == "100755", path
    assert scripts > 0


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_kit_references_scan_set(tmp_path):
    write(tmp_path / "plugin" / "a" / "x.md", "superpowers:aaa")
    write(tmp_path / "docs" / "y.md", "superpowers:bbb")
    write(tmp_path / "AGENTS.md", "superpowers:ccc")
    write(tmp_path / "conventions" / "z.md", "superpowers:ddd")
    assert mod.kit_references(tmp_path) == {"aaa", "ccc", "ddd"}


def upstream(tmp_path):
    up = tmp_path / "up"
    write(up / "skills" / "a" / "SKILL.md", "use superpowers:b")
    write(up / "skills" / "b" / "SKILL.md", "b")
    write(up / "skills" / "c" / "SKILL.md", "c")
    write(up / "LICENSE", "MIT License\n")
    write(up / "package.json", json.dumps({"version": "9.9.9"}))
    return up


def test_script_copies_the_closure(tmp_path):
    repo = tmp_path / "repo"
    write(repo / "plugin" / "x.md", "superpowers:a")
    args = ["--from", str(upstream(tmp_path)), "--repo", str(repo)]
    assert mod.main(args) == 0
    bundle = repo / "vendor" / "superpowers"
    assert names(bundle / "skills") == {"a", "b"}
    assert "version: 9.9.9" in (bundle / "VERSION").read_text(encoding="utf-8")
    assert (bundle / "LICENSE").is_file()


def test_script_fails_on_unknown_skill(tmp_path):
    repo = tmp_path / "repo"
    write(repo / "plugin" / "x.md", "superpowers:nope")
    args = ["--from", str(upstream(tmp_path)), "--repo", str(repo)]
    assert mod.main(args) == 1
    assert not (repo / "vendor").exists()
