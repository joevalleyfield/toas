from __future__ import annotations

import threading

import pytest

from toas.runtime.request_handler_edges import (
    backend_lifecycle_unavailable,
    build_request_handler_parts,
)


class _CliStub:
    @staticmethod
    def run_heads():
        print("head")


def _parts(**overrides):
    defaults = {
        "cli_module": _CliStub,
        "process_state_lock": threading.Lock(),
        "capture_stdout_fn": lambda fn, *args, **kwargs: f"{fn.__name__}:{args}:{kwargs}",
    }
    defaults.update(overrides)
    return build_request_handler_parts(**defaults)


def test_backend_lifecycle_unavailable_is_explicit():
    with pytest.raises(RuntimeError, match="backend lifecycle is not available"):
        backend_lifecycle_unavailable({})


def test_default_handler_captures_cli_stdout_with_workdir_lock():
    parts = _parts()

    out = parts["default_handler"]({}, "heads")

    assert out == {"stdout": "run_heads:():{}"}


def test_stream_subscribe_forces_follow_mode_and_delegates_watch():
    calls = []

    def _watch(payload):
        calls.append(payload)
        return {"events": [], "mode": payload["mode"]}

    parts = _parts(watch_async_step_fn=_watch)

    out = parts["handle_stream_subscribe_fn"]({"run_id": "r1", "mode": "poll", "since_seq": 2})

    assert calls == [{"run_id": "r1", "mode": "follow", "since_seq": 2}]
    assert out["mode"] == "follow"


def test_step_async_threads_local_runtime_dependencies():
    calls = {}

    def _start(payload, **kwargs):
        calls["payload"] = payload
        calls["kwargs"] = kwargs
        return {"run_id": "r1", "status": "started"}

    callback_calls = []

    parts = _parts(
        start_async_step_fn=_start,
        normalize_workdir_fn=lambda value: f"norm:{value}",
        thinking_stream_enabled_fn=lambda: True,
        prompt_progress_stream_enabled_fn=lambda: False,
        write_run_event_fn=lambda *args: callback_calls.append(("write", args)),
        emit_tool_events_from_line_fn=lambda run, line, **kwargs: callback_calls.append(("emit", run, line, kwargs)),
        stream_process_output_fn=lambda run, **kwargs: callback_calls.append(("stream", run, kwargs)),
        wait_for_process_fn=lambda run, **kwargs: callback_calls.append(("wait", run, kwargs)),
    )

    out = parts["handle_step_async_fn"]({"workdir": "/tmp"})

    assert out == {"run_id": "r1", "status": "started"}
    assert calls["payload"] == {"workdir": "/tmp"}
    assert calls["kwargs"]["normalize_workdir_fn"]("/x") == "norm:/x"
    assert calls["kwargs"]["thinking_stream_enabled_fn"]() is True
    assert calls["kwargs"]["prompt_progress_stream_enabled_fn"]() is False
    calls["kwargs"]["stream_process_output_fn"]("run")
    emit_fn = callback_calls[-1][2]["emit_tool_events_from_line_fn"]
    emit_fn("run", "[OK] shell: done")
    calls["kwargs"]["wait_for_process_fn"]("run")
    write_fn = callback_calls[-1][2]["write_run_event_fn"]
    write_fn("/repo", "r1", "done", "detail")
    assert callback_calls[0][0] == "stream"
    assert callback_calls[1][0] == "emit"
    assert "prompt_progress_line_re" in callback_calls[1][3]
    assert "tool_status_line_re" in callback_calls[1][3]
    assert callback_calls[2][0] == "wait"
    assert callback_calls[3] == ("write", ("/repo", "r1", "done", "detail"))


def test_backend_handlers_delegate_to_injected_lifecycle_functions():
    calls = []
    parts = _parts(
        managed_backend_status_fn=lambda **kwargs: calls.append(("status", kwargs)) or {"status": "external"},
        managed_backend_start_fn=lambda payload: calls.append(("start", payload)) or {"status": "started"},
        managed_backend_stop_fn=lambda payload: calls.append(("stop", payload)) or {"status": "stopped"},
        managed_backend_restart_fn=lambda payload: calls.append(("restart", payload)) or {"status": "restarted"},
    )

    assert parts["handle_backend_status_fn"]({"mode": "external", "workdir": "/tmp"})["status"] == "external"
    assert parts["handle_backend_start_fn"]({"mode": "managed-local"})["status"] == "started"
    assert parts["handle_backend_stop_fn"]({"mode": "managed-local"})["status"] == "stopped"
    assert parts["handle_backend_restart_fn"]({"mode": "managed-local"})["status"] == "restarted"
    assert calls == [
        ("status", {"mode": "external", "workdir": "/tmp"}),
        ("start", {"mode": "managed-local"}),
        ("stop", {"mode": "managed-local"}),
        ("restart", {"mode": "managed-local"}),
    ]


def test_build_request_handler_runtime_returns_callable_handle_request():
    from unittest.mock import MagicMock
    from toas.runtime.request_handler_assembly import build_request_handler_runtime

    cli_module = MagicMock()
    cli_module.run_step = MagicMock()

    runtime = build_request_handler_runtime(cli_module=cli_module)
    assert callable(runtime.handle_request)
    assert callable(runtime.safe_op_call)
    assert isinstance(runtime.op_handlers, dict)
    assert runtime.safe_op_call(
        "r1",
        "status",
        {},
        lambda payload: {"payload": payload},
    )["payload"] == {"payload": {}}
