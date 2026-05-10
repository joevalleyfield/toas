from __future__ import annotations

import json
import os
import os as _os
import selectors
import subprocess
import threading
import time
from pathlib import Path


def run_streaming_subprocess(
    *,
    argv: list[str],
    cwd: Path,
    timeout_s: int | None,
    env: dict[str, str],
) -> subprocess.CompletedProcess:
    stream_max_bytes = 512
    stream_max_latency_s = 0.12
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=False,
        bufsize=0,
        env=env,
    )
    chunks: list[bytes] = []
    chunks_lock = threading.Lock()

    def _emit_chunk(chunk_b: bytes) -> None:
        chunk = chunk_b.decode("utf-8", errors="replace")
        _stream_debug(
            "shell_stream_emit",
            {
                "chunk_len": len(chunk),
                "chunk_preview": chunk[:40],
            },
        )
        with chunks_lock:
            chunks.append(chunk_b)
        print(chunk, end="", flush=True)

    def _reader() -> None:
        stream = proc.stdout
        if stream is None:
            return
        fd = stream.fileno()
        try:
            _os.set_blocking(fd, False)
        except Exception:
            pass
        sel = selectors.DefaultSelector()
        sel.register(fd, selectors.EVENT_READ)
        pending = bytearray()
        last_emit = time.monotonic()
        try:
            while True:
                events = sel.select(timeout=stream_max_latency_s)
                now = time.monotonic()
                if events:
                    try:
                        data = _os.read(fd, 4096)
                    except BlockingIOError:
                        data = b""
                    if data:
                        pending.extend(data)
                should_flush = bool(
                    pending
                    and (
                        b"\n" in pending
                        or len(pending) >= stream_max_bytes
                        or (now - last_emit) >= stream_max_latency_s
                    )
                )
                if should_flush:
                    chunk_b = bytes(pending)
                    pending.clear()
                    last_emit = now
                    _emit_chunk(chunk_b)
                if proc.poll() is not None and not pending and not events:
                    break
            if pending:
                _emit_chunk(bytes(pending))
        finally:
            try:
                sel.unregister(fd)
            except Exception:
                pass
            sel.close()
            stream.close()

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()
    try:
        returncode = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.wait()
        raise RuntimeError(f"tool shell timed out after {timeout_s}s") from exc
    reader.join(timeout=1.0)
    if reader.is_alive():
        stream = proc.stdout
        if stream is not None:
            remainder = stream.read()
            if remainder:
                remainder_b = remainder if isinstance(remainder, bytes) else remainder.encode("utf-8", errors="replace")
                _emit_chunk(remainder_b)
    stdout = b"".join(chunks).decode("utf-8", errors="replace")
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")


def _stream_debug_enabled() -> bool:
    return os.environ.get("TOAS_DAEMON_STREAM_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _stream_debug(kind: str, payload: dict) -> None:
    if not _stream_debug_enabled():
        return
    path = os.environ.get("TOAS_DAEMON_STREAM_DEBUG_LOG", "").strip() or ".toas/stream-debug.jsonl"
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    row = {"kind": kind, "ts": time.time(), **payload}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
