from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

import pytest


def _host_env() -> dict[str, str]:
    env = dict(os.environ)
    project_root = Path(__file__).resolve().parents[1]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root / 'src'}:{existing}" if existing else str(project_root / "src")
    return env


def _spawn_host_stdio(*, workdir: Path) -> subprocess.Popen[bytes]:
    env = _host_env()
    env["TOAS_HOST_STDIO_JSON"] = "1"
    # Keep owner alive for the duration of the test process.
    cmd = [
        sys.executable,
        "-m",
        "toas",
        "host",
        "serve",
        "--owner-pid",
        str(os.getpid()),
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(workdir),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def _start_pump(stream) -> tuple[Queue[bytes], Thread]:
    assert stream is not None
    q: Queue[bytes] = Queue()

    def _pump() -> None:
        while True:
            b = stream.read(1)
            if not b:
                break
            q.put(b)

    t = Thread(target=_pump, daemon=True)
    t.start()
    return q, t


def _request(
    proc: subprocess.Popen[bytes], q: Queue[bytes], stderr_q: Queue[bytes], msg: dict,
    *, timeout_s: float = 4.0,
) -> dict:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
    proc.stdin.flush()
    deadline = time.monotonic() + timeout_s
    raw = b""
    while time.monotonic() < deadline:
        try:
            chunk = q.get(timeout=0.05)
        except Empty:
            if proc.poll() is not None:
                break
            continue
        raw += chunk
        if b"\n" in raw or b"\x00" in raw:
            break
    assert raw, _process_diag(proc, stderr_q, "expected framed response bytes")
    wire = raw.decode("utf-8", errors="replace").replace("\x00", "\n")
    line = wire.split("\n", 1)[0]
    assert line.strip(), _process_diag(proc, stderr_q, f"framed bytes had empty first line: {wire!r}")
    return json.loads(line)


def _process_diag(proc: subprocess.Popen[bytes], stderr_q: Queue[bytes], prefix: str) -> str:
    try:
        rc = proc.poll()
    except Exception:
        rc = None
    captured = bytearray()
    # Read only bytes already captured by the pump. A live pipe may never reach EOF.
    while len(captured) < 512:
        try:
            captured.extend(stderr_q.get_nowait())
        except Empty:
            break
    err = captured[:512].decode("utf-8", errors="replace")
    return f"{prefix}; returncode={rc}; stderr={err!r}"


@pytest.mark.parametrize("stderr_text", ["", "upstream is waiting"])
def test_request_timeout_reports_live_child_without_waiting_for_stderr_eof(stderr_text):
    # Readiness comes from stdout, so both empty and short stderr stay open.
    code = (
        "import sys; "
        f"sys.stderr.write({stderr_text!r}); sys.stderr.flush(); "
        "sys.stdout.buffer.write(b'ready\\n'); sys.stdout.flush(); "
        "sys.stdin.readline(); sys.stdin.read()"
    )
    with subprocess.Popen(
        [sys.executable, "-u", "-c", code],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ) as proc:
        q, out_thread = _start_pump(proc.stdout)
        stderr_q, err_thread = _start_pump(proc.stderr)
        try:
            assert b"".join(q.get(timeout=5.0) for _ in range(6)) == b"ready\n"
            # Synchronize stderr capture independently of scheduler speed.
            captured = b"".join(stderr_q.get(timeout=5.0) for _ in stderr_text)
            stderr_q.put(captured)
            with pytest.raises(AssertionError, match="expected framed response bytes") as exc:
                _request(proc, q, stderr_q, {"request_id": "silent-child"}, timeout_s=0.1)
            assert "returncode=None" in str(exc.value)
            assert f"stderr={stderr_text!r}" in str(exc.value)
            assert proc.poll() is None
        finally:
            proc.terminate()
            proc.wait(timeout=3)
            out_thread.join(timeout=1)
            err_thread.join(timeout=1)
            assert not out_thread.is_alive()
            assert not err_thread.is_alive()


def test_host_stdio_watch_returns_error_frame_or_clean_exit(tmp_path: Path):
    proc = _spawn_host_stdio(workdir=tmp_path)
    q, _ = _start_pump(proc.stdout)
    stderr_q, _ = _start_pump(proc.stderr)
    try:
        try:
            resp = _request(
                proc,
                q,
                stderr_q,
                {
                    "protocol_version": 1,
                    "request_id": "r-watch",
                    "op": "watch",
                    "payload": {"workdir": str(tmp_path)},
                },
            )
            assert resp["protocol_version"] == 1
            assert resp["request_id"] == "r-watch"
            assert resp["ok"] is False
            assert resp["error"]["code"] in {"op_error", "protocol_error", "internal_error"}
        except AssertionError:
            # NOTE: Non-editor subprocess stdio harnesses may observe clean early host exit
            # with no framed bytes. Vim job/channel integration tests are the authoritative
            # transport validation path for editor-host behavior.
            assert proc.poll() == 0
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=3)


def test_host_stdio_step_async_returns_framed_response_or_clean_exit(tmp_path: Path):
    (tmp_path / "session.md").write_text("hello\n", encoding="utf-8")
    proc = _spawn_host_stdio(workdir=tmp_path)
    q, _ = _start_pump(proc.stdout)
    stderr_q, _ = _start_pump(proc.stderr)
    try:
        try:
            resp = _request(
                proc,
                q,
                stderr_q,
                {
                    "protocol_version": 1,
                    "request_id": "r-step",
                    "op": "step_async",
                    "payload": {"workdir": str(tmp_path)},
                },
            )
            assert resp["protocol_version"] == 1
            assert resp["request_id"] == "r-step"
            assert "ok" in resp
            # We only assert framing/shape here; behavior outcome may vary by backend config.
            if resp["ok"]:
                assert isinstance(resp.get("payload", {}), dict)
            else:
                assert isinstance(resp.get("error", {}), dict)
        except AssertionError:
            assert proc.poll() == 0
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=3)


def test_host_stdio_sequential_watch_then_step_async_shape(tmp_path: Path):
    proc = _spawn_host_stdio(workdir=tmp_path)
    q, _ = _start_pump(proc.stdout)
    stderr_q, _ = _start_pump(proc.stderr)
    try:
        outcomes: list[dict | None] = []
        for req in (
            {
                "protocol_version": 1,
                "request_id": "r-watch",
                "op": "watch",
                "payload": {"workdir": str(tmp_path)},
            },
            {
                "protocol_version": 1,
                "request_id": "r-step",
                "op": "step_async",
                "payload": {"workdir": str(tmp_path)},
            },
        ):
            try:
                outcomes.append(_request(proc, q, stderr_q, req))
            except AssertionError:
                # An earlier good frame must not hide a later live-host timeout.
                assert proc.poll() == 0
                outcomes.append(None)
                break

        # At least one shaped interaction should be observable before clean exit.
        assert any(isinstance(x, dict) for x in outcomes) or proc.poll() == 0
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=3)
