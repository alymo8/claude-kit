"""Build the agent-kit and superpowers plugins for Mistral Vibe.

Assembles two native Vibe plugin folders from this checkout, `agent-kit` (the
kit's playbooks, commands, hooks and skills) and `superpowers` (the vendored
superpowers skills), in a staging folder beside the output folder, then swaps
them in. Every built folder holds plain files only and a `.agent-kit-build`
marker; a folder without the marker is never replaced.

Usage: python plugin/vibe_plugin.py --out DIR [--python CMD]

Spec: docs/superpowers/specs/2026-11-23-vibe-plugin-design.md (ADR 0053).
Keep this file parseable by Python 3.8 (install.py imports it).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

NAMES = ("agent-kit", "superpowers")
MARKER = ".agent-kit-build"
STAGING = ".agent-kit-staging"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
REPOSITORY = "https://github.com/alymo8/claude-kit"
KIT = Path(__file__).resolve().parent.parent

TOP_LEVEL_SKIP = {
    ".claude-plugin",
    "agent-skills",
    "skills",
    "install.py",
    "install.ps1",
    "vibe_plugin.py",
}
RUNTIME = shutil.ignore_patterns("__pycache__", "*.pyc")


class BuildError(Exception):
    pass


def read_version_file(path: Path) -> tuple[str, str]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc
    values = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    for key in ("version", "source"):
        if not values.get(key):
            raise BuildError(f"{path} has no {key}: line")
    return values["version"], values["source"]


def runner_command(python: str, runner: Path, event: str) -> str:
    exe = f'"{python}"' if " " in python else python
    return f'{exe} "{Path(runner).as_posix()}" --agent vibe --event {event}'


def hooks_toml(python: str, runner: Path) -> str:
    start = runner_command(python, runner, "SessionStart")
    stop = runner_command(python, runner, "Stop")
    return (
        "[[hooks]]\n"
        'name = "agent-kit-session-start"\n'
        'type = "session_start"\n'
        f"command = {json.dumps(start)}\n"
        "\n"
        "[[hooks]]\n"
        'name = "agent-kit-stop"\n'
        'type = "post_agent"\n'
        'match = "main"\n'
        f"command = {json.dumps(stop)}\n"
    )


def foreign_folders(out: Path) -> list[Path]:
    out = Path(out)
    return [
        out / name
        for name in NAMES
        if os.path.lexists(out / name) and not (out / name / MARKER).is_file()
    ]


def merge_skills(roots: list[Path], dest: Path) -> list[str]:
    seen = {}
    for root in roots:
        root = Path(root)
        for child in sorted(root.iterdir()):
            if not (child / "SKILL.md").is_file():
                continue
            if child.name in seen:
                raise BuildError(
                    f"skill {child.name} is in both {seen[child.name]} and {root}"
                )
            seen[child.name] = root
            shutil.copytree(child, Path(dest) / child.name, ignore=RUNTIME)
    return sorted(seen)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, indent=2) + "\n")


def stage_agent_kit(kit: Path, dest: Path, claude: dict, hooks: str) -> None:
    source = kit / "plugin"

    def ignore(directory, names):
        skipped = set(RUNTIME(directory, names))
        if Path(directory) == source:
            skipped |= TOP_LEVEL_SKIP & set(names)
        return skipped

    shutil.copytree(source, dest, ignore=ignore)
    merge_skills([source / "skills", source / "agent-skills"], dest / "skills")
    data = {"$schema": SCHEMA, "name": "agent-kit"}
    for key in ("version", "description", "author", "license"):
        data[key] = claude[key]
    data["repository"] = REPOSITORY
    data["extensions"] = {
        "ai.mistral.vibe": {"schemaVersion": 1, "displayName": "agent-kit"}
    }
    write_json(dest / "plugin.json", data)
    write_text(dest / "ai.mistral.vibe" / "hooks.toml", hooks)
    write_text(dest / MARKER, claude["version"] + "\n")


def stage_superpowers(kit: Path, dest: Path, kit_version: str) -> None:
    vendor = kit / "vendor" / "superpowers"
    version, source = read_version_file(vendor / "VERSION")
    merge_skills([vendor / "skills"], dest / "skills")
    for name in ("LICENSE", "VERSION"):
        shutil.copyfile(vendor / name, dest / name)
    data = {
        "$schema": SCHEMA,
        "name": "superpowers",
        "version": version,
        "description": (
            f"The superpowers skills, the copy bundled by agent-kit (from {source})."
        ),
        "license": "MIT",
        "repository": source,
        "extensions": {"ai.mistral.vibe": {"schemaVersion": 1}},
    }
    write_json(dest / "plugin.json", data)
    write_text(dest / MARKER, kit_version + "\n")


def swap(out: Path, staging: Path) -> None:
    done = []  # (target, old or None) for plugins already swapped in
    for name in NAMES:
        target = out / name
        old = staging / f"{name}.old"
        moved = None
        try:
            if os.path.lexists(target):
                os.rename(target, old)
                moved = old
            os.rename(staging / name, target)
        except OSError as exc:
            if moved is not None:
                try:
                    os.rename(moved, target)
                except OSError:
                    pass
            for prev_target, prev_old in reversed(done):
                shutil.rmtree(prev_target, ignore_errors=True)
                if prev_old is not None:
                    try:
                        os.rename(prev_old, prev_target)
                    except OSError:
                        pass
            raise BuildError(f"could not swap in the new copy: {exc}") from exc
        done.append((target, moved))


def build(out: Path, python: str = "python", kit: Path = KIT) -> None:
    out = Path(out).resolve()
    kit = Path(kit)
    foreign = foreign_folders(out)
    if foreign:
        raise BuildError(
            f"{foreign[0]} exists and was not built by agent-kit; remove or rename it"
        )
    staging = out.parent / STAGING
    if os.path.lexists(staging):
        shutil.rmtree(staging)
    try:
        manifest = kit / "plugin" / ".claude-plugin" / "plugin.json"
        claude = json.loads(manifest.read_text(encoding="utf-8"))
        read_version_file(kit / "vendor" / "superpowers" / "VERSION")
        hooks = hooks_toml(python, out / "agent-kit" / "hooks" / "run.py")
        stage_agent_kit(kit, staging / "agent-kit", claude, hooks)
        stage_superpowers(kit, staging / "superpowers", claude["version"])
        out.mkdir(parents=True, exist_ok=True)
        swap(out, staging)
    except BuildError:
        raise
    except (OSError, ValueError, KeyError) as exc:
        raise BuildError(str(exc)) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the agent-kit and superpowers Vibe plugins."
    )
    parser.add_argument("--out", required=True, help="folder to build into")
    parser.add_argument("--python", default="python", help="python command")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    try:
        build(out, args.python)
    except BuildError as exc:
        print(f"ERROR: {exc}; nothing changed.")
        return 1
    print(f"Built agent-kit and superpowers in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
