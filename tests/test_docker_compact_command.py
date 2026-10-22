"""Structure tests for the /docker-compact command."""

from __future__ import annotations

from helpers import PLUGIN

TEXT = (PLUGIN / "commands" / "docker-compact.md").read_text(encoding="utf-8")
FLAT = " ".join(TEXT.split())


def test_frontmatter_user_only():
    front = TEXT.split("---", 2)[1]
    assert TEXT.startswith("---\n") and "description:" in front
    assert "disable-model-invocation: true" in front


def test_runs_status_script_and_path_flag():
    assert '"${CLAUDE_PLUGIN_ROOT}/scripts/docker-disk.py"' in TEXT
    assert "~/.claude/skills/claude-kit/scripts/docker-disk.py" in TEXT
    assert "--path" in TEXT and "skipped" in TEXT


def test_asks_before_stopping_docker():
    ask = FLAT.index("Ask the user before anything else")
    assert ask < FLAT.index("fstrim") < FLAT.index("wsl --shutdown")
    assert "UAC" in FLAT and "clear yes" in FLAT


def test_steps_and_diskpart_script():
    for needle in (
        "fstrim -v /mnt/docker-desktop-disk",
        "wsl --shutdown",
        "wsl --manage docker-desktop --set-sparse true",
        r"%TEMP%\dcompact",
        'select vdisk file="',
        "attach vdisk readonly",
        "compact vdisk",
        "detach vdisk",
        "-Encoding ascii",
        "-Verb RunAs",
        "-Wait",
        "-PassThru",
        "ExitCode",
    ):
        assert needle in FLAT, needle


def test_temp_folder_deleted_and_no_prune():
    assert "Remove-Item" in FLAT
    assert "whether or not diskpart succeeded" in FLAT
    assert "prune" not in TEXT.lower()


def test_diskpart_argument_list_is_one_quoted_string():
    assert r'-ArgumentList "/s `"$env:TEMP\dcompact\compact.txt`""' in FLAT


def test_non_ascii_check_precedes_the_ask():
    check = FLAT.index("outside ASCII")
    assert check < FLAT.index("Ask the user before anything else")
    assert check < FLAT.index("wsl --shutdown")
    assert check < FLAT.index("Set-Content")
    assert "run diskpart by hand" in FLAT
