from __future__ import annotations

import json
import os
import os as _os
import selectors
import subprocess
import threading
import time
from pathlib import Path


def _spawn_streaming_process(*, argv: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=False,
        bufsize=0,
        env=env,
    )


def _emit_stdout_chunk(*, chunk_b: bytes, chunks: list[bytes], chunks_lock: threading.Lock) -> None:
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


def _reader_thread_target(
    *,
    proc: subprocess.Popen,
    stream_max_bytes: int,
    stream_max_latency_s: float,
    emit_chunk,
) -> None:
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
                emit_chunk(chunk_b)
            if proc.poll() is not None and not pending and not events:
                break
    finally:
        try:
            sel.unregister(fd)
        except Exception:
            pass
        sel.close()
        stream.close()


def _wait_for_process(*, proc: subprocess.Popen, timeout_s: int | None) -> int:
    try:
        return proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.wait()
        raise RuntimeError(f"tool shell timed out after {timeout_s}s") from exc


def _drain_if_reader_alive(*, proc: subprocess.Popen, reader: threading.Thread, emit_chunk) -> None:
    reader.join(timeout=1.0)
    if not reader.is_alive():
        return
    stream = proc.stdout
    if stream is None:
        return
    remainder = stream.read()
    if not remainder:
        return
    remainder_b = remainder if isinstance(remainder, bytes) else remainder.encode("utf-8", errors="replace")
    emit_chunk(remainder_b)


def _completed_process(*, argv: list[str], returncode: int, chunks: list[bytes]) -> subprocess.CompletedProcess:
    stdout = b"".join(chunks).decode("utf-8", errors="replace")
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")


def run_streaming_subprocess(
    *,
    argv: list[str],
    cwd: Path,
    timeout_s: int | None,
    env: dict[str, str],
) -> subprocess.CompletedProcess:
    stream_max_bytes = 512
    stream_max_latency_s = 0.12
    proc = _spawn_streaming_process(argv=argv, cwd=cwd, env=env)
    chunks: list[bytes] = []
    chunks_lock = threading.Lock()

    def _emit_chunk(chunk_b: bytes) -> None:
        _emit_stdout_chunk(chunk_b=chunk_b, chunks=chunks, chunks_lock=chunks_lock)

    reader = threading.Thread(
        target=lambda: _reader_thread_target(
            proc=proc,
            stream_max_bytes=stream_max_bytes,
            stream_max_latency_s=stream_max_latency_s,
            emit_chunk=_emit_chunk,
        ),
        daemon=True,
    )
    reader.start()
    returncode = _wait_for_process(proc=proc, timeout_s=timeout_s)
    _drain_if_reader_alive(proc=proc, reader=reader, emit_chunk=_emit_chunk)
    return _completed_process(argv=argv, returncode=returncode, chunks=chunks)


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
