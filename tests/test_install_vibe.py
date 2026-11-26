import importlib.util
import json
import subprocess
import sys
import tarfile

import pytest
from helpers import PLUGIN, REPO

BOOTSTRAP = PLUGIN / "install-vibe.py"
MANIFEST = PLUGIN / ".claude-plugin" / "plugin.json"
VERSION = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
SKIP = {".git", "__pycache__", ".worktrees"}


def bootstrap_module():
    spec = importlib.util.spec_from_file_location("install_vibe", BOOTSTRAP)
    assert spec and spec.loader, BOOTSTRAP
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_bootstrap(home, *extra):
    command = [sys.executable, str(BOOTSTRAP), "--home", str(home), *extra]
    return subprocess.run(command, capture_output=True, text=True, timeout=180)


def write_repo_tarball(path, top="agent-kit-main"):
    """A tarball in the shape GitHub serves: one top-level folder."""
    with tarfile.open(path, "w:gz") as tar:
        for file in sorted(REPO.rglob("*")):
            if file.is_file():
                relative = file.relative_to(REPO)
                if not any(part in SKIP for part in relative.parts):
                    tar.add(file, arcname=f"{top}/{relative.as_posix()}")


@pytest.fixture(scope="module")
def repo_tarball(tmp_path_factory):
    path = tmp_path_factory.mktemp("tarball") / "repo.tar.gz"
    write_repo_tarball(path)
    return path


@pytest.fixture()
def installed(tmp_path, repo_tarball):
    home = tmp_path / "home"
    result = run_bootstrap(home, "--tarball", str(repo_tarball))
    assert result.returncode == 0, result.stdout + result.stderr
    return home


def test_tarball_url_forms():
    module = bootstrap_module()
    base = "https://codeload.github.com/alymo8/claude-kit/tar.gz/main"
    assert module.tarball_url("alymo8/claude-kit", "main") == base
    assert module.tarball_url("https://github.com/alymo8/claude-kit", "main") == base
    assert (
        module.tarball_url("https://github.com/alymo8/claude-kit.git", "main") == base
    )
    assert module.tarball_url("https://github.com/alymo8/claude-kit/", "v1") == (
        "https://codeload.github.com/alymo8/claude-kit/tar.gz/v1"
    )


@pytest.mark.parametrize(
    "repo",
    ["https://gitlab.com/alymo8/claude-kit", "kit", "alymo8/kits/extra"],
)
def test_tarball_url_refuses(repo):
    module = bootstrap_module()
    with pytest.raises(module.BootstrapError):
        module.tarball_url(repo, "main")


def test_installs_the_vibe_plugins(installed):
    plugins = installed / ".vibe" / "plugins"
    assert sorted(p.name for p in plugins.iterdir()) == [
        "agent-kit",
        "superpowers",
    ]
    for name in ("agent-kit", "superpowers"):
        data = json.loads((plugins / name / "plugin.json").read_text("utf-8"))
        assert data["name"] == name
        assert (plugins / name / ".agent-kit-build").is_file()
    kit = plugins / "agent-kit"
    assert (kit / "skills" / "ship" / "SKILL.md").is_file()
    rules = installed / ".vibe" / "AGENTS.md"
    assert rules.is_file()
    assert "agent-kit:begin" in rules.read_text(encoding="utf-8")


def test_reports_the_version_and_next_step(tmp_path, repo_tarball):
    home_dir = tmp_path / "home"
    result = run_bootstrap(home_dir, "--tarball", str(repo_tarball))
    assert f"Downloaded agent-kit {VERSION} to" in result.stdout
    assert "rerun this command to upgrade" in result.stdout
    assert "Next: start a new Vibe session" in result.stdout


def test_keeps_the_source_in_the_cache(installed):
    cache = installed / ".vibe" / ".agent-kit-src" / "agent-kit"
    marker = cache / ".agent-kit-src"
    assert (cache / "plugin" / "install.py").is_file()
    assert marker.is_file()
    assert VERSION in marker.read_text(encoding="utf-8")


def test_upgrade_is_idempotent(tmp_path, repo_tarball):
    home = tmp_path / "h"
    first = run_bootstrap(home, "--tarball", str(repo_tarball))
    assert first.returncode == 0, first.stdout + first.stderr
    plugins = home / ".vibe" / "plugins"
    snapshot = sorted(p.name for p in plugins.iterdir())
    second = run_bootstrap(home, "--tarball", str(repo_tarball))
    assert second.returncode == 0, second.stdout + second.stderr
    assert sorted(p.name for p in plugins.iterdir()) == snapshot
    sources = home / ".vibe" / ".agent-kit-src"
    assert not (sources / "agent-kit.old").exists()
    assert not (sources / ".staging").exists()


def test_foreign_cache_is_refused(installed, repo_tarball):
    cache = installed / ".vibe" / ".agent-kit-src" / "agent-kit"
    before = {p.name for p in cache.iterdir()}
    (cache / ".agent-kit-src").unlink()
    result = run_bootstrap(installed, "--tarball", str(repo_tarball))
    assert result.returncode == 1
    assert "not written by the bootstrap" in result.stdout
    assert {p.name for p in cache.iterdir()} == before - {".agent-kit-src"}


def test_missing_tarball_is_refused(tmp_path):
    result = run_bootstrap(tmp_path, "--tarball", str(tmp_path / "no.tar.gz"))
    assert result.returncode == 1
    assert "is not a file" in result.stdout


def test_flat_tarball_is_refused(tmp_path):
    path = tmp_path / "flat.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        readme = tmp_path / "README.md"
        readme.write_text("not a repo\n", encoding="utf-8")
        tar.add(readme, arcname="README.md")
    result = run_bootstrap(tmp_path / "h", "--tarball", str(path))
    assert result.returncode == 1
    assert "no single top-level folder" in result.stdout


def test_escaping_tarball_member_is_refused(tmp_path):
    path = tmp_path / "escape.tar.gz"
    home = tmp_path / "h"
    sources = home / ".vibe" / ".agent-kit-src"
    with tarfile.open(path, "w:gz") as tar:
        inside = tmp_path / "plugin.py"
        inside.write_text("x = 1\n", encoding="utf-8")
        tar.add(inside, arcname="agent-kit-main/plugin/install.py")
        tar.add(inside, arcname="../escape.txt")
    result = run_bootstrap(home, "--tarball", str(path))
    assert result.returncode == 1
    assert "escapes the source cache" in result.stdout
    assert not (sources / "escape.txt").exists()
    assert not (sources / "agent-kit").exists()
