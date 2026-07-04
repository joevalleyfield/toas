from __future__ import annotations

import pytest

from toas.projection_selection import (
    anchor_id_for_selected_sources,
    default_head_id_for_selected_sources,
    projection_selection,
    qualified_anchor_tuple,
    qualified_message_events_for_selected_sources,
)


def test_projection_selection_defaults_to_hot_head_when_hot_is_selected(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    segments_dir = events_path.parent / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    (segments_dir / "000001-events.jsonl").write_text(
        '{"id":"n1","parent":null,"role":"user","content":"cold","metadata":{}}\n',
        encoding="utf-8",
    )
    events_path.write_text(
        (
            '{"id":"n1","parent":null,"role":"user","content":"hot","metadata":{}}\n'
            '{"id":"n2","parent":"n1","role":"assistant","content":"head","metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    selected = projection_selection(events_path, source_tokens=["segments", "hot"], anchor_id=None)

    assert selected.head_id == "hot:n2"
    assert [event["id"] for event in selected.events if "role" in event] == [
        "000001:n1",
        "hot:n1",
        "hot:n2",
    ]


def test_default_head_uses_last_selected_source_when_hot_has_no_head():
    selected_sources = [
        ("older", [{"id": "n1", "parent": None, "role": "user", "content": "older"}]),
        ("hot", []),
        ("newer", [{"id": "n1", "parent": None, "role": "assistant", "content": "newer"}]),
    ]

    assert default_head_id_for_selected_sources(selected_sources) == "newer:n1"


def test_anchor_resolution_uses_stitched_common_prefix_aliases():
    selected_sources = [
        (
            "000001",
            [
                {"id": "n1", "parent": None, "role": "user", "content": "root"},
                {"id": "n2", "parent": "n1", "role": "assistant", "content": "same"},
            ],
        ),
        (
            "hot",
            [
                {"id": "n1", "parent": None, "role": "user", "content": "root"},
                {"id": "n2", "parent": "n1", "role": "assistant", "content": "same"},
                {"id": "n3", "parent": "n2", "role": "user", "content": "hot"},
            ],
        ),
    ]

    assert anchor_id_for_selected_sources(selected_sources, anchor_id="hot:n2") == "000001:n2"
    assert anchor_id_for_selected_sources(selected_sources, anchor_id="n1") == "000001:n1"


def test_anchor_resolution_reports_surface_neutral_errors():
    selected_sources = [
        ("older", [{"id": "n1", "parent": None, "role": "user", "content": "older"}]),
        ("newer", [{"id": "n1", "parent": None, "role": "assistant", "content": "newer"}]),
    ]

    with pytest.raises(SystemExit, match="projection anchor is ambiguous"):
        anchor_id_for_selected_sources(selected_sources, anchor_id="n1")
    with pytest.raises(SystemExit, match="projection anchor source not selected: missing"):
        anchor_id_for_selected_sources(selected_sources, anchor_id="missing:n1")
    with pytest.raises(SystemExit, match="projection anchor not found: newer:n9"):
        anchor_id_for_selected_sources(selected_sources, anchor_id="newer:n9")


def test_qualified_message_events_preserve_non_message_records_and_source_local_parents():
    selected = qualified_message_events_for_selected_sources(
        [
            (
                "older",
                [
                    {"id": "n1", "parent": None, "role": "user", "content": "root"},
                    {"kind": "tool_result", "related_to": "n1", "payload": {"ok": True}},
                ],
            ),
            (
                "hot",
                [
                    {"id": "n1", "parent": None, "role": "user", "content": "root"},
                    {"id": "n2", "parent": "n1", "role": "assistant", "content": "reply"},
                    {"kind": "anchor", "payload": {}},
                ],
            ),
        ]
    )

    assert selected == [
        {"id": "older:n1", "parent": None, "role": "user", "content": "root"},
        {"kind": "tool_result", "related_to": "n1", "payload": {"ok": True}},
        {"id": "hot:n1", "parent": None, "role": "user", "content": "root"},
        {"id": "hot:n2", "parent": "hot:n1", "role": "assistant", "content": "reply"},
        {"kind": "anchor", "payload": {}},
    ]


def test_qualified_anchor_tuple_rejects_incomplete_qualified_shapes():
    assert qualified_anchor_tuple("hot:n1") == ("hot", "n1")
    assert qualified_anchor_tuple("n1") is None
    assert qualified_anchor_tuple(":n1") is None
    assert qualified_anchor_tuple("hot:") is None
