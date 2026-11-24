"""Anthropic's plugin-directory pre-submission checklist, as tests.

The checks run on the tracked tree (`git ls-files plugin`), because the
directory only sees what is pushed: untracked files such as `__pycache__/`
do not count.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest
from helpers import PLUGIN, REPO

MAX_BYTES = 5 * 1024 * 1024
MAX_FILES = 512
LFS_HEAD = b"version https://git-lfs.github.com/spec/v1"
RESERVED = ("claude", "anthropic", "official", "plugin", "mcp", "test")
BANNED_NAMES = {".DS_Store", "Thumbs.db"}
BANNED_MODES = {"120000": "symlink", "160000": "submodule"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
COMMAND_RE = re.compile(
    r'^python3? "\$\{CLAUDE_PLUGIN_ROOT\}/(hooks|scripts)/[a-z_-]+\.py"'
    r"( --[a-z-]+( [A-Za-z]+)?)*$"
)


def tracked(root: Path) -> list[tuple[str, str]]:
    """(mode, path) of each tracked entry under plugin/ that exists on disk."""
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-s", "-z", "plugin"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    entries = []
    for line in filter(None, out.split("\0")):
        meta, _, path = line.partition("\t")
        mode = meta.split()[0]
        if (root / path).exists() or (root / path).is_symlink():
            entries.append((mode, path))
    return entries


def entry_problems(entries: list[tuple[str, str]]) -> list[str]:
    problems = []
    for mode, path in entries:
        if mode in BANNED_MODES:
            problems.append(f"{path}: {BANNED_MODES[mode]} (mode {mode})")
        if path.rsplit("/", 1)[-1] in BANNED_NAMES:
            problems.append(f"{path}: banned file name")
    return problems


def size_problems(sizes: dict[str, int]) -> list[str]:
    problems = [
        f"{path}: {size} bytes, limit is under {MAX_BYTES}"
        for path, size in sizes.items()
        if size >= MAX_BYTES
    ]
    if len(sizes) > MAX_FILES:
        problems.append(f"{len(sizes)} files, limit is {MAX_FILES}")
    return problems


def lfs_problems(heads: dict[str, bytes]) -> list[str]:
    return [
        f"{path}: LFS pointer" for path, h in heads.items() if h.startswith(LFS_HEAD)
    ]


def readme_problems(text: str, scripts: list[str]) -> list[str]:
    problems = []
    words = len(text.split())
    if words < 40:
        problems.append(f"README has {words} words, needs at least 40")
    problems += [f"README does not name {s}" for s in scripts if s not in text]
    return problems


def manifest_problems(data: dict) -> list[str]:
    problems = [
        f"plugin.json lacks {key}"
        for key in ("license", "description", "author", "version")
        if not data.get(key)
    ]
    homepage = data.get("homepage")
    if homepage is not None:
        url = urlparse(str(homepage))
        if url.scheme != "https" or not url.netloc:
            problems.append(f"homepage {homepage!r} is not an https URL with a host")
    else:
        problems.append("plugin.json lacks homepage")
    name = str(data.get("name", ""))
    if not NAME_RE.match(name):
        problems.append(f"name {name!r} is not kebab-case")
    problems += [f"name {name!r} contains {w!r}" for w in RESERVED if w in name]
    if "hooks" in data:
        problems.append("plugin.json lists hooks; hooks/hooks.json is loaded already")
    return problems


def hook_commands() -> list[str]:
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return [
        h["command"]
        for groups in hooks["hooks"].values()
        for group in groups
        for h in group["hooks"]
    ]


def manifest() -> dict:
    path = PLUGIN / ".claude-plugin" / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_real_tree_is_clean():
    entries = tracked(REPO)
    assert entries
    files = [p for _, p in entries if (REPO / p).is_file()]
    sizes = {p: (REPO / p).stat().st_size for p in files}
    heads = {p: (REPO / p).read_bytes()[:64] for p in files}
    commands = hook_commands()
    scripts = sorted({s for c in commands for s in re.findall(r"[\w-]+\.py", c)})
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8")
    assert entry_problems(entries) == []
    assert size_problems(sizes) == []
    assert lfs_problems(heads) == []
    assert readme_problems(readme, scripts) == []
    assert manifest_problems(manifest()) == []
    for command in commands:
        assert COMMAND_RE.fullmatch(command), command


@pytest.mark.parametrize(
    ("entry", "count"),
    [
        (("120000", "plugin/x"), 1),
        (("160000", "plugin/sub"), 1),
        (("100644", "plugin/a/.DS_Store"), 1),
        (("100644", "plugin/Thumbs.db"), 1),
        (("100644", "plugin/ok.py"), 0),
    ],
)
def test_entry_problems_fail(entry, count):
    assert len(entry_problems([entry])) == count


def test_size_problems_fail():
    assert size_problems({"plugin/big": MAX_BYTES})
    assert size_problems({"plugin/ok": MAX_BYTES - 1}) == []
    assert size_problems({f"plugin/f{i}": 1 for i in range(513)})


def test_lfs_problems_fail():
    pointer = b"version https://git-lfs.github.com/spec/v1\noid sha256:..."
    assert lfs_problems({"plugin/big.bin": pointer})
    assert lfs_problems({"plugin/ok.py": b"print(1)\n"}) == []


def test_readme_problems_fail():
    scripts = ["a.py", "b.py"]
    assert readme_problems(" ".join(["a.py", "b.py"] + ["word"] * 37), scripts)
    assert readme_problems(" ".join(["a.py"] + ["word"] * 39), scripts)
    assert readme_problems(" ".join(["a.py", "b.py"] + ["word"] * 38), scripts) == []


def _without(key):
    def change(data):
        del data[key]

    return change


def _set(key, value):
    def change(data):
        data[key] = value

    return change


@pytest.mark.parametrize(
    "change",
    [
        _without("license"),
        _without("description"),
        _without("author"),
        _without("version"),
        _set("homepage", "not a url"),
        _set("homepage", "http://"),
        _set("name", "Agent_Kit"),
        _set("name", "agent-plugin"),
        _set("name", "claude-tools"),
        _set("hooks", "./hooks/hooks.json"),
    ],
)
def test_manifest_problems_fail(change):
    data = copy.deepcopy(manifest())
    change(data)
    assert manifest_problems(data)


@pytest.mark.parametrize(
    "command",
    [
        'python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py" '
        '"${CLAUDE_PROJECT_DIR}/docs/superpowers"',
        'python3 -c "print(1)"',
        'python "${CLAUDE_PLUGIN_ROOT}/hooks/*.py"',
        'python "$HOME/hooks/x.py"',
    ],
)
def test_command_pattern_rejects(command):
    assert not COMMAND_RE.fullmatch(command)


def test_checklist_reads_tracked_files_only(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True)

    git("init", "-q")
    (tmp_path / "plugin").mkdir()
    (tmp_path / "plugin" / "ok.py").write_text("print(1)\n", encoding="utf-8")
    git("add", "plugin/ok.py")
    git(
        "-c",
        "user.name=t",
        "-c",
        "user.email=t",
        "commit",
        "-q",
        "-m",
        "init",
    )
    (tmp_path / "plugin" / ".DS_Store").write_bytes(b"\0")
    entries = tracked(tmp_path)
    assert entries == [("100644", "plugin/ok.py")]
    assert entry_problems(entries) == []
