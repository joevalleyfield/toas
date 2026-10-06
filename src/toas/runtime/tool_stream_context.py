from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

ToolStreamEmitter = Callable[[str, dict], None]

_TOOL_STREAM_EMITTER: ContextVar[ToolStreamEmitter | None] = ContextVar(
    "TOAS_TOOL_STREAM_EMITTER",
    default=None,
)
_CURRENT_TOOL_DONE_EMITTED: ContextVar[bool] = ContextVar(
    "TOAS_CURRENT_TOOL_DONE_EMITTED",
    default=False,
)


def current_tool_stream_emitter() -> ToolStreamEmitter | None:
    return _TOOL_STREAM_EMITTER.get()


def is_tool_done_emitted() -> bool:
    if current_tool_stream_emitter() is None:
        return False
    return _CURRENT_TOOL_DONE_EMITTED.get()


@contextmanager
def tool_stream_emitter(emitter: ToolStreamEmitter | None) -> Iterator[None]:
    token = _TOOL_STREAM_EMITTER.set(emitter)
    done_token = _CURRENT_TOOL_DONE_EMITTED.set(False)
    try:
        yield
    finally:
        _TOOL_STREAM_EMITTER.reset(token)
        _CURRENT_TOOL_DONE_EMITTED.reset(done_token)


def emit_tool_start(
    *,
    operation: str,
    index: int | None = None,
    total: int | None = None,
) -> bool:
    emitter = current_tool_stream_emitter()
    if emitter is None:
        return False
    _CURRENT_TOOL_DONE_EMITTED.set(False)
    payload: dict[str, object] = {"operation": operation}
    if index is not None:
        payload["index"] = index
    if total is not None:
        payload["total"] = total
    emitter("tool_start", payload)
    return True


def emit_tool_progress_text(text: str) -> bool:
    if not text:
        return False
    emitter = current_tool_stream_emitter()
    if emitter is None:
        return False
    emitter("tool_progress", {"text": text})
    return True


def emit_tool_done(
    *,
    operation: str,
    ok: bool,
    status: str | None = None,
    index: int | None = None,
    total: int | None = None,
) -> bool:
    emitter = current_tool_stream_emitter()
    if emitter is None:
        return False
    _CURRENT_TOOL_DONE_EMITTED.set(True)
    payload: dict[str, object] = {"operation": operation, "ok": ok}
    if status:
        payload["status"] = status
    if index is not None:
        payload["index"] = index
    if total is not None:
        payload["total"] = total
    emitter("tool_done", payload)
    return True
