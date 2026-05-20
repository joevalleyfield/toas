from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def spawn_session_host(*, workdir: Path, owner_pid: int) -> int:
    cmd = [
        sys.executable,
        "-m",
        "toas.cli",
        "host",
        "serve",
        "--owner-pid",
        str(owner_pid),
    ]
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=str(workdir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=(os.name != "nt"),
    )
    return int(proc.pid)


def serve_session_host(*, owner_pid: int, sleep_s: float = 0.25) -> None:
    while True:
        try:
            os.kill(owner_pid, 0)
        except OSError:
            return
        time.sleep(sleep_s)

