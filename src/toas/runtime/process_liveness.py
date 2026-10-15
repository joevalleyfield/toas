"""Non-destructive process existence probes for runtime ownership."""
from __future__ import annotations

import os
import sys
from typing import Any, cast


def probe_process(pid: int) -> None:
    if sys.platform == "win32":
        # Windows signal 0 is a console control event, not a liveness probe.
        if not is_pid_running(pid, os_name="nt"):
            raise ProcessLookupError(pid)
    else:
        os.kill(pid, 0)


def is_pid_running(pid: int, *, os_name: str | None = None) -> bool:
    platform_name = os_name if os_name is not None else os.name
    if platform_name == "nt":
        # Windows signal 0 can send a console control event.
        # Use OpenProcess/GetExitCodeProcess to check liveness.
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259

            kernel32 = cast(Any, ctypes).windll.kernel32
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
