#!/usr/bin/env python3
"""Install agent-kit as a Claude Code skills-dir plugin, on any OS.

Usage: install.py [--agent {claude,vibe,codex,cursor}] [--home DIR]
                  [--skills-dir DIR] [--settings FILE] [--python CMD]

First checks that the command the hooks run (default "python") is Python
3.11+, and exits 1 with nothing changed if not. For Vibe, Codex and Cursor it
first refuses a python path holding ", $, a backtick or %, which no hook shell
quoting protects. Warns when git, gh or the
superpowers plugin is missing. Then, for Claude Code, in three steps:

1. Removes the old link (<skills-dir>/<LEGACY_LINK>) when it points at a kit
   plugin folder; anything else at that path is left alone.
2. Adds the kit's status line when none is configured, or moves one that
   still runs through the old link. When the plugin is installed from the
   marketplace (recorded in <config>/plugins/installed_plugins.json, <config>
   being $CLAUDE_CONFIG_DIR or <home>/.claude), the line runs a stable copy
   of the script kept in the kit's state folder under <config>.
3. Links <skills-dir>/agent-kit to this plugin folder (a junction on Windows,
   a symlink elsewhere), so Claude Code loads the kit from the git checkout
   (ADR 0005, amended by ADR 0033), unless a marketplace copy is installed:
   then it links nothing, so only one copy loads.

Idempotent; refuses to overwrite anything else at the link path.

With --agent codex or cursor it instead links every kit skill folder
(plugin/skills, plugin/agent-skills, vendor/superpowers/skills) into
<home>/.agents/skills and merges plugin/hooks/run.py into the agent's user
hook file (for Codex also a fallback line into its AGENTS.md), replacing the
blocks an older kit version wrote.

With --agent vibe it builds the agent-kit and superpowers Vibe plugins into
<home>/.vibe/plugins (plugin/vibe_plugin.py), removes the kit's old block from
<home>/.vibe/hooks.toml and, when Codex and Cursor do not use them, the old
kit skill links in <skills-dir>, and keeps the fallback line in
<home>/.vibe/AGENTS.md pointing at the copy's hook runner.

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
LINK_NAME = "agent-kit"
LEGACY_LINK = "claude-kit"
PLUGIN_ID = "agent-kit@agent-kit"
TOML_BEGIN = "# >>> agent-kit hooks (managed by plugin/install.py) >>>"
TOML_END = "# <<< agent-kit hooks <<<"
MD_BEGIN = "<!-- agent-kit:begin (managed by plugin/install.py) -->"
MD_END = "<!-- agent-kit:end -->"
LEGACY_TOML_BEGIN = TOML_BEGIN.replace(LINK_NAME, LEGACY_LINK)
LEGACY_TOML_END = TOML_END.replace(LINK_NAME, LEGACY_LINK)
LEGACY_MD_BEGIN = MD_BEGIN.replace(LINK_NAME, LEGACY_LINK)
LEGACY_MD_END = MD_END.replace(LINK_NAME, LEGACY_LINK)
NEXT_STEP = {
    "vibe": "Next: start a new Vibe session (or run /reload-plugins).",
    "codex": "Next: in Codex, run /hooks and trust the agent-kit hooks.",
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


def config_dir(home: Path) -> Path:
    """$CLAUDE_CONFIG_DIR when set and non-empty, else <home>/.claude."""
    value = os.environ.get("CLAUDE_CONFIG_DIR", "")
    return Path(value) if value else home / ".claude"


def marketplace_copy(config: Path) -> Path | None:
    """The installed marketplace copy of the kit, or None.

    Reads <config>/plugins/installed_plugins.json, prefers the user-scope
    entry, and returns the first installPath that is an existing folder. Any
    read, parse or shape problem gives None.
    """
    record = config / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
        entries = data["plugins"][PLUGIN_ID]
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return None
    if not isinstance(entries, list):
        return None
    entries = [e for e in entries if isinstance(e, dict)]
    entries.sort(key=lambda e: e.get("scope") != "user")
    for entry in entries:
        path = entry.get("installPath")
        if isinstance(path, str) and path and Path(path).is_dir():
            return Path(path)
    return None


def is_kit_plugin(folder: Path) -> bool:
    """True when folder holds this kit's plugin manifest (old or new name)."""
    manifest = folder / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("name") in (LEGACY_LINK, LINK_NAME)


def remove_legacy_link(skills_dir: Path) -> bool:
    """Remove <skills-dir>/<LEGACY_LINK> when it is a link to a kit plugin."""
    link = skills_dir / LEGACY_LINK
    if is_link(link) and not os.path.exists(link):
        print(
            f"NOTE: the old link {link} points nowhere; "
            "left in place, remove it yourself."
        )
        return False
    if not is_link(link) or not is_kit_plugin(Path(os.path.realpath(link))):
        return False
    remove_link(link)
    print(f"Removed the old link {link}")
    return True


def install_link(skills_dir: Path) -> str | None:
    """'installed' or 'present'; None after printing an error."""
    link = skills_dir / LINK_NAME
    if os.path.lexists(link):
        if is_link(link) and points_at_plugin(link):
            print(f"{LINK_NAME} already installed: {link} -> {PLUGIN}")
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


def install_statusline(
    settings: Path, skills_dir: Path, config: Path | None = None
) -> None:
    script = PLUGIN / "scripts" / "install-statusline.py"
    command = [sys.executable, str(script), "--settings", str(settings)]
    command += ["--skills-dir", str(skills_dir)]
    if config is not None:
        command += ["--stable-copy", "--config-dir", str(config)]
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


SAFE = "_./:\\-"
REFUSED = ('"', "$", "`", "%")


def quote_python(python: str) -> str:
    """The python path, double-quoted unless every character is safe bare."""
    if all(c.isalnum() or c in SAFE for c in python):
        return python
    return f'"{python}"'


def unquotable(python: str) -> str | None:
    """The first character of python that no hook quoting protects, or None."""
    return next((c for c in python if c in REFUSED), None)


def refusal(python: str, char: str) -> str:
    return (
        f"--python {python} contains {char}, which a hook command cannot quote safely"
    )


def hook_command(python: str, agent: str, event: str, runner: Path = RUNNER) -> str:
    exe = quote_python(python)
    return f'{exe} "{Path(runner).as_posix()}" --agent {agent} --event {event}'


def fallback_line(python: str, agent: str, runner: Path = RUNNER) -> str:
    command = hook_command(python, agent, "SessionStart", runner=runner)
    return (
        'If your context has no "Kit map (agent-kit)" text, run '
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


def under_kit_roots(target: str, link: Path) -> bool:
    if not os.path.isabs(target):
        target = os.path.join(str(link.parent), target)
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
        if target is not None and under_kit_roots(target, link):
            remove_link(link)
            make_link(link, folder)
            print(f"Relinked {name}")
            continue
        print(
            f"Skipped {name}: {link} exists and is not a link into this kit"
            " checkout (remove it by hand if it points into an old checkout)"
        )
    for link in sorted(skills_dir.iterdir()):
        target = link_target(link)
        if target is None or os.path.exists(link):
            continue
        if not under_kit_roots(target, link):
            continue
        remove_link(link)
        print(f"Removed {link.name} (dangling)")


def strip_block(text: str, begin: str, end: str) -> str:
    """text without its managed block between begin and end.

    Raises ValueError when the markers are damaged (a marker missing its pair,
    or more than one block): cutting there could delete the user's own text.
    """
    if text.count(begin) != text.count(end) or text.count(begin) > 1:
        raise ValueError(f"the block markers are damaged ({begin!r})")
    start = text.find(begin)
    stop = text.find(end, start) if start >= 0 else -1
    if start >= 0 and stop < 0:
        raise ValueError(f"the block markers are damaged ({begin!r})")
    if stop >= 0:
        stop += len(end)
        if text[stop : stop + 1] == "\n":
            stop += 1
        text = text[:start] + text[stop:]
    return text


def replace_block(text: str, begin: str, end: str, lines: list[str]) -> str:
    """text without its managed block, then a fresh block at the end."""
    rest = strip_block(text, begin, end).rstrip("\n")
    block = "\n".join([begin, *lines, end]) + "\n"
    return f"{rest}\n\n{block}" if rest else block


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


def agents_block(text: str, python: str, agent: str, runner: Path = RUNNER) -> str:
    text = strip_block(text, LEGACY_MD_BEGIN, LEGACY_MD_END)
    line = fallback_line(python, agent, runner=runner)
    return replace_block(text, MD_BEGIN, MD_END, [line])


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def has_kit_command(data: object) -> bool:
    """True when any string anywhere in the parsed JSON is a kit hook command."""
    if isinstance(data, dict):
        return any(has_kit_command(v) for v in data.values())
    if isinstance(data, list):
        return any(has_kit_command(v) for v in data)
    return is_kit_command(data)


def kit_hooks_in_use(home: Path) -> tuple[list[Path], list[Path]]:
    """The Codex and Cursor hook files that may still run the kit's hooks.

    Returns (files holding a kit hook command, files that cannot be read or
    parsed); a missing file is in neither list.
    """
    found: list[Path] = []
    unreadable: list[Path] = []
    for agent in ("codex", "cursor"):
        path = home / f".{agent}" / "hooks.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            unreadable.append(path)
            continue
        if has_kit_command(data):
            found.append(path)
    return found, unreadable


def kit_links(skills_dir: Path) -> list[Path]:
    """The links in skills_dir into this checkout's skill roots (dangling too)."""
    if not skills_dir.is_dir():
        return []
    found = []
    for entry in sorted(skills_dir.iterdir()):
        target = link_target(entry)
        if target is not None and under_kit_roots(target, entry):
            found.append(entry)
    return found


def remove_kit_links(skills_dir: Path) -> bool:
    """Remove the links into this checkout's skill roots (dangling ones too).

    Returns True when every kit link was removed (also when there were none).
    """
    if not skills_dir.is_dir():
        return True
    ok = True
    kit = set(kit_links(skills_dir))
    names = {f.name for f in skill_sources()}
    for entry in sorted(skills_dir.iterdir()):
        if entry in kit:
            try:
                remove_link(entry)
            except OSError as exc:
                print(f"Could not remove {entry.name}: {exc}")
                ok = False
                continue
            print(f"Removed old link {entry.name}")
        elif entry.name in names and link_target(entry) is not None:
            print(
                f"Kept {entry.name}: it links outside this kit checkout (remove it"
                " by hand if it points into an old checkout)"
            )
    return ok


def install_vibe(home: Path, skills_dir: Path, python: str) -> int:
    """Build the agent-kit and superpowers Vibe plugins, remove the old install."""
    if str(PLUGIN) not in sys.path:
        sys.path.insert(0, str(PLUGIN))
    import vibe_plugin

    plugins = (home / ".vibe" / "plugins").resolve()
    foreign = vibe_plugin.foreign_folders(plugins)
    if foreign:
        print(
            f"ERROR: {foreign[0]} exists and was not built by agent-kit; remove or "
            "rename it, then rerun. Nothing changed."
        )
        return 1
    hooks = home / ".vibe" / "hooks.toml"
    rules = home / ".vibe" / "AGENTS.md"
    runner = plugins / "agent-kit" / "hooks" / "run.py"
    current = hooks
    try:
        old = read_text(hooks)
        rest = strip_block(old, LEGACY_TOML_BEGIN, LEGACY_TOML_END)
        rest = strip_block(rest, TOML_BEGIN, TOML_END)
        current = rules
        old_rules = read_text(rules)
        new_rules = agents_block(old_rules, python, "vibe", runner=runner)
    except ValueError as exc:
        print(f"ERROR: {current} cannot be updated ({exc}); nothing changed.")
        return 1
    try:
        vibe_plugin.build(plugins, python)
    except vibe_plugin.ChangedError as exc:
        print(f"ERROR: {exc}")
        return 1
    except vibe_plugin.BuildError as exc:
        print(f"ERROR: {exc}; nothing changed.")
        return 1
    print(f"Installed the agent-kit and superpowers plugins in {plugins}")
    ok = True
    if rest != old:
        try:
            if rest.strip() == "":
                hooks.unlink()
                print(f"Removed {hooks} (only the kit's hooks were in it)")
            else:
                vibe_plugin.write_text(hooks, rest.rstrip("\n") + "\n")
                print(f"Wrote {hooks}")
        except OSError as exc:
            print(
                f"ERROR: could not update {hooks} ({exc}); the plugins are "
                f"installed, but remove the kit block from {hooks} by hand or "
                "rerun."
            )
            ok = False
    if new_rules == old_rules:
        print(f"Unchanged {rules}")
    else:
        try:
            vibe_plugin.write_text(rules, new_rules)
            print(f"Wrote {rules}")
        except OSError as exc:
            print(
                f"ERROR: could not write {rules} ({exc}); the plugins are "
                f"installed, but update the kit block in {rules} by hand or "
                "rerun."
            )
            ok = False
    in_use, unreadable = kit_hooks_in_use(home)
    if not in_use and not unreadable:
        ok = remove_kit_links(skills_dir) and ok
    elif kit_links(skills_dir):
        for path in unreadable:
            print(
                f"Kept the kit's skill links: {path} cannot be read, so it may "
                "still use them."
            )
        if in_use:
            print(
                f"WARNING: kept the kit's skill links in {skills_dir}: "
                f"{', '.join(str(p) for p in in_use)} still run the kit's hooks, "
                "so Vibe lists the kit's skills twice (bare and agent-kit:-"
                "prefixed) until Codex and Cursor stop using them."
            )
    print(NEXT_STEP["vibe"])
    return 0 if ok else 1


def install_agent(agent: str, home: Path, skills_dir: Path, python: str) -> int:
    """Link the kit skills and merge its hooks for Codex or Cursor."""
    base = home / f".{agent}"
    hooks = base / "hooks.json"
    rules = base / "AGENTS.md"
    current = hooks
    try:
        old = read_text(hooks)
        new = json_hooks(old, agent, python)
        files = [(hooks, old, new)]
        if agent != "cursor":
            current = rules
            old = read_text(rules)
            files.append((rules, old, agents_block(old, python, agent)))
    except ValueError as exc:
        print(f"ERROR: {current} cannot be updated ({exc}); nothing changed.")
        return 1
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
    char = unquotable(args.python)
    if args.agent != "claude" and char:
        print(f"ERROR: {refusal(args.python, char)}; nothing changed.")
        return 1
    if not check_python(args.python):
        return 1
    warn_missing_tools()
    if args.agent != "claude":
        skills_dir = Path(args.skills_dir or home / ".agents" / "skills")
        if args.agent == "vibe":
            return install_vibe(home, skills_dir, args.python)
        return install_agent(args.agent, home, skills_dir, args.python)
    skills_dir = Path(args.skills_dir or home / ".claude" / "skills")
    settings = Path(args.settings or home / ".claude" / "settings.json")
    config = config_dir(home)
    copy = marketplace_copy(config)
    new_link = skills_dir / LINK_NAME
    try:
        removed = remove_legacy_link(skills_dir)
        if copy is not None and is_link(new_link) and points_at_plugin(new_link):
            remove_link(new_link)
            print(f"Removed {new_link} (the marketplace copy loads instead)")
            removed = True
    except OSError as exc:
        print(f"ERROR: could not remove the old link: {exc}")
        return 1
    install_statusline(settings, skills_dir, config if copy else None)
    if copy is not None:
        print(
            f"{LINK_NAME} is installed from the marketplace ({copy}); "
            "not linking, so only one copy loads."
        )
        outcome = "marketplace"
    else:
        try:
            outcome = install_link(skills_dir)
        except OSError as exc:
            print(f"ERROR: could not create the link: {exc}")
            return 1
        if outcome is None:
            return 1
    if not superpowers_enabled(settings):
        print(
            "WARNING: the superpowers plugin is not enabled. The kit's flow "
            f"uses its skills. In Claude Code run: /plugin install {SUPERPOWERS}"
        )
    if outcome == "installed" or removed:
        print(
            "Start a new Claude Code session (or run /reload-plugins) to load the kit."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
