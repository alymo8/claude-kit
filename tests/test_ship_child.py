import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from helpers import PLUGIN, clean_env, load_module, run_script


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


def test_stop_rule_handoff_not_utf8(mod, tmp_path):
    handoffs = tmp_path / ".claude" / "handoffs"
    handoffs.mkdir(parents=True)
    (handoffs / "feat_demo.md").write_bytes(b"- **Written:** \xff\xfe by /handoff\n")
    assert mod.stop_rule_handoff(tmp_path, "demo") is False


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
        "tail",
        f"--pid={os.getpid()}",
        "-f",
        "/dev/null",
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


class InterruptedProc:
    pid = 4343

    def __init__(self):
        self.waits = []

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if len(self.waits) == 1:
            raise KeyboardInterrupt
        return 0

    def kill(self):
        pass


def test_run_attempt_interrupt_kills_tree(mod, monkeypatch, tmp_path):
    proc = InterruptedProc()
    monkeypatch.setattr(mod.subprocess, "Popen", lambda cmd, **kw: proc)
    killed = []
    monkeypatch.setattr(mod, "_kill_tree", killed.append)
    with pytest.raises(KeyboardInterrupt):
        mod.run_attempt("claude", "s.md", tmp_path, tmp_path / "o", tmp_path / "e", 5)
    assert killed == [proc]
    assert len(proc.waits) == 2  # reaped after the kill


def test_run_attempt_cannot_start(mod, tmp_path):
    entry = mod.run_attempt(
        sys.executable,
        "s.md",
        tmp_path / "missing",
        tmp_path / "o.json",
        tmp_path / "o.err",
        5,
    )
    assert entry["exit"] == 127
    assert entry["timed_out"] is False
    assert entry["cost"] is None


def test_worktrees_git_failure_is_none(mod, tmp_path):
    assert mod._worktrees("git", tmp_path / "missing") is None


def test_decide_resume_without_worktree_list(mod, tmp_path):
    first = {"timed_out": False}
    args = SimpleNamespace(main=tmp_path, spec="s.md")
    (tmp_path / "s.md").write_text("x", encoding="utf-8")
    assert mod.decide_resume(first, False, None, "", args, "s") == (
        "no worktree",
        None,
    )
    assert mod.decide_resume(first, False, "", None, args, "s") == (
        "no worktree",
        None,
    )


# --- Task 2: the runner end to end, with fake claude and gh ---------------

SHIP_CHILD = PLUGIN / "scripts" / "ship-child.py"
WIN = sys.platform == "win32"

FAKE_CLAUDE = r"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

fake = Path(os.environ["FAKE_DIR"])
cfg = json.loads((fake / "claude.json").read_text(encoding="utf-8"))
calls = fake / "calls.jsonl"
done = calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []
call = {
    "argv": sys.argv[1:],
    "cwd": os.getcwd(),
    "env": os.environ.get("CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS"),
}
with calls.open("a", encoding="utf-8") as f:
    f.write(json.dumps(call) + "\n")
attempt = cfg["attempts"][len(done)]
main = cfg["main"]
wt = fake / "wt"
if attempt.get("worktree"):
    subprocess.run(
        ["git", "-C", main, "worktree", "add", str(wt), "-b", "feat/demo"],
        check=True,
        capture_output=True,
    )
if "handoff" in attempt:
    handoff = wt / ".claude" / "handoffs" / "feat_demo.md"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(attempt["handoff"], encoding="utf-8")
if attempt.get("remove_worktree"):
    shutil.rmtree(wt)
if attempt.get("delete_spec"):
    (Path(main) / cfg["rel"]).unlink()
if attempt.get("grandchild"):
    kid = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    (fake / "grandchild.pid").write_text(str(kid.pid), encoding="utf-8")
    (fake / "child.pid").write_text(str(os.getpid()), encoding="utf-8")
if attempt.get("stubborn"):
    ready = fake / "grandchild.pid"
    code = (
        "import os, signal, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
        "time.sleep(60)\n"
    )
    subprocess.Popen([sys.executable, "-c", code, str(ready)])
    while not ready.exists():
        time.sleep(0.05)
if "sleep" in attempt:
    time.sleep(attempt["sleep"])
sys.stdout.write(attempt.get("stdout", ""))
sys.stderr.write(attempt.get("stderr", ""))
sys.exit(attempt.get("exit", 0))
"""

FAKE_GH = r"""
import json
import os
import sys
from pathlib import Path

fake = Path(os.environ["FAKE_DIR"])
cfg = json.loads((fake / "gh.json").read_text(encoding="utf-8"))
call = {"argv": sys.argv[1:], "cwd": os.getcwd()}
with (fake / "gh_calls.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(call) + "\n")
sys.stdout.write(cfg["stdout"])
sys.exit(cfg["exit"])
"""


def git(*args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        check=True,
        capture_output=True,
    )


def install_fake(fake: Path, bin_dir: Path, name: str, source: str) -> None:
    script = fake / f"{name}.py"
    script.write_text(source, encoding="utf-8")
    if WIN:
        launcher = bin_dir / f"{name}.cmd"
        launcher.write_text(f'@"{sys.executable}" "{script}" %*\r\n')
    else:
        launcher = bin_dir / name
        launcher.write_text(f"#!{sys.executable}\n{source}", encoding="utf-8")
        launcher.chmod(0o755)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


class Rig:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.main = tmp_path / "main checkout"
        self.rel = "docs/superpowers/specs/2026-11-18-demo-design.md"
        spec = self.main / self.rel
        spec.parent.mkdir(parents=True)
        git("init", "-b", "main", str(self.main))
        spec.write_text("# Demo\n", encoding="utf-8")
        git("-C", str(self.main), "add", ".")
        git("-C", str(self.main), "commit", "-m", "spec")
        self.fake = tmp_path / "fake"
        self.bin = tmp_path / "bin"
        self.fake.mkdir()
        self.bin.mkdir()
        install_fake(self.fake, self.bin, "claude", FAKE_CLAUDE)
        install_fake(self.fake, self.bin, "gh", FAKE_GH)
        path = str(self.bin) + os.pathsep + os.environ["PATH"]
        self.env = clean_env(PATH=path, FAKE_DIR=str(self.fake))
        self.log = tmp_path / "logs"

    def run(self, attempts, *extra, gh=None, log=None):
        cfg = {"main": str(self.main), "rel": self.rel, "attempts": attempts}
        (self.fake / "claude.json").write_text(json.dumps(cfg), encoding="utf-8")
        gh_cfg = gh or {"exit": 0, "stdout": "[]"}
        (self.fake / "gh.json").write_text(json.dumps(gh_cfg), encoding="utf-8")
        self.log = log or self.tmp / "logs"
        proc = run_script(
            SHIP_CHILD,
            "--spec",
            self.rel,
            "--main",
            str(self.main),
            "--log",
            str(self.log),
            "--name",
            "demo",
            "--resume-wait",
            "0",
            *extra,
            env=self.env,
        )
        status_file = self.log / "demo.status.json"
        status = None
        if status_file.exists():
            status = json.loads(status_file.read_text(encoding="utf-8"))
        return proc, status

    def start(self, attempts, *extra) -> subprocess.Popen:
        """Start the runner without waiting for it."""
        cfg = {"main": str(self.main), "rel": self.rel, "attempts": attempts}
        (self.fake / "claude.json").write_text(json.dumps(cfg), encoding="utf-8")
        gh_cfg = {"exit": 0, "stdout": "[]"}
        (self.fake / "gh.json").write_text(json.dumps(gh_cfg), encoding="utf-8")
        cmd = [sys.executable, str(SHIP_CHILD), "--spec", self.rel]
        cmd += ["--main", str(self.main), "--log", str(self.log)]
        cmd += ["--name", "demo", "--resume-wait", "0", *extra]
        return subprocess.Popen(
            cmd,
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @property
    def calls(self) -> list[dict]:
        return read_jsonl(self.fake / "calls.jsonl")

    @property
    def gh_calls(self) -> list[dict]:
        return read_jsonl(self.fake / "gh_calls.jsonl")


@pytest.fixture
def rig(tmp_path):
    return Rig(tmp_path)


def alive(pid: int) -> bool:
    if WIN:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
        ).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def gone_within(pid: int, seconds: float = 5) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not alive(pid):
            return True
        time.sleep(0.2)
    return not alive(pid)


MERGED_LATER = {
    "exit": 0,
    "stdout": '[{"number": 7, "createdAt": "2999-01-01T00:00:00Z"}]',
}


def test_child_command_env_and_logs(rig, tmp_path):
    log = tmp_path / "new" / "logs"
    attempt = {"exit": 0, "stdout": '{"total_cost_usd": 1}', "stderr": "warn"}
    proc, status = rig.run([attempt], gh=MERGED_LATER, log=log)
    assert proc.returncode == 0, proc.stderr
    calls = rig.calls
    assert calls[0]["argv"] == [
        "-p",
        f"/agent-kit:ship {rig.rel}",
        "--permission-mode",
        "auto",
        "--permission-prompts",
        "none",
        "--output-format",
        "json",
    ]
    assert calls[0]["env"] == "0"
    assert os.path.samefile(calls[0]["cwd"], rig.main)
    assert (log / "demo.json").read_text(encoding="utf-8") == attempt["stdout"]
    assert (log / "demo.err").read_text(encoding="utf-8") == "warn"
    assert status["resume"] == "merged"
    assert len(status["attempts"]) == 1
    assert status["exit"] == 0
    gh_call = rig.gh_calls[0]
    assert gh_call["argv"] == [
        "pr",
        "list",
        "--head",
        "feat/demo",
        "--state",
        "merged",
        "--json",
        "number,createdAt",
    ]
    assert os.path.samefile(gh_call["cwd"], rig.main)


def test_timeout_kills_tree(rig):
    started = time.monotonic()
    proc, status = rig.run([{"grandchild": True, "sleep": 60}], "--timeout", "2")
    elapsed = time.monotonic() - started
    assert elapsed < 30
    assert proc.returncode == 124, proc.stderr
    child = int((rig.fake / "child.pid").read_text(encoding="utf-8"))
    grandchild = int((rig.fake / "grandchild.pid").read_text(encoding="utf-8"))
    assert gone_within(child)
    assert gone_within(grandchild)
    assert status["timed_out"] is True
    assert status["exit"] == 124
    assert status["resume"] == "timed out"
    assert len(status["attempts"]) == 1
    assert len(rig.calls) == 1


def test_timeout_kills_grandchild_ignoring_sigterm(rig):
    proc, status = rig.run([{"stubborn": True, "sleep": 60}], "--timeout", "2")
    assert proc.returncode == 124, proc.stderr
    grandchild = int((rig.fake / "grandchild.pid").read_text(encoding="utf-8"))
    assert gone_within(grandchild)
    assert status["timed_out"] is True


@pytest.mark.skipif(WIN, reason="POSIX signals")
@pytest.mark.parametrize("signame", ["SIGTERM", "SIGHUP"])
def test_runner_signal_kills_child_tree(rig, signame):
    runner = rig.start([{"grandchild": True, "sleep": 60}], "--timeout", "60")
    child_pid = rig.fake / "child.pid"
    deadline = time.monotonic() + 20
    while not child_pid.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert child_pid.exists()
    runner.send_signal(getattr(signal, signame))
    try:
        assert runner.wait(30) != 0
    finally:
        if runner.poll() is None:
            runner.kill()
    child = int(child_pid.read_text(encoding="utf-8"))
    grandchild = int((rig.fake / "grandchild.pid").read_text(encoding="utf-8"))
    assert gone_within(child)
    assert gone_within(grandchild)


def test_resume_cannot_start_records_127(rig):
    attempts = [{"exit": 1, "worktree": True, "remove_worktree": True}, {}]
    proc, status = rig.run(attempts)
    assert proc.returncode == 127, proc.stderr
    assert status["resume"] == "resumed"
    assert len(status["attempts"]) == 2
    assert status["attempts"][1]["exit"] == 127
    assert status["attempts"][1]["timed_out"] is False
    assert status["exit"] == 127
    assert len(rig.calls) == 1


def test_failure_resumes_once_in_worktree(rig):
    attempts = [
        {"exit": 1, "worktree": True, "stdout": '{"total_cost_usd": 1.5}'},
        {"exit": 0, "stdout": '{"total_cost_usd": 2.25}'},
    ]
    proc, status = rig.run(attempts)
    assert proc.returncode == 0, proc.stderr
    assert status["resume"] == "resumed"
    assert len(status["attempts"]) == 2
    assert os.path.samefile(status["attempts"][1]["cwd"], rig.fake / "wt")
    assert os.path.samefile(rig.calls[1]["cwd"], rig.fake / "wt")
    assert status["cost"] == 3.75
    assert status["exit"] == 0
    assert (rig.log / "demo.resume.json").exists()
    assert (rig.log / "demo.resume.err").exists()


def test_second_failure_not_resumed(rig):
    attempts = [{"exit": 1, "worktree": True}, {"exit": 1}, {"exit": 0}]
    proc, status = rig.run(attempts)
    assert len(rig.calls) == 2
    assert status["exit"] == 1
    assert proc.returncode == 1


def test_handoff_by_handoff_is_stop_rule(rig):
    handoff = "- **Written:** 2026-11-18T10:00 by /handoff\n"
    attempt = {"exit": 0, "worktree": True, "handoff": handoff}
    proc, status = rig.run([attempt, {"exit": 0}])
    assert status["resume"] == "stop rule"
    assert len(status["attempts"]) == 1


@pytest.mark.parametrize(
    "handoff",
    [
        "- **Written:** 2026-11-18T10:00 by session-end snapshot\n",
        "- **Written:** 2026-11-18T10:00 by session-end snapshot\n"
        "- **State refreshed:** 2026-11-18T11:00 by session-end snapshot\n",
    ],
)
def test_snapshot_handoff_does_not_block(rig, handoff):
    attempts = [{"exit": 1, "worktree": True, "handoff": handoff}, {"exit": 0}]
    proc, status = rig.run(attempts)
    assert status["resume"] == "resumed"
    assert len(status["attempts"]) == 2


def test_merged_before_start_does_not_count(rig):
    stdout = '[{"number": 1, "createdAt": "2000-01-01T00:00:00Z"}]'
    gh = {"exit": 0, "stdout": stdout}
    proc, status = rig.run([{"exit": 1, "worktree": True}, {"exit": 0}], gh=gh)
    assert status["resume"] == "resumed"


def test_gh_failure_blocks_resume(rig):
    gh = {"exit": 1, "stdout": ""}
    proc, status = rig.run([{"exit": 1, "worktree": True}, {"exit": 0}], gh=gh)
    assert status["resume"] == "gh failed"
    assert len(status["attempts"]) == 1


def test_gh_bad_json_is_gh_failed(rig):
    gh = {"exit": 0, "stdout": "warning: x"}
    proc, status = rig.run([{"exit": 1, "worktree": True}, {"exit": 0}], gh=gh)
    assert status["resume"] == "gh failed"
    assert len(status["attempts"]) == 1


def test_preexisting_worktree_blocks_resume(rig, tmp_path):
    old = str(tmp_path / "old")
    git("-C", str(rig.main), "worktree", "add", old, "-b", "feat/demo")
    proc, status = rig.run([{"exit": 1}, {"exit": 0}])
    assert status["resume"] == "no worktree"
    assert len(status["attempts"]) == 1


def test_no_worktree_resumes_in_main_checkout(rig):
    proc, status = rig.run([{"exit": 1}, {"exit": 0}])
    assert status["resume"] == "resumed"
    assert os.path.samefile(status["attempts"][1]["cwd"], rig.main)


def test_no_worktree_and_no_spec(rig):
    proc, status = rig.run([{"exit": 1, "delete_spec": True}, {"exit": 0}])
    assert status["resume"] == "no worktree"
    assert len(status["attempts"]) == 1


def test_non_json_stdout_cost_null(rig):
    proc, status = rig.run([{"exit": 0, "stdout": "oops"}], gh=MERGED_LATER)
    assert status["attempts"][0]["cost"] is None
    assert status["cost"] is None


def test_missing_claude_exits_2(rig):
    proc, status = rig.run([{"exit": 0}], "--claude", "no-such-claude-xyz")
    assert proc.returncode == 2
    assert "no-such-claude-xyz" in proc.stderr
    assert status is None


def test_bad_usage_exits_2(rig, tmp_path):
    proc = run_script(SHIP_CHILD, "--main", str(rig.main), env=rig.env)
    assert proc.returncode == 2
    proc = run_script(
        SHIP_CHILD,
        "--spec",
        rig.rel,
        "--main",
        str(tmp_path / "missing"),
        "--log",
        str(tmp_path / "logs"),
        "--name",
        "demo",
        env=rig.env,
    )
    assert proc.returncode == 2
    assert not (tmp_path / "logs" / "demo.status.json").exists()


def test_status_records_keep_awake(rig):
    proc, status = rig.run([{"exit": 0}], gh=MERGED_LATER)
    assert isinstance(status["keep_awake"], bool)
    if WIN:
        assert status["keep_awake"] is True
