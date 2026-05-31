from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

ToolStreamEmitter = Callable[[str, dict], None]

_TOOL_STREAM_EMITTER: ContextVar[ToolStreamEmitter | None] = ContextVar(
    "TOAS_TOOL_STREAM_EMITTER",
    default=None,
)


def current_tool_stream_emitter() -> ToolStreamEmitter | None:
    return _TOOL_STREAM_EMITTER.get()


@contextmanager
def tool_stream_emitter(emitter: ToolStreamEmitter | None) -> Iterator[None]:
    token = _TOOL_STREAM_EMITTER.set(emitter)
    try:
        yield
    finally:
        _TOOL_STREAM_EMITTER.reset(token)


def emit_tool_progress_text(text: str) -> bool:
    if not text:
        return False
    emitter = current_tool_stream_emitter()
    if emitter is None:
        return False
    emitter("tool_progress", {"text": text})
    return True


def emit_tool_done(*, operation: str, ok: bool, status: str | None = None) -> bool:
    emitter = current_tool_stream_emitter()
    if emitter is None:
        return False
    payload: dict = {"operation": operation, "ok": ok}
    if status:
        payload["status"] = status
    emitter("tool_done", payload)
    return True
