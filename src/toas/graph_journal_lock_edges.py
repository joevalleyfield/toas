from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path

_LOCKS: dict[Path, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()
_LOCAL = threading.local()


def _lock_path(events_path: str | Path) -> Path:
    path = Path(events_path).resolve()
    return path.with_name(f".{path.name}.lock")


def _thread_depths() -> dict[Path, tuple[object, int]]:
    depths = getattr(_LOCAL, "depths", None)
    if depths is None:
        depths = {}
        _LOCAL.depths = depths
    return depths


def _process_lock(lock_file) -> None:
    if os.name == "nt":  # pragma: no cover - exercised on Windows
        import msvcrt  # pragma: no cover

        lock_file.seek(0)  # pragma: no cover
        lock_file.write(b"0")  # pragma: no cover
        lock_file.flush()  # pragma: no cover
        lock_file.seek(0)  # pragma: no cover
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)  # pragma: no cover
        return  # pragma: no cover
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)


def _release_process_lock(lock_file) -> None:
    if os.name == "nt":  # pragma: no cover - exercised on Windows
        import msvcrt  # pragma: no cover

        lock_file.seek(0)  # pragma: no cover
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)  # pragma: no cover
        return  # pragma: no cover
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def journal_write_lock(events_path: str | Path):
    """Serialize cooperating appenders and rollover for one event journal."""
    lock_path = _lock_path(events_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCKS_GUARD:
        thread_lock = _LOCKS.setdefault(lock_path, threading.RLock())

    thread_lock.acquire()
    depths = _thread_depths()
    held = depths.get(lock_path)
    if held is None:
        lock_file = lock_path.open("a+b")
        try:
            _process_lock(lock_file)
        except Exception:
            lock_file.close()
            thread_lock.release()
            raise
        depths[lock_path] = (lock_file, 1)
    else:
        lock_file, depth = held
        depths[lock_path] = (lock_file, depth + 1)

    try:
        yield
    finally:
        lock_file, depth = depths[lock_path]
        if depth == 1:
            try:
                _release_process_lock(lock_file)
            finally:
                lock_file.close()
                del depths[lock_path]
        else:
            depths[lock_path] = (lock_file, depth - 1)
        thread_lock.release()
