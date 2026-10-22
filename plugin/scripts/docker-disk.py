#!/usr/bin/env python3
"""Print one status line for Docker Desktop's virtual disk on Windows.

Usage: docker-disk.py [--path]

The line reads::

    docker disk: file 9.5 GiB, used 3.2 GiB, docker 1.6 GiB, sparse no -> <verdict>

``file`` is the size of the disk file on the host, ``used`` the space in use
inside the ``docker-desktop`` distro (``df``), ``docker`` the total that
``docker system df`` reports (context only), ``sparse`` whether the file has
the NTFS sparse attribute. The verdict is ``ok``, or ``not sparse`` and/or
``compact suggested (/docker-compact)`` when the file is more than 1.5 times
the used space and more than 2 GiB larger. An unknown value prints as ``?``.
Off Windows, or with no disk found, the line says ``skipped``.

``--path`` prints only the disk path (nothing when none is found or not on
Windows).

The script always exits 0. It runs no command other than
``wsl -l --running -q``, ``wsl -d docker-desktop -- df -B1
/mnt/docker-desktop-disk`` and ``docker system df``, and never starts the
``docker-desktop`` distro: if it is not running, ``used`` is ``?``.
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

GIB = 2**30
TIMEOUT = 15
DISTRO_CMD = ["wsl", "-l", "--running", "-q"]
DF_CMD = ["wsl", "-d", "docker-desktop", "--", "df", "-B1", "/mnt/docker-desktop-disk"]
DOCKER_CMD = ["docker", "system", "df"]

DISK_PATHS = (
    ("Docker", "wsl", "disk", "docker_data.vhdx"),
    ("Docker", "wsl", "data", "ext4.vhdx"),
)

ROW = re.compile(
    r"^(Images|Containers|Local Volumes|Build Cache)\s+\S+\s+\S+\s+"
    r"(\d+(?:\.\d+)?)(B|kB|MB|GB|TB)\s",
    re.M,
)
UNITS = {"B": 1, "kB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}
ROW_NAMES = {"Images", "Containers", "Local Volumes", "Build Cache"}

_stat = os.stat


def find_disk(localappdata: str | None) -> Path | None:
    """First existing Docker Desktop disk under ``localappdata``, or None."""
    if not localappdata:
        return None
    for parts in DISK_PATHS:
        path = Path(localappdata).joinpath(*parts)
        if path.is_file():
            return path
    return None


def read_disk(path: Path) -> tuple[int, bool] | None:
    """File size and whether the NTFS sparse attribute is set, None if unreadable."""
    try:
        st = _stat(path)
    except OSError:
        return None
    attrs = getattr(st, "st_file_attributes", 0)
    return st.st_size, attrs & stat.FILE_ATTRIBUTE_SPARSE_FILE != 0


def run(cmd: list[str]) -> bytes | None:
    """Stdout of ``cmd`` on exit 0, else None (missing, failed or timed out)."""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def running_distros(out: bytes) -> list[str]:
    """Distro names from ``wsl -l --running -q`` (UTF-16-LE or UTF-8)."""
    encoding = "utf-16-le" if b"\x00" in out else "utf-8"
    text = out.decode(encoding, errors="ignore")
    text = text.replace("\x00", "").replace("\ufeff", "")
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_df_used(text: str) -> int | None:
    """The ``Used`` column of the first data row of ``df -B1`` output."""
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    cols = lines[1].split()
    if len(cols) < 3 or not cols[2].isdecimal():
        return None
    return int(cols[2])


def parse_docker_total(text: str) -> int | None:
    """Sum of the four ``docker system df`` rows, or None if any does not parse."""
    sizes: dict[str, int] = {}
    for match in ROW.finditer(text + "\n"):
        name, number, unit = match.groups()
        sizes[name] = round(float(number) * UNITS[unit])
    if set(sizes) != ROW_NAMES:
        return None
    return sum(sizes.values())


def used_bytes() -> int | None:
    """Used space inside the running ``docker-desktop`` distro, or None."""
    out = run(DISTRO_CMD)
    if out is None or "docker-desktop" not in running_distros(out):
        return None
    out = run(DF_CMD)
    if out is None:
        return None
    return parse_df_used(out.decode("utf-8", errors="replace"))


def docker_bytes() -> int | None:
    """Total from ``docker system df``, or None."""
    out = run(DOCKER_CMD)
    if out is None:
        return None
    return parse_docker_total(out.decode("utf-8", errors="replace"))


def verdict(file: int, used: int | None, sparse: bool) -> str:
    flags = []
    if not sparse:
        flags.append("not sparse")
    if used is not None and file > 1.5 * used and file - used > 2 * GIB:
        flags.append("compact suggested (/docker-compact)")
    return "; ".join(flags) or "ok"


def gib(n: int | None) -> str:
    return "?" if n is None else f"{n / GIB:.1f} GiB"


def status_line(file: int, used: int | None, docker: int | None, sparse: bool) -> str:
    return (
        f"docker disk: file {gib(file)}, used {gib(used)}, docker {gib(docker)}, "
        f"sparse {'yes' if sparse else 'no'} -> {verdict(file, used, sparse)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Docker Desktop disk status.")
    parser.add_argument("--path", action="store_true", help="print the disk path only")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    windows = sys.platform == "win32"
    disk = find_disk(os.environ.get("LOCALAPPDATA")) if windows else None
    if args.path:
        if disk is not None:
            print(disk)
        return 0
    if not windows:
        print("docker disk: skipped (not Windows)")
        return 0
    info = read_disk(disk) if disk is not None else None
    if info is None:
        print("docker disk: skipped (no Docker Desktop disk found)")
        return 0
    file, sparse = info
    used = used_bytes()
    docker = docker_bytes()
    print(status_line(file, used, docker, sparse))
    return 0


if __name__ == "__main__":
    sys.exit(main())
