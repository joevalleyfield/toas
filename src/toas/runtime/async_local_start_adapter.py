from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ..graph import write_run_record
from .async_step_runtime_worker import (
    start_async_step as start_async_step_impl,
)
from .async_step_runtime_worker import (
    stream_process_output as stream_process_output_impl,
)
from .async_step_runtime_worker import (
    wait_for_process as wait_for_process_impl,
)
from .policy_edges import stream_flags_for_workdir


def normalize_workdir(path: str | os.PathLike[str]) -> str:
    path = str(path)
    if sys.platform == "win32":
        if match := re.match(r"/([a-zA-Z])/(.*)", path):
            return f"{match.group(1)}:/{match.group(2)}"
    return path


def events_path_for_workdir(workdir: str) -> str:
    return str(Path(workdir) / ".toas" / "events.jsonl")


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


def start_async_step_local(payload: dict) -> dict:
    return start_async_step_impl(
        payload=payload,
        normalize_workdir_fn=normalize_workdir,
        thinking_stream_enabled_fn=thinking_stream_enabled,
        prompt_progress_stream_enabled_fn=prompt_progress_stream_enabled,
        stream_process_output_fn=stream_process_output_impl,
        wait_for_process_fn=wait_for_process_impl,
        write_run_event_fn=write_run_event,
    )
