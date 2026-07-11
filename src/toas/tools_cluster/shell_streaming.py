from __future__ import annotations

import json
import os
import os as _os
import selectors
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from ..runtime.tool_stream_context import current_tool_stream_emitter


def _spawn_streaming_process(*, argv: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.Popen(
        argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=False,
        bufsize=0,
        env=merged_env,
    )


def _emit_stdout_chunk(
    *,
    chunk_b: bytes,
    chunks: list[bytes],
    chunks_lock: threading.Lock,
    tool_stream_emitter,
) -> None:
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
    if tool_stream_emitter is not None:
        tool_stream_emitter("tool_progress", {"text": chunk})
    else:
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
    if os.name == "nt" and hasattr(stream, "read"):
        _reader_event_loop_windows(
            stream=stream,
            stream_max_bytes=stream_max_bytes,
            stream_max_latency_s=stream_max_latency_s,
            emit_chunk=emit_chunk,
        )
        stream.close()
        return
    with _reader_selector(stream=stream) as (fd, sel):
        _reader_event_loop(
            proc=proc,
            fd=fd,
            sel=sel,
            stream_max_bytes=stream_max_bytes,
            stream_max_latency_s=stream_max_latency_s,
            emit_chunk=emit_chunk,
        )
    stream.close()


def _reader_event_loop_windows(
    *,
    stream,
    stream_max_bytes: int,
    stream_max_latency_s: float,
    emit_chunk,
) -> None:
    pending = bytearray()
    last_emit = time.monotonic()
    while True:
        # Windows pipe reads can block until a large requested size or EOF.
        # Read incrementally so tool output can advance and the worker can
        # converge promptly when the child exits.
        data = stream.read(1)
        if not data:
            break
        pending.extend(data)
        now = time.monotonic()
        last_emit = _flush_pending_if_needed(
            pending=pending,
            last_emit=last_emit,
            now=now,
            stream_max_bytes=stream_max_bytes,
            stream_max_latency_s=stream_max_latency_s,
            emit_chunk=emit_chunk,
        )
    if pending:
        emit_chunk(bytes(pending))


@contextmanager
def _reader_selector(*, stream):
    fd = stream.fileno()
    try:
        _os.set_blocking(fd, False)
    except Exception:
        pass
    sel = selectors.DefaultSelector()
    sel.register(fd, selectors.EVENT_READ)
    try:
        yield fd, sel
    finally:
        try:
            sel.unregister(fd)
        except Exception:
            pass
        sel.close()


def _reader_event_loop(
    *,
    proc: subprocess.Popen,
    fd: int,
    sel: selectors.BaseSelector,
    stream_max_bytes: int,
    stream_max_latency_s: float,
    emit_chunk,
) -> None:
    pending = bytearray()
    last_emit = time.monotonic()
    while True:
        events = _select_stream_events(sel=sel, stream_max_latency_s=stream_max_latency_s)
        now = time.monotonic()
        eof = _read_into_pending(fd=fd, events=events, pending=pending)
        if eof:
            if pending:
                emit_chunk(bytes(pending))
                pending.clear()
            break
        last_emit = _flush_pending_if_needed(
            pending=pending,
            last_emit=last_emit,
            now=now,
            stream_max_bytes=stream_max_bytes,
            stream_max_latency_s=stream_max_latency_s,
            emit_chunk=emit_chunk,
        )
        if _reader_should_exit(proc=proc, pending=pending, events=events):
            break


def _select_stream_events(*, sel: selectors.BaseSelector, stream_max_latency_s: float):
    return sel.select(timeout=stream_max_latency_s)


def _read_into_pending(*, fd: int, events, pending: bytearray) -> bool:
    """Read available data into pending buffer.

    Returns True if EOF was reached (read returned b"" on an active event),
    False otherwise.
    """
    if not events:
        return False
    try:
        data = _os.read(fd, 4096)
    except BlockingIOError:
        return False
    if not data:
        # Empty read on an active event = EOF; the fd is now exhausted.
        return True
    pending.extend(data)
    return False


def _flush_pending_if_needed(
    *,
    pending: bytearray,
    last_emit: float,
    now: float,
    stream_max_bytes: int,
    stream_max_latency_s: float,
    emit_chunk,
) -> float:
    should_flush = bool(
        pending
        and (
            b"\n" in pending
            or len(pending) >= stream_max_bytes
            or (now - last_emit) >= stream_max_latency_s
        )
    )
    if not should_flush:
        return last_emit
    chunk_b = bytes(pending)
    pending.clear()
    emit_chunk(chunk_b)
    return now


def _reader_should_exit(*, proc: subprocess.Popen, pending: bytearray, events) -> bool:
    return bool(proc.poll() is not None and not pending and not events)


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
    if os.name == "nt":
        _stream_debug(
            "shell_stream_reader_still_alive",
            {
                "platform": "windows",
                "pid": getattr(proc, "pid", None),
            },
        )
        return
    stream = proc.stdout
    if stream is None:
        return
    try:
        fd = stream.fileno()
    except Exception:
        return
    try:
        _os.set_blocking(fd, False)
    except Exception:
        return
    try:
        remainder = _os.read(fd, 65536)
    except BlockingIOError:
        return
    except Exception:
        return
    if not remainder:
        return
    remainder_b = remainder if isinstance(remainder, bytes) else remainder.encode("utf-8", errors="replace")
    emit_chunk(remainder_b)


def _completed_process(*, argv: list[str], returncode: int, chunks: list[bytes]) -> subprocess.CompletedProcess:
    stdout = b"".join(chunks).decode("utf-8", errors="replace")
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")


def _make_emit_chunk(*, chunks: list[bytes], chunks_lock: threading.Lock):
    tool_stream_emitter = current_tool_stream_emitter()

    def _emit(chunk_b: bytes) -> None:
        _emit_stdout_chunk(
            chunk_b=chunk_b,
            chunks=chunks,
            chunks_lock=chunks_lock,
            tool_stream_emitter=tool_stream_emitter,
        )

    return _emit


def _start_reader_thread(
    *,
    proc: subprocess.Popen,
    stream_max_bytes: int,
    stream_max_latency_s: float,
    emit_chunk,
) -> threading.Thread:
    reader = threading.Thread(
        target=lambda: _reader_thread_target(
            proc=proc,
            stream_max_bytes=stream_max_bytes,
            stream_max_latency_s=stream_max_latency_s,
            emit_chunk=emit_chunk,
        ),
        daemon=True,
    )
    reader.start()
    return reader


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
    emit_chunk = _make_emit_chunk(chunks=chunks, chunks_lock=chunks_lock)
    reader = _start_reader_thread(
        proc=proc,
        stream_max_bytes=stream_max_bytes,
        stream_max_latency_s=stream_max_latency_s,
        emit_chunk=emit_chunk,
    )
    returncode = _wait_for_process(proc=proc, timeout_s=timeout_s)
    _drain_if_reader_alive(proc=proc, reader=reader, emit_chunk=emit_chunk)
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
