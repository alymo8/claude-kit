import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module


@pytest.fixture(scope="module")
def mod():
    return load_module(PLUGIN / "scripts" / "ship-child.py", "ship_child")


def test_branch_slug(mod):
    name = "2026-11-15-user-config-audit-design.md"
    assert mod.branch_slug(name) == "user-config-audit"
    assert mod.branch_slug("docs/specs/2026-11-18-demo-design.md") == "demo"
    assert mod.branch_slug("notes.md") == "notes"


def test_worktree_on(mod):
    porcelain = (
        "worktree C:/r/main\nHEAD 1\nbranch refs/heads/main\n\n"
        "worktree C:/r/wt x\nHEAD 2\nbranch refs/heads/feat/demo\n\n"
        "worktree C:/r/d\nHEAD 3\ndetached\n"
    )
    assert mod.worktree_on(porcelain, "feat/demo") == Path("C:/r/wt x")
    assert mod.worktree_on(porcelain, "feat/other") is None


SNAPSHOT = "- **Written:** 2026-11-18T10:00 by session-end snapshot\n"
REFRESHED = "- **State refreshed:** 2026-11-18T11:00 by session-end snapshot\n"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("- **Written:** 2026-11-18T10:00 by /handoff\n", True),
        (SNAPSHOT, False),
        (SNAPSHOT + REFRESHED, False),
        (None, False),
    ],
)
def test_stop_rule_handoff(mod, tmp_path, text, expected):
    if text is not None:
        handoffs = tmp_path / ".claude" / "handoffs"
        handoffs.mkdir(parents=True)
        (handoffs / "feat_demo.md").write_text(text, encoding="utf-8")
    assert mod.stop_rule_handoff(tmp_path, "demo") is expected


def test_stop_rule_handoff_crlf(mod, tmp_path):
    handoffs = tmp_path / ".claude" / "handoffs"
    handoffs.mkdir(parents=True)
    (handoffs / "feat_demo.md").write_bytes(
        b"# Handoff\r\n- **Written:** 2026-11-18T10:00 by /handoff\r\n"
    )
    assert mod.stop_rule_handoff(tmp_path, "demo") is True


@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"total_cost_usd": 4.12}', 4.12),
        ("", None),
        ("not json", None),
        ("[1]", None),
        (None, None),
    ],
)
def test_read_cost(mod, tmp_path, text, expected):
    path = tmp_path / "child.json"
    if text is not None:
        path.write_text(text, encoding="utf-8")
    assert mod.read_cost(path) == expected


class FakeProc:
    def __init__(self, early_exit=None):
        self.pid = 4242
        self.early_exit = early_exit
        self.calls = []

    def wait(self, timeout=None):
        self.calls.append(("wait", timeout))
        if timeout == 1:
            if self.early_exit is not None:
                return self.early_exit
            raise subprocess.TimeoutExpired("fake", timeout)
        return 0

    def terminate(self):
        self.calls.append(("terminate",))

    def kill(self):
        self.calls.append(("kill",))


def patch_popen(monkeypatch, mod, proc=None, error=None, which="/usr/bin/x"):
    started = []

    def popen(cmd, **kwargs):
        started.append((cmd, kwargs))
        if error is not None:
            raise error
        return proc

    monkeypatch.setattr(mod.subprocess, "Popen", popen)
    monkeypatch.setattr(mod.shutil, "which", lambda name: which)
    return started


def test_keep_awake_darwin(mod, monkeypatch):
    proc = FakeProc()
    started = patch_popen(monkeypatch, mod, proc)
    k = mod.keep_awake("darwin")
    assert started[0][0] == ["caffeinate", "-i", "-w", str(os.getpid())]
    assert k.active is True
    k.release()
    assert ("terminate",) in proc.calls


def test_keep_awake_linux(mod, monkeypatch):
    proc = FakeProc()
    started = patch_popen(monkeypatch, mod, proc)
    k = mod.keep_awake("linux")
    cmd, kwargs = started[0]
    assert cmd == [
        "systemd-inhibit",
        "--what=sleep",
        "--mode=block",
        "sleep",
        "infinity",
    ]
    assert kwargs.get("start_new_session") is True
    assert k.active is True
    killed = []
    monkeypatch.setattr(
        mod.os, "killpg", lambda pid, sig: killed.append((pid, sig)), raising=False
    )
    k.release()
    assert killed == [(proc.pid, signal.SIGTERM)]


def test_keep_awake_linux_without_inhibit(mod, monkeypatch):
    started = patch_popen(monkeypatch, mod, FakeProc(), which=None)
    k = mod.keep_awake("linux")
    assert started == []
    assert k.active is False


def test_keep_awake_popen_fails(mod, monkeypatch):
    patch_popen(monkeypatch, mod, error=OSError("no such file"))
    assert mod.keep_awake("darwin").active is False


def test_keep_awake_exits_early(mod, monkeypatch):
    patch_popen(monkeypatch, mod, FakeProc(early_exit=1))
    assert mod.keep_awake("darwin").active is False


def test_keep_awake_other_platform(mod):
    assert mod.keep_awake("sunos").active is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_keep_awake_windows(mod):
    import ctypes

    es_continuous = 0x80000000
    es_system_required = 0x00000001
    set_state = ctypes.windll.kernel32.SetThreadExecutionState
    set_state.restype = ctypes.c_uint32
    k = mod.keep_awake("win32")
    try:
        assert k.active is True
        prev = set_state(es_continuous | es_system_required)
        assert prev & es_system_required
    finally:
        k.release()
    assert not set_state(es_continuous) & es_system_required
