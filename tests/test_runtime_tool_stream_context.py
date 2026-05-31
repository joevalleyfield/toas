from toas.runtime.tool_stream_context import (
    current_tool_stream_emitter,
    emit_tool_done,
    emit_tool_progress_text,
    tool_stream_emitter,
)


def test_tool_stream_context_defaults_to_no_emitter():
    assert current_tool_stream_emitter() is None
    assert emit_tool_progress_text("chunk") is False
    assert emit_tool_progress_text("") is False
    assert emit_tool_done(operation="shell", ok=True) is False


def test_tool_stream_context_emits_and_resets():
    seen = []

    def _emit(event_type, payload):
        seen.append((event_type, payload))

    with tool_stream_emitter(_emit):
        assert current_tool_stream_emitter() is _emit
        assert emit_tool_progress_text("chunk") is True
        assert emit_tool_done(operation="shell", ok=False, status="error") is True
        assert emit_tool_done(operation="shell", ok=True) is True

    assert current_tool_stream_emitter() is None
    assert seen == [
        ("tool_progress", {"text": "chunk"}),
        ("tool_done", {"operation": "shell", "ok": False, "status": "error"}),
        ("tool_done", {"operation": "shell", "ok": True}),
    ]
