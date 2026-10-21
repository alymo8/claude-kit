import subprocess
from types import SimpleNamespace

import pytest
from helpers import PLUGIN, load_module

G = 2**30
DISTROS = "docker-desktop\r\nUbuntu\r\n".encode("utf-16-le")
DF = (
    b"Filesystem        1B-blocks       Used   Available Use% Mounted on\n"
    b"/dev/sde     1081101176832 3435973837 1022473838592   1%"
    b" /mnt/docker-desktop-disk\n"
)
DOCKER = (
    b"TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE\n"
    b"Images          5         2         1.2GB     800MB (66%)\n"
    b"Containers      2         0         212B      212B (100%)\n"
    b"Local Volumes   2         1         500MB     0B (0%)\n"
    b"Build Cache     10        0         45.5kB    45.5kB\n"
)


@pytest.fixture
def mod():
    return load_module(PLUGIN / "scripts" / "docker-disk.py", "docker_disk")


def fake_run(monkeypatch, mod, responses, calls=None):
    """Patch subprocess.run; responses maps tuple(cmd) -> (rc, bytes) or exception."""
    if calls is None:
        calls = []

    def run(cmd, **kwargs):
        calls.append(list(cmd))
        key = tuple(cmd)
        if key not in responses:
            pytest.fail(f"unexpected command: {cmd}")
        resp = responses[key]
        if isinstance(resp, BaseException):
            raise resp
        rc, out = resp
        return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr=b"")

    monkeypatch.setattr(mod.subprocess, "run", run)
    return calls


def windows(monkeypatch, mod, tmp_path, disk=True):
    monkeypatch.setattr(mod.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = tmp_path / "Docker" / "wsl" / "disk" / "docker_data.vhdx"
    if disk:
        path.parent.mkdir(parents=True)
        path.write_bytes(b"")
    return path


def full_responses(mod):
    return {
        tuple(mod.DISTRO_CMD): (0, DISTROS),
        tuple(mod.DF_CMD): (0, DF),
        tuple(mod.DOCKER_CMD): (0, DOCKER),
    }


def test_not_windows_skips(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod.sys, "platform", "linux")
    fake_run(monkeypatch, mod, {})
    assert mod.main([]) == 0
    assert capsys.readouterr().out.strip() == "docker disk: skipped (not Windows)"


def test_no_disk(mod, monkeypatch, tmp_path, capsys):
    windows(monkeypatch, mod, tmp_path, disk=False)
    fake_run(monkeypatch, mod, {})
    assert mod.main([]) == 0
    assert (
        capsys.readouterr().out.strip()
        == "docker disk: skipped (no Docker Desktop disk found)"
    )


def test_localappdata_unset(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod.sys, "platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    fake_run(monkeypatch, mod, {})
    assert mod.main([]) == 0
    assert (
        capsys.readouterr().out.strip()
        == "docker disk: skipped (no Docker Desktop disk found)"
    )


def test_find_disk_prefers_docker_data_then_ext4(mod, tmp_path):
    ext4 = tmp_path / "Docker" / "wsl" / "data" / "ext4.vhdx"
    ext4.parent.mkdir(parents=True)
    ext4.write_bytes(b"")
    assert mod.find_disk(str(tmp_path)) == ext4
    data = tmp_path / "Docker" / "wsl" / "disk" / "docker_data.vhdx"
    data.parent.mkdir(parents=True)
    data.write_bytes(b"")
    assert mod.find_disk(str(tmp_path)) == data
    assert mod.find_disk(None) is None
    assert mod.find_disk("") is None


def test_read_disk_size_from_real_file(mod, tmp_path):
    p = tmp_path / "d.vhdx"
    p.write_bytes(b"x" * 1234)
    assert mod.read_disk(p)[0] == 1234


def test_sparse_bit(mod, monkeypatch):
    monkeypatch.setattr(
        mod, "_stat", lambda p: SimpleNamespace(st_size=5, st_file_attributes=0x200)
    )
    assert mod.read_disk("x") == (5, True)
    monkeypatch.setattr(
        mod, "_stat", lambda p: SimpleNamespace(st_size=5, st_file_attributes=0)
    )
    assert mod.read_disk("x") == (5, False)
    monkeypatch.setattr(mod, "_stat", lambda p: SimpleNamespace(st_size=5))
    assert mod.read_disk("x") == (5, False)


def test_full_line_suggests_compact(mod, monkeypatch, tmp_path, capsys):
    windows(monkeypatch, mod, tmp_path)
    monkeypatch.setattr(mod, "read_disk", lambda p: (int(9.5 * G), False))
    calls = fake_run(monkeypatch, mod, full_responses(mod))
    assert mod.main([]) == 0
    out = capsys.readouterr().out.strip()
    assert out == (
        "docker disk: file 9.5 GiB, used 3.2 GiB, docker 1.6 GiB, sparse no"
        " -> not sparse; compact suggested (/docker-compact)"
    )
    assert calls == [mod.DISTRO_CMD, mod.DF_CMD, mod.DOCKER_CMD]


def test_parse_docker_total_units(mod):
    text = DOCKER.decode()
    base = 1_200_000_000 + 212 + 500_000_000 + 45_500
    assert mod.parse_docker_total(text) == base
    tb = text.replace("1.2GB     800MB", "2.5TB     800MB")
    assert mod.parse_docker_total(tb) == 2_500_000_000_000 + 212 + 500_000_000 + 45_500


def test_docker_total_unparseable(mod):
    text = DOCKER.decode()
    assert mod.parse_docker_total(text.replace("1.2GB", "1.2PB")) is None
    no_cache = "".join(
        line for line in text.splitlines(True) if not line.startswith("Build Cache")
    )
    assert mod.parse_docker_total(no_cache) is None
    assert mod.parse_docker_total("") is None


def test_df_used(mod):
    assert mod.parse_df_used(DF.decode()) == 3435973837


def test_df_used_bad_output(mod):
    assert mod.parse_df_used("") is None
    assert mod.parse_df_used(DF.decode().splitlines()[0] + "\n") is None
    assert mod.parse_df_used(DF.decode().replace("3435973837", "abc")) is None


def test_running_distros_variants(mod):
    bom = b"\xff\xfe" + "docker-desktop\r\nUbuntu\r\n".encode("utf-16-le")
    assert "docker-desktop" in mod.running_distros(bom)
    assert "docker-desktop" in mod.running_distros(b"docker-desktop\nUbuntu\n")
    assert "docker-desktop" not in mod.running_distros(b"docker-desktop-data\n")


def test_distro_not_running_skips_df(mod, monkeypatch, tmp_path, capsys):
    windows(monkeypatch, mod, tmp_path)
    monkeypatch.setattr(mod, "read_disk", lambda p: (40 * G, True))
    responses = full_responses(mod)
    responses[tuple(mod.DISTRO_CMD)] = (0, "Ubuntu\r\n".encode("utf-16-le"))
    calls = fake_run(monkeypatch, mod, responses)
    assert mod.main([]) == 0
    out = capsys.readouterr().out
    assert calls == [mod.DISTRO_CMD, mod.DOCKER_CMD]
    assert "used ?" in out
    assert "compact suggested" not in out


@pytest.mark.parametrize(
    "response",
    [
        FileNotFoundError(),
        (1, b""),
        subprocess.TimeoutExpired(["docker", "system", "df"], 15),
    ],
)
def test_docker_missing_down_timeout(mod, monkeypatch, tmp_path, capsys, response):
    windows(monkeypatch, mod, tmp_path)
    monkeypatch.setattr(mod, "read_disk", lambda p: (int(9.5 * G), True))
    responses = full_responses(mod)
    responses[tuple(mod.DOCKER_CMD)] = response
    fake_run(monkeypatch, mod, responses)
    assert mod.main([]) == 0
    assert "docker ?" in capsys.readouterr().out


def test_oserror_is_unknown(mod, monkeypatch, tmp_path, capsys):
    windows(monkeypatch, mod, tmp_path)
    monkeypatch.setattr(mod, "read_disk", lambda p: (int(9.5 * G), True))
    responses = full_responses(mod)
    responses[tuple(mod.DISTRO_CMD)] = OSError("boom")
    fake_run(monkeypatch, mod, responses)
    assert mod.main([]) == 0
    assert "used ?" in capsys.readouterr().out


def test_only_allowed_commands(mod, monkeypatch, tmp_path, capsys):
    windows(monkeypatch, mod, tmp_path)
    monkeypatch.setattr(mod, "read_disk", lambda p: (int(9.5 * G), False))
    calls = []
    scenarios = [
        full_responses(mod),
        {**full_responses(mod), tuple(mod.DISTRO_CMD): (0, b"Ubuntu\n")},
        {**full_responses(mod), tuple(mod.DOCKER_CMD): FileNotFoundError()},
        {**full_responses(mod), tuple(mod.DOCKER_CMD): (1, b"")},
        {
            **full_responses(mod),
            tuple(mod.DOCKER_CMD): subprocess.TimeoutExpired(mod.DOCKER_CMD, 15),
        },
        {**full_responses(mod), tuple(mod.DISTRO_CMD): OSError("boom")},
    ]
    for responses in scenarios:
        fake_run(monkeypatch, mod, responses, calls)
        assert mod.main([]) == 0
        fake_run(monkeypatch, mod, responses, calls)
        assert mod.main(["--path"]) == 0
    allowed = [mod.DISTRO_CMD, mod.DF_CMD, mod.DOCKER_CMD]
    assert calls
    assert all(cmd in allowed for cmd in calls)


def test_threshold_edges(mod):
    v = mod.verdict
    assert v(int(9.5 * G), int(3.2 * G), True) == "compact suggested (/docker-compact)"
    assert v(4 * G, 2 * G, True) == "ok"
    assert v(3 * G, int(1.9 * G), True) == "ok"
    assert v(9 * G, 6 * G, True) == "ok"
    assert v(40 * G, None, True) == "ok"
    assert v(G, G, False) == "not sparse"


def test_status_line_sparse_yes_no(mod):
    assert mod.status_line(int(9.5 * G), int(3.2 * G), None, True) == (
        "docker disk: file 9.5 GiB, used 3.2 GiB, docker ?, sparse yes"
        " -> compact suggested (/docker-compact)"
    )
    assert "sparse no -> not sparse; " in mod.status_line(
        int(9.5 * G), int(3.2 * G), None, False
    )


def test_gib_and_unknown(mod):
    assert mod.gib(int(9.5 * G)) == "9.5 GiB" and mod.gib(None) == "?"


def test_path_flag(mod, monkeypatch, tmp_path, capsys):
    path = windows(monkeypatch, mod, tmp_path)
    calls = fake_run(monkeypatch, mod, {})
    assert mod.main(["--path"]) == 0
    assert capsys.readouterr().out.strip() == str(path)
    assert calls == []

    path.unlink()
    assert mod.main(["--path"]) == 0
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(mod.sys, "platform", "linux")
    assert mod.main(["--path"]) == 0
    assert capsys.readouterr().out == ""
