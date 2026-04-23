from __future__ import annotations

import io
import os
import re
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

from ..graph import write_run_record
from ..runtime.policy_edges import stream_flags_for_workdir


def capture_stdout(fn, *args, **kwargs) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        fn(*args, **kwargs)
    return buffer.getvalue()


def debug_log(message: str) -> None:
    path = os.environ.get("TOAS_RPC_DEBUG_LOG", "").strip()
    if not path:
        return
    try:
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(message + "\n")
    except OSError:
        pass


def normalize_workdir(path: str) -> str:
    if sys.platform == "win32":
        if match := re.match(r"/([a-zA-Z])/(.*)", path):
            return f"{match.group(1)}:/{match.group(2)}"
    return path


def step_subprocess_command() -> list[str]:
    toas_cmd = shutil.which("toas")
    if toas_cmd:
        return [toas_cmd, "step"]
    return [sys.executable, "-m", "toas.cli", "step"]


def events_path_for_workdir(workdir: str) -> str:
    return str(Path(workdir) / "events.jsonl")


def write_run_event(workdir: str, run_id: str, status: str, detail: str | None = None) -> None:
    try:
        write_run_record(
            events_path_for_workdir(workdir),
            run_id=run_id,
            status=status,
            workdir=workdir,
            detail=detail,
        )
    except Exception:
        return


def thinking_stream_enabled(workdir: str) -> bool:
    thinking, _prompt_progress = stream_flags_for_workdir(workdir)
    return thinking


def prompt_progress_stream_enabled(workdir: str) -> bool:
    _thinking, prompt_progress = stream_flags_for_workdir(workdir)
    return prompt_progress
