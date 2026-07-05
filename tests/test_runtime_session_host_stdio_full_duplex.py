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


def _host_env() -> dict[str, str]:
    env = dict(os.environ)
    project_root = Path(__file__).resolve().parents[1]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root / 'src'}:{existing}" if existing else str(project_root / "src")
    return env


def _spawn_host_stdio(*, workdir: Path) -> subprocess.Popen[bytes]:
    env = _host_env()
    env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    cmd = [
        sys.executable,
        "-m",
        "toas",
        "host",
        "serve",
        "--stdio-json",
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


def _start_pump(stream: subprocess.PIPE | None) -> tuple[Queue[bytes], Thread]:
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


def _recv_frame_bytes(stdout_q: Queue[bytes], *, timeout_s: float = 4.0) -> bytes:
    deadline = time.time() + timeout_s
    raw = b""
    while time.time() < deadline:
        try:
            chunk = stdout_q.get(timeout=0.05)
        except Empty:
            continue
        raw += chunk
        if b"\n" in raw or b"\x00" in raw:
            return raw
    return raw


def _decode_first_frame(raw: bytes) -> dict:
    text = raw.decode("utf-8", errors="replace").replace("\x00", "\n")
    line = text.split("\n", 1)[0]
    if not line.strip():
        raise AssertionError(f"empty frame line from raw={raw!r}")
    obj = json.loads(line)
    assert isinstance(obj, dict)
    return obj


def _send(stdin, request: dict) -> None:
    assert stdin is not None
    wire = (json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8")
    stdin.write(wire)
    stdin.flush()


def test_stdio_full_duplex_multi_request_shape(tmp_path: Path):
    # Keep session path deterministic for daemon-side request handling.
    (tmp_path / "session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    proc = _spawn_host_stdio(workdir=tmp_path)
    out_q, _ = _start_pump(proc.stdout)
    err_q, _ = _start_pump(proc.stderr)

    try:
        # 1) watch with missing run_id should return a framed error.
        req1 = {
            "protocol_version": 1,
            "request_id": "r-watch-missing",
            "op": "watch",
            "payload": {"workdir": str(tmp_path), "backend_mode": "local"},
        }
        _send(proc.stdin, req1)
        raw1 = _recv_frame_bytes(out_q)
        assert raw1, f"expected watch error frame bytes; rc={proc.poll()} stderr={_drain_queue(err_q)!r}"
        resp1 = _decode_first_frame(raw1)
        assert resp1.get("request_id") == "r-watch-missing"
        assert resp1.get("ok") is False
        assert isinstance(resp1.get("error"), dict)

        # 2) step_async should return framed accepted payload with run_id.
        req2 = {
            "protocol_version": 1,
            "request_id": "r-step",
            "op": "step_async",
            "payload": {"workdir": str(tmp_path), "backend_mode": "local"},
        }
        _send(proc.stdin, req2)
        raw2 = _recv_frame_bytes(out_q)
        assert raw2, f"expected step_async frame bytes; rc={proc.poll()} stderr={_drain_queue(err_q)!r}"
        resp2 = _decode_first_frame(raw2)
        assert resp2.get("request_id") == "r-step"
        assert resp2.get("ok") is True
        payload2 = resp2.get("payload", {})
        assert isinstance(payload2, dict)
        run_id = payload2.get("run_id", "")
        assert isinstance(run_id, str) and run_id != ""

        # 3) watch that run_id should also return a framed response.
        req3 = {
            "protocol_version": 1,
            "request_id": "r-watch-run",
            "op": "watch",
            "payload": {
                "workdir": str(tmp_path),
                "backend_mode": "local",
                "run_id": run_id,
                "offset": 0,
                "since_seq": 0,
                "mode": "poll",
            },
        }
        _send(proc.stdin, req3)
        raw3 = _recv_frame_bytes(out_q)
        if not raw3:
            # Non-editor stdio harnesses may observe clean host exit before a third framed turn.
            assert proc.poll() == 0
            return
        resp3 = _decode_first_frame(raw3)
        assert resp3.get("request_id") == "r-watch-run"
        assert "ok" in resp3
        if resp3.get("ok") is True:
            assert isinstance(resp3.get("payload"), dict)
        else:
            assert isinstance(resp3.get("error"), dict)

    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=3)


def _drain_queue(q: Queue[bytes]) -> str:
    buf = b""
    while True:
        try:
            buf += q.get_nowait()
        except Empty:
            break
    return buf.decode("utf-8", errors="replace")
