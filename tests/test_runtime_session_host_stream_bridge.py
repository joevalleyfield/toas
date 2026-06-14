from __future__ import annotations

from toas.runtime import session_host_stream_bridge as bridge


def _request(payload: dict | None = None) -> dict:
    return {
        "request_id": "req-bridge",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-bridge", **(payload or {})},
        "protocol_version": 1,
    }


def _run_bridge(request: dict, handler, *, deadline_cap_s_fn=lambda: 0.1):
    frames = []
    debug_events = []
    bridge.bridge_stream_subscribe_request(
        request,
        handler,
        frames.append,
        deadline_cap_s_fn=deadline_cap_s_fn,
        debug_log_fn=lambda event, **fields: debug_events.append((event, fields)),
    )
    return frames, debug_events


def test_stream_bridge_reports_upstream_thread_timeout(monkeypatch):
    class _HungThread:
        def __init__(self, *, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            pass

        def join(self, _timeout):
            pass

        def is_alive(self):
            return True

    monkeypatch.setattr(bridge.threading, "Thread", _HungThread)

    frames, debug_events = _run_bridge(_request(), lambda _request: {"ok": True, "payload": {}})

    assert frames[-1]["payload"] == {
        "kind": "push_complete",
        "run_id": "r-bridge",
        "complete": False,
        "reason": "upstream_read_timeout",
    }
    assert any(event == "stream_subscribe_upstream_read_timeout" for event, _fields in debug_events)


def test_stream_bridge_reports_upstream_exception_without_activity_terminality():
    def _handler(_request):
        raise RuntimeError("watch exploded")

    frames, debug_events = _run_bridge(_request(), _handler)

    assert frames[-1]["payload"]["complete"] is False
    assert frames[-1]["payload"]["reason"] == "upstream_exception"
    assert any(event == "stream_subscribe_upstream_exception" for event, _fields in debug_events)


def test_stream_bridge_reports_invalid_upstream_response():
    frames, debug_events = _run_bridge(_request(), lambda _request: "not a response")

    assert frames[-1]["payload"]["complete"] is False
    assert frames[-1]["payload"]["reason"] == "upstream_invalid_response"
    assert any(event == "stream_subscribe_upstream_invalid_response" for event, _fields in debug_events)


def test_stream_bridge_logs_idle_timeout_after_successful_empty_read(monkeypatch):
    now = iter([0.0, 0.0, 0.0, 0.0, 0.2, 0.2])
    monkeypatch.setattr(bridge.time, "time", now.__next__)

    frames, debug_events = _run_bridge(
        _request({"timeout_s": 0.1}),
        lambda _request: {"protocol_version": 1, "request_id": "req-bridge", "ok": True, "payload": {}},
    )

    assert [frame["payload"]["kind"] for frame in frames] == ["push_ack", "push_complete"]
    assert frames[-1]["payload"]["complete"] is False
    assert frames[-1]["payload"]["reason"] == "idle_timeout"
    assert any(event == "stream_subscribe_idle_timeout" for event, _fields in debug_events)
