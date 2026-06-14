from __future__ import annotations

import os

from ..runtime import async_local_start_adapter
from ..runtime.local_request_ops import capture_stdout

__all__ = ["capture_stdout"]


def normalize_workdir(path: str | os.PathLike[str]) -> str:
    return async_local_start_adapter.normalize_workdir(path)


def events_path_for_workdir(workdir: str) -> str:
    return async_local_start_adapter.events_path_for_workdir(workdir)


def write_run_event(workdir: str, run_id: str, status: str, detail: str | None = None) -> None:
    async_local_start_adapter.write_run_event(workdir, run_id, status, detail)


def thinking_stream_enabled(workdir: str) -> bool:
    return async_local_start_adapter.thinking_stream_enabled(workdir)


def prompt_progress_stream_enabled(workdir: str) -> bool:
    return async_local_start_adapter.prompt_progress_stream_enabled(workdir)
