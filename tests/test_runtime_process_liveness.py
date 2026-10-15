from __future__ import annotations

import os
import subprocess
import sys

import pytest

from toas.runtime import process_liveness
from toas.runtime.session_host_process import _build_sync_host_io
from toas.runtime.session_host_state import process_alive


def test_windows_probe_uses_query_and_never_sends_a_signal(monkeypatch):
    monkeypatch.setattr(process_liveness.sys, "platform", "win32")
    seen = []
    monkeypatch.setattr(process_liveness.os, "kill", lambda *_: pytest.fail("destructive probe"))
    monkeypatch.setattr(process_liveness, "is_pid_running", lambda pid, **kw: seen.append((pid, kw)) or True)
    process_liveness.probe_process(123)
    assert seen == [(123, {"os_name": "nt"})]
    monkeypatch.setattr(process_liveness, "is_pid_running", lambda *a, **kw: False)
    with pytest.raises(ProcessLookupError):
        process_liveness.probe_process(123)


def test_posix_probe_preserves_permission_and_missing_errors(monkeypatch):
    monkeypatch.setattr(process_liveness.sys, "platform", "linux")
    seen = []
    monkeypatch.setattr(process_liveness.os, "kill", lambda *args: seen.append(args))
    process_liveness.probe_process(123)
    assert seen == [(123, 0)]
    for error in (PermissionError, ProcessLookupError):
        def fail(*_, error=error):
            raise error("probe")
        monkeypatch.setattr(process_liveness.os, "kill", fail)
        with pytest.raises(error):
            process_liveness.probe_process(123)


def test_real_owner_and_record_probes_leave_child_alive(monkeypatch):
    monkeypatch.delenv("TOAS_HOST_IGNORE_OWNER_CHECK", raising=False)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        io = _build_sync_host_io(owner_pid=child.pid, sleep_s=0.01)
        for _ in range(3):
            assert process_alive(child.pid)
            assert io.owner_alive_fn() == "ok"
        assert child.poll() is None
    finally:
        child.terminate()
        child.wait(timeout=5)
    assert not process_alive(child.pid)
    assert io.owner_alive_fn() is False
    assert process_alive(os.getpid())
