from toas.graph_message_edges import (
    lineage_or_message_events,
    message_view,
)


def test_lineage_or_message_events_returns_message_events_when_any_id_missing():
    events = [
        {"id": "n0", "role": "user", "content": "hello"},
        {"role": "assistant", "content": "partial"},
    ]

    def _lineage(_events, *, head_id=None):  # pragma: no cover - should not run
        raise AssertionError("lineage_fn should not be called when ids are incomplete")

    assert lineage_or_message_events(events, head_id=None, lineage_fn=_lineage) == events


def test_message_view_skips_incomplete_event_shapes_from_lineage_result():
    events = [
        {"id": "n0", "role": "user", "content": "ok"},
        {"id": "n1", "role": "assistant"},
    ]

    def _lineage(_events, *, head_id=None):
        return events

    assert message_view(events, head_id=None, lineage_fn=_lineage) == [{"role": "user", "content": "ok"}]
