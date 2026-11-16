#!/usr/bin/env python3
"""Install claude-kit as a Claude Code skills-dir plugin, on any OS.

Usage: install.py [--skills-dir DIR] [--settings FILE] [--python CMD]

Links <skills-dir>/claude-kit to this plugin folder (a junction on Windows, a
symlink elsewhere), so Claude Code loads the kit from the git checkout
(ADR 0005, amended by ADR 0033). First checks that the command the hooks run
(default "python") is Python 3.11+, and exits 1 with nothing changed if not.
Warns when git, gh or the superpowers plugin is missing. Adds the kit's status
line when none is configured. Idempotent; refuses to overwrite anything else
at the link path.

Keep this file parseable by Python 3.8, so an old interpreter still reaches
the version error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent
MIN_VERSION = (3, 11)
SUPERPOWERS = "superpowers@claude-plugins-official"
OS_NAMES = {"win32": "Windows", "darwin": "macOS", "linux": "Linux"}
# Where Homebrew keeps the unversioned python -> python3 links (Apple silicon,
# then Intel).
BREW_LIBEXEC = [
    Path("/opt/homebrew/opt/python@3/libexec/bin"),
    Path("/usr/local/opt/python@3/libexec/bin"),
]


def os_name(platform: str) -> str:
    """Readable OS name for a sys.platform value ('linux' covers 'linux2')."""
    key = "linux" if platform.startswith("linux") else platform
    return OS_NAMES.get(key, platform)


def fix_for(platform: str, command: str, libexec_dirs: list[Path] | None = None) -> str:
    """How to make `command` a Python 3.11+ on this OS. Shell aliases are never
    suggested: hooks run in a non-interactive shell, which ignores them."""
    name = os_name(platform)
    if name == "Windows":
        return (
            'install Python 3.11+ from python.org with "Add python.exe to PATH" ticked.'
        )
    if name == "macOS":
        dirs = BREW_LIBEXEC if libexec_dirs is None else libexec_dirs
        found = next((d for d in dirs if (d / command).exists()), None)
        if found is not None:
            return (
                f"Homebrew's {command} is in {found}. Put it on PATH, then open a "
                "new terminal and restart the Claude app:\n"
                f"  echo 'export PATH=\"{found}:$PATH\"' >> ~/.zprofile"
            )
        return (
            "run `brew install python@3`, then add "
            '"$(brew --prefix)/opt/python@3/libexec/bin" to PATH in ~/.zprofile '
            "and restart the Claude app."
        )
    return (
        "install the python-is-python3 package, or link python to python3 on your PATH."
    )


def python_version(command: str) -> tuple[int, int] | None:
    """(major, minor) of the given python command, or None if it cannot run."""
    if shutil.which(command) is None:
        return None
    try:
        done = subprocess.run(
            [command, "-c", "import sys; print(*sys.version_info[:2])"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = done.stdout.split()
    if done.returncode != 0 or len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def check_python(command: str) -> bool:
    version = python_version(command)
    if version is not None and version >= MIN_VERSION:
        return True
    if version is None:
        problem = "is not on PATH"
    else:
        problem = f"is {version[0]}.{version[1]}"
    print(f'ERROR: hooks run "{command}", which {problem}.')
    print(f"Fix: {fix_for(sys.platform, command)}")
    return False


def warn_missing_tools() -> None:
    for tool in ("git", "gh"):
        if shutil.which(tool) is None:
            print(
                f"WARNING: {tool} not found on PATH; "
                "/ship and the worktree flow need it."
            )


def is_link(path: Path) -> bool:
    """True for a symlink or a Windows junction, dangling or not."""
    try:
        os.readlink(path)
    except (OSError, ValueError):
        return False
    return True


def points_at_plugin(link: Path) -> bool:
    try:
        return os.path.samefile(link, PLUGIN)
    except OSError:
        return False


def make_link(link: Path) -> None:
    if sys.platform == "win32":
        shell = os.environ.get("COMSPEC", "cmd")
        done = subprocess.run(
            [shell, "/c", "mklink", "/J", str(link), str(PLUGIN)],
            capture_output=True,
            text=True,
        )
        if done.returncode != 0:
            raise OSError((done.stdout + done.stderr).strip())
    else:
        os.symlink(PLUGIN, link, target_is_directory=True)


def install_link(skills_dir: Path) -> str | None:
    """'installed' or 'present'; None after printing an error."""
    link = skills_dir / "claude-kit"
    if os.path.lexists(link):
        if is_link(link) and points_at_plugin(link):
            print(f"claude-kit already installed: {link} -> {PLUGIN}")
            return "present"
        print(
            f"ERROR: {link} already exists and is not a link to {PLUGIN}. "
            "Remove it first."
        )
        return None
    skills_dir.mkdir(parents=True, exist_ok=True)
    make_link(link)
    print(f"Installed: {link} -> {PLUGIN}")
    return "installed"


def install_statusline(settings: Path, skills_dir: Path) -> None:
    script = PLUGIN / "scripts" / "install-statusline.py"
    command = [sys.executable, str(script), "--settings", str(settings)]
    command += ["--skills-dir", str(skills_dir)]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"WARNING: could not run install-statusline.py: {exc}")
        return
    if done.stdout.strip():
        print(done.stdout.strip())
    if done.returncode != 0:
        if done.stderr.strip():
            print(done.stderr.strip())
        print(
            "WARNING: status line not configured (install-statusline.py "
            f"exited {done.returncode}); see the message above."
        )


def superpowers_enabled(settings: Path) -> bool:
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    plugins = data.get("enabledPlugins") if isinstance(data, dict) else None
    return isinstance(plugins, dict) and plugins.get(SUPERPOWERS) is True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    home = Path.home() / ".claude"
    parser.add_argument("--skills-dir", default=str(home / "skills"))
    parser.add_argument("--settings", default=str(home / "settings.json"))
    parser.add_argument("--python", default="python", help="the command the hooks run")
    args = parser.parse_args(argv)
    print(f"Detected: {os_name(sys.platform)}")
    if not check_python(args.python):
        return 1
    warn_missing_tools()
    skills_dir, settings = Path(args.skills_dir), Path(args.settings)
    try:
        outcome = install_link(skills_dir)
    except OSError as exc:
        print(f"ERROR: could not create the link: {exc}")
        return 1
    if outcome is None:
        return 1
    install_statusline(settings, skills_dir)
    if not superpowers_enabled(settings):
        print(
            "WARNING: the superpowers plugin is not enabled. The kit's flow "
            f"uses its skills. In Claude Code run: /plugin install {SUPERPOWERS}"
        )
    if outcome == "installed":
        print(
            "Start a new Claude Code session (or run /reload-plugins) to load the kit."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
