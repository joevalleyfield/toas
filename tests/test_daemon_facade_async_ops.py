from toas.daemon import facade_async_ops as f


def test_stream_read_async_step_op_delegates_to_runtime_store(monkeypatch):
    sentinel_run = object()
    seen = {}

    def _stream_read_async_step(*, run, mode, since_seq, initial_output_len, initial_event_seq):
        seen["args"] = (run, mode, since_seq, initial_output_len, initial_event_seq)
        return {"out": "x", "status": "running", "err": None, "next_seq": 1, "events": [], "run_mode": "cold_asyncio"}

    monkeypatch.setattr(f, "stream_read_async_step", _stream_read_async_step)
    out = f.stream_read_async_step_op(
        run=sentinel_run,
        mode="poll",
        since_seq=0,
        initial_output_len=0,
        initial_event_seq=0,
    )

    assert seen["args"] == (sentinel_run, "poll", 0, 0, 0)
    assert out["status"] == "running"


def test_facade_async_wrappers_delegate(monkeypatch):
    seen = {}

    monkeypatch.setattr(
        f,
        "emit_tool_events_from_line_impl",
        lambda run, line, **kwargs: seen.setdefault("emit", (run, line, kwargs)),
    )
    monkeypatch.setattr(
        f,
        "stream_process_output_impl",
        lambda run, *, emit_tool_events_from_line_fn: seen.setdefault("stream", (run, emit_tool_events_from_line_fn)),
    )
    monkeypatch.setattr(
        f,
        "wait_for_process_impl",
        lambda run, *, write_run_event_fn: seen.setdefault("wait", (run, write_run_event_fn)),
    )
    monkeypatch.setattr(
        f,
        "start_async_step_impl",
        lambda payload, **kwargs: (seen.setdefault("start", (payload, kwargs)), {"status": "ok"})[1],
    )
    monkeypatch.setattr(
        f,
        "stream_read_async_step",
        lambda **kwargs: {"out": "x", "status": "running", "err": None, "next_seq": 1, "events": [], "run_mode": "cold_asyncio"},
    )
    monkeypatch.setattr(f, "watch_async_step", lambda payload: {"watch": payload["run_id"]})
    monkeypatch.setattr(f, "cancel_async_step", lambda payload: {"cancel": payload["run_id"]})

    assert f.emit_tool_events_from_line(run=object(), line="x", prompt_progress_line_re=1, tool_status_line_re=2) is None
    assert f.stream_process_output(run=object(), emit_tool_events_from_line_fn=str) is None
    assert f.wait_for_process(run=object(), write_run_event_fn=str) is None
    assert f.start_async_step(
        payload={},
        normalize_workdir_fn=str,
        thinking_stream_enabled_fn=str,
        prompt_progress_stream_enabled_fn=str,
        stream_process_output_fn=str,
        wait_for_process_fn=str,
        write_run_event_fn=str,
    ) == {"status": "ok"}
    assert f.watch_async_step_op({"run_id": "r1"}) == {"watch": "r1"}
    assert f.cancel_async_step_op({"run_id": "r1"}) == {"cancel": "r1"}
    assert f.stream_read_async_step_op(
        run=object(),
        mode="poll",
        since_seq=0,
        initial_output_len=0,
        initial_event_seq=0,
    ) == {"out": "x", "status": "running", "err": None, "next_seq": 1, "events": [], "run_mode": "cold_asyncio"}
