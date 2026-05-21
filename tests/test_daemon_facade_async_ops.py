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
