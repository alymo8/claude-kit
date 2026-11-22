#!/usr/bin/env python3
"""Install claude-kit as a Claude Code skills-dir plugin, on any OS.

Usage: install.py [--agent {claude,vibe,codex,cursor}] [--home DIR]
                  [--skills-dir DIR] [--settings FILE] [--python CMD]

Links <skills-dir>/claude-kit to this plugin folder (a junction on Windows, a
symlink elsewhere), so Claude Code loads the kit from the git checkout
(ADR 0005, amended by ADR 0033). First checks that the command the hooks run
(default "python") is Python 3.11+, and exits 1 with nothing changed if not.
Warns when git, gh or the superpowers plugin is missing. Adds the kit's status
line when none is configured. Idempotent; refuses to overwrite anything else
at the link path.

With --agent vibe, codex or cursor it instead links every kit skill folder
(plugin/skills, plugin/agent-skills, vendor/superpowers/skills) into
<home>/.agents/skills and merges plugin/hooks/run.py into the agent's user
hook file (for Vibe and Codex also a fallback line into its AGENTS.md).

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
KIT = PLUGIN.parent
RUNNER = PLUGIN / "hooks" / "run.py"
AGENTS = ("claude", "vibe", "codex", "cursor")
TOML_BEGIN = "# >>> claude-kit hooks (managed by plugin/install.py) >>>"
TOML_END = "# <<< claude-kit hooks <<<"
MD_BEGIN = "<!-- claude-kit:begin (managed by plugin/install.py) -->"
MD_END = "<!-- claude-kit:end -->"
NEXT_STEP = {
    "vibe": "Next: start a new Vibe session.",
    "codex": "Next: in Codex, run /hooks and trust the claude-kit hooks.",
    "cursor": (
        "Next: start a new Cursor agent chat. If the kit map does not reach the "
        "model, paste this into Cursor's user rules:"
    ),
}
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


def make_link(link: Path, target: Path = PLUGIN) -> None:
    if sys.platform == "win32":
        shell = os.environ.get("COMSPEC", "cmd")
        done = subprocess.run(
            [shell, "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if done.returncode != 0:
            raise OSError((done.stdout + done.stderr).strip())
    else:
        os.symlink(target, link, target_is_directory=True)


def remove_link(link: Path) -> None:
    """Remove the link itself, never what it points at."""
    if sys.platform == "win32":
        os.rmdir(link)
    else:
        os.unlink(link)


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


def skill_roots(kit: Path = KIT) -> list[Path]:
    plugin = kit / "plugin"
    vendor = kit / "vendor" / "superpowers" / "skills"
    return [plugin / "skills", plugin / "agent-skills", vendor]


def skill_sources(kit: Path = KIT) -> list[Path]:
    """Every folder holding a SKILL.md under the three kit roots."""
    found = []
    for root in skill_roots(kit):
        if root.is_dir():
            found += sorted(d for d in root.iterdir() if (d / "SKILL.md").is_file())
    return found


def hook_command(python: str, agent: str, event: str) -> str:
    exe = f'"{python}"' if " " in python else python
    return f'{exe} "{RUNNER.as_posix()}" --agent {agent} --event {event}'


def fallback_line(python: str, agent: str) -> str:
    command = hook_command(python, agent, "SessionStart")
    return (
        'If your context has no "Kit map (claude-kit)" text, run '
        f"`{command}` and follow what it prints."
    )


def link_target(link: Path) -> str | None:
    """The link's target ('\\\\?\\' stripped), or None if it is not a link."""
    try:
        target = os.readlink(link)
    except (OSError, ValueError):
        return None
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return target


def under_kit_roots(target: str) -> bool:
    norm = os.path.normcase(os.path.abspath(target))
    for root in skill_roots():
        if norm.startswith(os.path.normcase(str(root)) + os.sep):
            return True
    return False


def same_dir(link: Path, folder: Path) -> bool:
    try:
        return os.path.samefile(link, folder)
    except OSError:
        return False


def link_skills(skills_dir: Path, sources: list[Path]) -> None:
    skills_dir.mkdir(parents=True, exist_ok=True)
    for folder in sources:
        name = folder.name
        link = skills_dir / name
        if not os.path.lexists(link):
            make_link(link, folder)
            print(f"Linked {name}")
            continue
        target = link_target(link)
        if target is not None and same_dir(link, folder):
            continue
        if target is not None and under_kit_roots(target):
            remove_link(link)
            make_link(link, folder)
            print(f"Relinked {name}")
            continue
        print(f"Skipped {name}: {link} exists and is not this kit's link")
    for link in sorted(skills_dir.iterdir()):
        target = link_target(link)
        if target is None or os.path.exists(link) or not under_kit_roots(target):
            continue
        remove_link(link)
        print(f"Removed {link.name} (dangling)")


def replace_block(text: str, begin: str, end: str, lines: list[str]) -> str:
    """text without its managed block, then a fresh block at the end."""
    start = text.find(begin)
    stop = text.find(end, start) if start >= 0 else -1
    if stop >= 0:
        stop += len(end)
        if text[stop : stop + 1] == "\n":
            stop += 1
        text = text[:start] + text[stop:]
    rest = text.rstrip("\n")
    block = "\n".join([begin, *lines, end]) + "\n"
    return f"{rest}\n\n{block}" if rest else block


def vibe_hooks(text: str, python: str) -> str:
    start = hook_command(python, "vibe", "SessionStart")
    stop = hook_command(python, "vibe", "Stop")
    lines = [
        "[[hooks]]",
        'name = "claude-kit-session-start"',
        'type = "session_start"',
        f"command = '{start}'",
        "",
        "[[hooks]]",
        'name = "claude-kit-stop"',
        'type = "post_agent"',
        'match = "main"',
        f"command = '{stop}'",
    ]
    return replace_block(text, TOML_BEGIN, TOML_END, lines)


def is_kit_command(command: object) -> bool:
    return (
        isinstance(command, str)
        and '/plugin/hooks/run.py"' in command
        and "--agent " in command
    )


def is_kit_group(group: object) -> bool:
    inner = group.get("hooks") if isinstance(group, dict) else None
    return isinstance(inner, list) and any(
        isinstance(h, dict) and is_kit_command(h.get("command")) for h in inner
    )


def json_hooks(text: str, agent: str, python: str) -> str:
    """The agent's hooks.json text with the kit entries (re)added at the end."""
    data = json.loads(text) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("the top level is not an object")
    if agent == "cursor":
        if "version" in data:
            data["version"] = 1
        else:
            data = {"version": 1, **data}
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError('"hooks" is not an object')
    if agent == "codex":
        events = {"SessionStart": "SessionStart", "Stop": "Stop"}
    else:
        events = {"sessionStart": "SessionStart", "stop": "Stop"}
    for key, event in events.items():
        entries = hooks.get(key, [])
        if not isinstance(entries, list):
            raise ValueError(f'"hooks.{key}" is not a list')
        command = hook_command(python, agent, event)
        if agent == "codex":
            kept = [g for g in entries if not is_kit_group(g)]
            kept.append({"hooks": [{"type": "command", "command": command}]})
        else:
            kept = [
                e
                for e in entries
                if not (isinstance(e, dict) and is_kit_command(e.get("command")))
            ]
            kept.append({"command": command})
        hooks[key] = kept
    return json.dumps(data, indent=2) + "\n"


def agents_block(text: str, python: str, agent: str) -> str:
    return replace_block(text, MD_BEGIN, MD_END, [fallback_line(python, agent)])


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def install_agent(agent: str, home: Path, skills_dir: Path, python: str) -> int:
    """Link the kit skills and merge its hooks for Vibe, Codex or Cursor."""
    base = home / f".{agent}"
    hooks = base / ("hooks.toml" if agent == "vibe" else "hooks.json")
    old = read_text(hooks)
    try:
        if agent == "vibe":
            new = vibe_hooks(old, python)
        else:
            new = json_hooks(old, agent, python)
    except ValueError:
        print(f"ERROR: {hooks} is not valid JSON; nothing changed.")
        return 1
    files = [(hooks, old, new)]
    if agent != "cursor":
        rules = base / "AGENTS.md"
        old = read_text(rules)
        files.append((rules, old, agents_block(old, python, agent)))
    link_skills(skills_dir, skill_sources())
    for path, old, new in files:
        if new == old:
            print(f"Unchanged {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(new)
        print(f"Wrote {path}")
    print(NEXT_STEP[agent])
    if agent == "cursor":
        print(fallback_line(python, agent))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--agent", choices=AGENTS, default="claude")
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--skills-dir", default=None)
    parser.add_argument("--settings", default=None)
    parser.add_argument("--python", default="python", help="the command the hooks run")
    args = parser.parse_args(argv)
    home = Path(args.home)
    print(f"Detected: {os_name(sys.platform)}")
    if not check_python(args.python):
        return 1
    warn_missing_tools()
    if args.agent != "claude":
        skills_dir = Path(args.skills_dir or home / ".agents" / "skills")
        return install_agent(args.agent, home, skills_dir, args.python)
    skills_dir = Path(args.skills_dir or home / ".claude" / "skills")
    settings = Path(args.settings or home / ".claude" / "settings.json")
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
