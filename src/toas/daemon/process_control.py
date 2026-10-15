from pathlib import Path

from ..runtime.process_liveness import is_pid_running as is_pid_running


def pid_path(*, cwd: Path | None = None) -> Path:
    base = cwd if cwd is not None else Path.cwd().resolve()
    return base / ".toas" / "toas.pid"


def vim_port_path(*, cwd: Path | None = None) -> Path:
    base = cwd if cwd is not None else Path.cwd().resolve()
    return base / ".toas" / "toas.vim-port"


def read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None
    return value if value > 0 else None
