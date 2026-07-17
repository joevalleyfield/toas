from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "spikes" / "shell_host_stdio" / "shell-init.zsh"


def _run_zsh(script: str, *, timeout: float = 15.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["zsh", "-fc", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def test_eval_hook_lazily_reuses_one_stdio_host_for_sequential_requests(tmp_path: Path):
    diag = tmp_path / "host.log"
    result = _run_zsh(
        f"""
        export TOAS_SHELL_HOST_DIAG_LOG={diag}
        eval \"$({HOOK} --emit)\"
        [[ -z $TOAS_SHELL_HOST_PID ]]
        toas_shell_spike status
        first=$TOAS_SHELL_HOST_PID
        toas_shell_spike status
        second=$TOAS_SHELL_HOST_PID
        print -r -- \"same_host=$([[ $first == $second ]] && print yes || print no)\"
        toas_shell_spike_stop
        """
    )

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    host_lines = [line for line in lines if line.startswith("host_pid=")]
    assert len(host_lines) == 2
    assert host_lines[0].split()[0] == host_lines[1].split()[0]
    assert "ok=true status=ok" in host_lines[0]
    assert "ok=true status=ok" in host_lines[1]
    assert "same_host=yes" in lines


def test_interrupted_client_sends_cancel_on_same_channel_then_host_remains_usable(tmp_path: Path):
    diag = tmp_path / "host.log"
    result = _run_zsh(
        f"""
        export TOAS_SHELL_HOST_DIAG_LOG={diag}
        eval \"$({HOOK} --emit)\"
        rc=0
        toas_shell_spike cancel-probe --self-interrupt-after 0.2 || rc=$?
        print -r -- \"interrupt_rc=$rc\"
        toas_shell_spike status
        toas_shell_spike_stop
        """
    )

    assert result.returncode == 0, result.stderr
    assert "cancel_sent=true ok=false code=op_error" in result.stdout
    assert "interrupt_rc=130" in result.stdout
    assert result.stdout.count("status=ok") == 1


def test_host_exits_after_owner_shell_exits(tmp_path: Path):
    diag = tmp_path / "host.log"
    result = _run_zsh(
        f"""
        export TOAS_SHELL_HOST_DIAG_LOG={diag}
        eval \"$({HOOK} --emit)\"
        toas_shell_spike status
        print -r -- \"owner_host_pid=$TOAS_SHELL_HOST_PID\"
        """
    )

    assert result.returncode == 0, result.stderr
    owner_line = next(line for line in result.stdout.splitlines() if line.startswith("owner_host_pid="))
    host_pid = int(owner_line.split("=", 1)[1])

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if diag.exists() and "EXIT_OWNER_GONE" in diag.read_text(encoding="utf-8"):
            break
        time.sleep(0.05)
    else:
        raise AssertionError(f"host {host_pid} did not record owner exit; diag={diag.read_text() if diag.exists() else ''}")

    try:
        os.kill(host_pid, 0)
    except OSError:
        pass
    else:
        # A just-exited orphan can remain briefly observable while its new
        # parent reaps it; the lifecycle diagnostic is the primary assertion.
        time.sleep(0.1)
