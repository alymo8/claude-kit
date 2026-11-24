import json
import re

from helpers import PLUGIN, REPO, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "agent-skills.py"
WRAPPERS = PLUGIN / "agent-skills"
NAME_RE = re.compile(r"^[a-z0-9-]+$")
MACHINE_RE = re.compile(r"[A-Za-z]:[\\/]|/home/|/Users/")
mod = load_module(SCRIPT, "agent_skills")


def front(path):
    head = path.read_text(encoding="utf-8").split("---", 2)[1]
    pairs = (line.split(":", 1) for line in head.strip().splitlines())
    return {k.strip(): v.strip() for k, v in pairs}


def test_check_passes_on_committed_wrappers():
    result = run_script(SCRIPT, "--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_one_wrapper_per_command_except_claude_only():
    commands = {p.stem for p in (PLUGIN / "commands").glob("*.md")}
    wrappers = {p.name for p in WRAPPERS.iterdir() if p.is_dir()}
    assert wrappers == commands - {"ship-many", "statusline"}


def test_wrapper_frontmatter_and_body():
    for folder in WRAPPERS.iterdir():
        skill = folder / "SKILL.md"
        meta = front(skill)
        assert meta["name"] == folder.name
        assert meta["disable-model-invocation"] == "true"
        command = PLUGIN / "commands" / f"{folder.name}.md"
        assert json.loads(meta["description"]) == front(command)["description"]
        text = skill.read_text(encoding="utf-8")
        assert f"`<plugin>/commands/{folder.name}.md`" in text
        assert not MACHINE_RE.search(text), folder.name


def test_check_accepts_crlf_working_copy(tmp_path):
    out = tmp_path / "out"
    assert mod.main(["--out", str(out)]) == 0
    skill = out / "ship" / "SKILL.md"
    skill.write_bytes(skill.read_bytes().replace(b"\n", b"\r\n"))
    assert mod.main(["--check", "--out", str(out)]) == 0


def test_check_fails_then_write_fixes(tmp_path):
    out = tmp_path / "out"
    (out / "stale").mkdir(parents=True)
    assert mod.main(["--check", "--out", str(out)]) == 1
    assert mod.main(["--out", str(out)]) == 0
    assert not (out / "stale").exists()
    assert mod.main(["--check", "--out", str(out)]) == 0


def test_every_linked_folder_has_a_valid_name():
    roots = [
        PLUGIN / "skills",
        WRAPPERS,
        REPO / "vendor" / "superpowers" / "skills",
    ]
    folders = [p for root in roots for p in root.iterdir() if p.is_dir()]
    assert len(folders) > 30
    for folder in folders:
        name = front(folder / "SKILL.md")["name"]
        assert name == folder.name and NAME_RE.match(name), folder
