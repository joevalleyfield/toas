from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster import shell_streaming


def test_stream_debug_enabled_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TOAS_DAEMON_STREAM_DEBUG", raising=False)
    assert shell_streaming._stream_debug_enabled() is False
    monkeypatch.setenv("TOAS_DAEMON_STREAM_DEBUG", "true")
    assert shell_streaming._stream_debug_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_STREAM_DEBUG", "ON")
    assert shell_streaming._stream_debug_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_STREAM_DEBUG", "0")
    assert shell_streaming._stream_debug_enabled() is False


def test_stream_debug_writes_default_log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_DAEMON_STREAM_DEBUG", "1")
    monkeypatch.delenv("TOAS_DAEMON_STREAM_DEBUG_LOG", raising=False)
    shell_streaming._stream_debug("probe", {"x": 1})
    log_path = tmp_path / ".toas" / "stream-debug.jsonl"
    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert '"kind": "probe"' in text
    assert '"x": 1' in text


def test_stream_debug_disabled_does_not_write_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TOAS_DAEMON_STREAM_DEBUG", raising=False)
    monkeypatch.delenv("TOAS_DAEMON_STREAM_DEBUG_LOG", raising=False)
    shell_streaming._stream_debug("probe", {"x": 1})
    assert not (tmp_path / ".toas" / "stream-debug.jsonl").exists()


def test_run_streaming_subprocess_collects_stdout(tmp_path: Path) -> None:
    completed = shell_streaming.run_streaming_subprocess(
        argv=["python3", "-c", "print('one'); print('two')"],
        cwd=tmp_path,
        timeout_s=5,
        env={},
    )
    assert completed.returncode == 0
    assert "one" in completed.stdout
    assert "two" in completed.stdout


def test_run_streaming_subprocess_timeout_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="timed out"):
        shell_streaming.run_streaming_subprocess(
            argv=["python3", "-c", "import time; time.sleep(0.3)"],
            cwd=tmp_path,
            timeout_s=0,
            env={},
        )


def test_run_streaming_subprocess_reader_alive_remainder_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeThread:
        def __init__(self, *, target, daemon):  # type: ignore[no-untyped-def]
            self._target = target
            self._daemon = daemon

        def start(self) -> None:
            return None

        def join(self, timeout=None) -> None:  # noqa: ARG002
            return None

        def is_alive(self) -> bool:
            return True

    class _FakeStream:
        def __init__(self) -> None:
            self._fd = 0

        def fileno(self) -> int:
            return self._fd

        def read(self) -> bytes:
            return b"tail-only"

        def close(self) -> None:
            return None

    class _FakeProc:
        def __init__(self) -> None:
            self.stdout = _FakeStream()
            self.returncode = 0

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

        def kill(self) -> None:
            return None

    def _fake_popen(*args, **kwargs):  # noqa: ARG001
        return _FakeProc()

    monkeypatch.setattr(shell_streaming.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(shell_streaming.threading, "Thread", _FakeThread)
    monkeypatch.setattr(shell_streaming._os, "set_blocking", lambda *a, **k: None)

    completed = shell_streaming.run_streaming_subprocess(
        argv=["ignored"],
        cwd=tmp_path,
        timeout_s=1,
        env={},
    )
    assert completed.returncode == 0
    assert "tail-only" in completed.stdout


def test_run_streaming_subprocess_reader_handles_none_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeThread:
        def __init__(self, *, target, daemon):  # type: ignore[no-untyped-def]
            self._target = target

        def start(self) -> None:
            self._target()

        def join(self, timeout=None) -> None:  # noqa: ARG002
            return None

        def is_alive(self) -> bool:
            return False

    class _FakeProc:
        def __init__(self) -> None:
            self.stdout = None

        def wait(self, timeout=None):  # noqa: ARG002
            return 0

    monkeypatch.setattr(shell_streaming.subprocess, "Popen", lambda *a, **k: _FakeProc())
    monkeypatch.setattr(shell_streaming.threading, "Thread", _FakeThread)
    completed = shell_streaming.run_streaming_subprocess(
        argv=["ignored"],
        cwd=tmp_path,
        timeout_s=1,
        env={},
    )
    assert completed.returncode == 0
    assert completed.stdout == ""


def test_reader_stdout_uses_windows_reader_path(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[bytes] = []

    class _Stream:
        def __init__(self) -> None:
            self._chunks = [b"ab", b"cd", b""]
            self.closed = False

        def read(self, _size):
            return self._chunks.pop(0)

        def close(self) -> None:
            self.closed = True

    stream = _Stream()
    proc = type("_Proc", (), {"stdout": stream})()
    monkeypatch.setattr(shell_streaming.os, "name", "nt")
    shell_streaming._reader_thread_target(
        proc=proc,
        stream_max_bytes=99,
        stream_max_latency_s=999,
        emit_chunk=emitted.append,
    )
    assert emitted == [b"abcd"]
    assert stream.closed is True


def test_drain_if_reader_alive_handles_none_stdout() -> None:
    class _AliveReader:
        def join(self, timeout=None) -> None:  # noqa: ARG002
            return None

        def is_alive(self) -> bool:
            return True

    class _NoStdoutProc:
        stdout = None

    emitted: list[bytes] = []
    shell_streaming._drain_if_reader_alive(
        proc=_NoStdoutProc(),
        reader=_AliveReader(),
        emit_chunk=lambda chunk: emitted.append(chunk),
    )
    assert emitted == []


def test_run_streaming_subprocess_reader_tolerates_streaming_exceptions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeThread:
        def __init__(self, *, target, daemon):  # type: ignore[no-untyped-def]
            self._target = target

        def start(self) -> None:
            self._target()

        def join(self, timeout=None) -> None:  # noqa: ARG002
            return None

        def is_alive(self) -> bool:
            return False

    class _FakeStream:
        def fileno(self) -> int:
            return 7

        def close(self) -> None:
            return None

    class _FakeProc:
        def __init__(self) -> None:
            self.stdout = _FakeStream()

        def wait(self, timeout=None):  # noqa: ARG002
            return 0

        def poll(self):
            return 0

    class _FakeSelector:
        def __init__(self) -> None:
            self._calls = 0

        def register(self, fd, event):  # noqa: ARG002
            return None

        def select(self, timeout=None):  # noqa: ARG002
            self._calls += 1
            if self._calls == 1:
                return [object()]
            return []

        def unregister(self, fd):  # noqa: ARG002
            raise RuntimeError("unregister failure")

        def close(self) -> None:
            return None

    monkeypatch.setattr(shell_streaming.subprocess, "Popen", lambda *a, **k: _FakeProc())
    monkeypatch.setattr(shell_streaming.threading, "Thread", _FakeThread)
    monkeypatch.setattr(shell_streaming.selectors, "DefaultSelector", _FakeSelector)
    monkeypatch.setattr(shell_streaming._os, "set_blocking", lambda *a, **k: (_ for _ in ()).throw(OSError("nope")))
    monkeypatch.setattr(shell_streaming._os, "read", lambda *a, **k: (_ for _ in ()).throw(BlockingIOError()))
    completed = shell_streaming.run_streaming_subprocess(
        argv=["ignored"],
        cwd=tmp_path,
        timeout_s=1,
        env={},
    )
    assert completed.returncode == 0
    assert completed.stdout == ""


def test_read_into_pending_appends_data_with_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    pending = bytearray()
    monkeypatch.setattr(shell_streaming._os, "read", lambda _fd, _n: b"abc")
    shell_streaming._read_into_pending(fd=7, events=[object()], pending=pending)
    assert pending == b"abc"


def test_read_into_pending_blocking_io_is_not_eof(monkeypatch: pytest.MonkeyPatch) -> None:
    pending = bytearray()
    monkeypatch.setattr(shell_streaming._os, "read", lambda _fd, _n: (_ for _ in ()).throw(BlockingIOError()))
    eof = shell_streaming._read_into_pending(fd=7, events=[object()], pending=pending)
    assert eof is False
    assert pending == b""


def test_reader_event_loop_flushes_pending_on_eof(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[bytes] = []
    reads = [b"tail", b""]

    class _Proc:
        def poll(self):
            return None

    monkeypatch.setattr(shell_streaming, "_select_stream_events", lambda **_kwargs: [object()])
    monkeypatch.setattr(shell_streaming._os, "read", lambda _fd, _n: reads.pop(0))
    shell_streaming._reader_event_loop(
        proc=_Proc(),
        fd=7,
        sel=object(),
        stream_max_bytes=99,
        stream_max_latency_s=999,
        emit_chunk=emitted.append,
    )
    assert emitted == [b"tail"]


def test_drain_if_reader_alive_ignores_empty_remainder() -> None:
    class _AliveReader:
        def join(self, timeout=None) -> None:  # noqa: ARG002
            return None

        def is_alive(self) -> bool:
            return True

    class _Stream:
        def read(self):
            return b""

    class _Proc:
        stdout = _Stream()

    emitted: list[bytes] = []
    shell_streaming._drain_if_reader_alive(proc=_Proc(), reader=_AliveReader(), emit_chunk=lambda b: emitted.append(b))
    assert emitted == []
