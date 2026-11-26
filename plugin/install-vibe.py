#!/usr/bin/env python3
"""Install agent-kit in Mistral Vibe without a checkout of the repo.

Usage: install-vibe.py [--home DIR] [--python CMD] [--repo REPO]
                       [--ref REF] [--tarball FILE]

Downloads the kit repo as a tarball from GitHub (default: alymo8/claude-kit,
branch main; no git needed), unpacks it into the persistent cache
<home>/.vibe/.agent-kit-src/agent-kit, and runs plugin/install.py
--agent vibe from it. Re-running the command refreshes the cache and
rebuilds the plugins, so it is also the upgrade path: the Vibe plugins
are a copy.

The hooks run --python (default: the path of this interpreter, so they
survive later even when the bare `python` is Python 2 or the Windows
store stub); pass --python python to keep the plain command.

--tarball skips the download and installs from a local tar.gz instead
(the shape GitHub serves, a single top-level folder), so the kit can be
installed offline or from a test.

Idempotent. A cache folder the bootstrap did not write is never
replaced. Keep this file parseable by Python 3.8, so an old interpreter
still reaches a clear error inside install.py.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPO = "alymo8/claude-kit"
REF = "main"
KIT_DIR = "agent-kit"
MARKER = ".agent-kit-src"
STAGING = ".staging"


class BootstrapError(Exception):
    pass


def tarball_url(repo: str, ref: str) -> str:
    """The codeload URL of a repo given as ``owner/repo`` or a github URL."""
    repo = repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    if "://" in repo:
        parts = repo.split("://", 1)[1].split("/", 1)
        if len(parts) != 2 or parts[0] != "github.com":
            raise BootstrapError(f"--repo {repo} is not a GitHub repository URL")
        repo = parts[1]
    if repo.count("/") != 1:
        raise BootstrapError(f"--repo {repo} is not owner/repo or a GitHub URL")
    return f"https://codeload.github.com/{repo}/tar.gz/{ref}"


def download(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "agent-kit-install"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with open(dest, "wb") as handle:
                shutil.copyfileobj(response, handle)
    except OSError as exc:
        raise BootstrapError(f"cannot download {url}: {exc}") from exc


def safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract into dest, refusing any member that would escape it."""
    inside = str(dest.resolve())
    sep = os.sep
    for member in tar.getmembers():
        target = str((dest / member.name).resolve())
        if target != inside and not target.startswith(inside + sep):
            raise BootstrapError(
                f"tarball entry {member.name} escapes the source cache"
            )
    try:
        tar.extractall(dest, filter="data")
    except TypeError:
        tar.extractall(dest)


def kit_root(staging: Path) -> Path:
    """The root of the extracted repo: its single top-level folder."""
    try:
        children = sorted(p for p in staging.iterdir())
    except OSError as exc:
        raise BootstrapError(f"cannot read the extracted source: {exc}") from exc
    if len(children) != 1 or not children[0].is_dir():
        raise BootstrapError(
            "the tarball has no single top-level folder; refuse to install it"
        )
    root = children[0]
    if not (root / "plugin" / "install.py").is_file():
        raise BootstrapError("the tarball holds no plugin/install.py")
    return root


def cache_version(root: Path) -> str:
    try:
        data = json.loads(
            (root / "plugin" / ".claude-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        return data["version"]
    except (OSError, ValueError, KeyError) as exc:
        raise BootstrapError(f"cannot read the kit version: {exc}") from exc


def refresh_cache(sources: Path, cache: Path, ref: str) -> str:
    """Unpack a fresh tarball over the cache folder, keeping a way back."""
    if os.path.lexists(cache) and not (cache / MARKER).is_file():
        raise BootstrapError(
            f"{cache} exists and was not written by the bootstrap; remove or "
            "rename it, then rerun. Nothing changed."
        )
    staging = sources / STAGING
    if staging.is_dir():
        shutil.rmtree(staging, ignore_errors=False)
    staging.mkdir(parents=True)
    with tarfile.open(sources / "tarball.tar.gz", "r:gz") as tar:
        safe_extract(tar, staging)
    root = kit_root(staging)
    version = cache_version(root)
    kit = staging / KIT_DIR
    shutil.move(str(root), str(kit))
    staging_items = [p.name for p in staging.iterdir()]
    if staging_items != [KIT_DIR]:
        raise BootstrapError(
            "the tarball held more than the repo folder; refuse to install it"
        )
    (kit / MARKER).write_text(f"agent-kit {version} ({ref})\n", encoding="utf-8")
    old = sources / f"{KIT_DIR}.old"
    if os.path.lexists(old):
        raise BootstrapError(
            f"{old} is in the way; remove it, then rerun. Nothing changed."
        )
    if not os.path.lexists(cache):
        os.rename(kit, cache)
    else:
        os.rename(cache, old)
        try:
            os.rename(kit, cache)
        except OSError as exc:
            os.rename(old, cache)
            raise BootstrapError(f"cannot swap in the new source: {exc}") from exc
        shutil.rmtree(old, ignore_errors=True)
    staging.rmdir()
    return version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument(
        "--python",
        default=None,
        help="the command the hooks run (default: this interpreter path)",
    )
    parser.add_argument("--repo", default=REPO, help="owner/repo or a GitHub URL")
    parser.add_argument("--ref", default=REF, help="a branch, tag or commit")
    parser.add_argument(
        "--tarball", default=None, help="install from a local tar.gz instead"
    )
    args = parser.parse_args(argv)
    home = Path(args.home)
    sources = home / ".vibe" / ".agent-kit-src"
    cache = sources / KIT_DIR
    if args.tarball is None:
        url = tarball_url(args.repo, args.ref)
        print(f"Downloading {url}")
        sources.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(dir=sources, suffix=".tar.gz")
        os.close(handle)
        target = Path(name)
        try:
            download(url, target)
            os.replace(target, sources / "tarball.tar.gz")
        except (BootstrapError, OSError) as exc:
            target.unlink(missing_ok=True)
            print(f"ERROR: {exc}; nothing changed.")
            return 1
    else:
        target = Path(args.tarball)
        if not target.is_file():
            print(f"ERROR: --tarball {target} is not a file; nothing changed.")
            return 1
        sources.mkdir(parents=True, exist_ok=True)
        if target.resolve() != (sources / "tarball.tar.gz").resolve():
            shutil.copyfile(target, sources / "tarball.tar.gz")
    try:
        version = refresh_cache(sources, cache, args.ref)
    except (BootstrapError, OSError) as exc:
        print(f"ERROR: {exc}; nothing changed.")
        return 1
    print(f"Downloaded agent-kit {version} to {cache}", flush=True)
    print(f"The source stays in {sources}; rerun this command to upgrade", flush=True)
    command = [
        sys.executable,
        str(cache / "plugin" / "install.py"),
        "--agent",
        "vibe",
        "--home",
        str(home),
        "--python",
        args.python or sys.executable,
    ]
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())
