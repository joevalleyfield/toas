"""Deadline-aware reads from subprocess pipes on Windows and POSIX."""

from __future__ import annotations

from queue import Empty, Queue
from threading import Thread
from typing import IO


class PipeReader:
    """One reader per pipe; its owning process must close the pipe at shutdown."""

    def __init__(self, stream: IO[bytes]):
        self._queue: Queue[bytes | OSError] = Queue()
        self._ended = False
        Thread(target=self._read, args=(stream,), daemon=True).start()

    def _read(self, stream: IO[bytes]) -> None:
        try:
            while chunk := stream.read(1):
                self._queue.put(chunk)
        except OSError as exc:
            self._queue.put(exc)
        self._queue.put(b"")

    def read(self, *, timeout_s: float) -> bytes | None:
        if self._ended:
            return b""
        try:
            item = self._queue.get(timeout=max(0.0, timeout_s))
        except Empty:
            return None
        if isinstance(item, OSError):
            self._ended = True
            raise item
        if item == b"":
            self._ended = True
        return item
