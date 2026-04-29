import os
from pathlib import Path

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


def is_pid_running(pid: int, *, os_name: str | None = None) -> bool:
    platform_name = os_name if os_name is not None else os.name
    if platform_name == "nt":
        # os.kill(pid, 0) is not consistently reliable across Windows shells.
        # Use OpenProcess/GetExitCodeProcess to check liveness.
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259

            kernel32 = ctypes.windll.kernel32
            OpenProcess = kernel32.OpenProcess
            OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            OpenProcess.restype = wintypes.HANDLE
            GetExitCodeProcess = kernel32.GetExitCodeProcess
            GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            GetExitCodeProcess.restype = wintypes.BOOL
            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                if not GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return int(exit_code.value) == STILL_ACTIVE
            finally:
                CloseHandle(handle)
        except Exception:
            return False

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
