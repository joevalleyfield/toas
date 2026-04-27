from __future__ import annotations

from toas.runtime.context_assembly import (
    build_context_packet,
    build_folded_packet_outline,
    render_folded_packet_outline,
    shape_messages_for_packet,
    validate_context_packet,
)


def test_build_context_packet_is_deterministic_with_lens_artifacts():
    working = [
        {"id": "n1", "role": "user", "content": "goal line"},
        {
            "id": "n2",
            "role": "assistant",
            "content": "artifact",
            "metadata": {
                "lens_artifact": {
                    "title": "repo-state",
                    "distillation": "tests are green",
                    "source_pointers": ["n1", "n2"],
                    "use_when": "planning",
                }
            },
        },
    ]

    packet_a = build_context_packet(working=working, project_messages_fn=lambda m: [{"role": "user", "content": "x"}])
    packet_b = build_context_packet(working=working, project_messages_fn=lambda m: [{"role": "user", "content": "x"}])

    assert packet_a == packet_b
    assert packet_a.goal_cue == "goal line"
    assert len(packet_a.artifacts) == 1
    assert packet_a.artifacts[0].title == "repo-state"


def test_validate_context_packet_reports_quality_failures():
    working = [
        {"id": "n1", "role": "user", "content": "goal"},
        {
            "id": "n2",
            "role": "assistant",
            "content": "artifact",
            "metadata": {
                "lens_artifact": {
                    "title": "repo-state",
                    "distillation": "tests are green",
                    "source_pointers": ["n404"],
                    "use_when": "planning",
                }
            },
        },
    ]
    packet = build_context_packet(working=working, project_messages_fn=lambda m: m)
    failure = validate_context_packet(packet, message_ids={"n1", "n2"})
    assert failure is not None
    assert failure.code == "staleness"
    assert "n404" in failure.detail


def test_build_context_packet_prefers_durable_event_lane_artifacts_by_title():
    working = [
        {
            "id": "n2",
            "role": "assistant",
            "content": "artifact",
            "metadata": {
                "lens_artifact": {
                    "title": "repo-state",
                    "distillation": "from-message",
                    "source_pointers": ["n2"],
                    "use_when": "planning",
                }
            },
        }
    ]
    events = [
        {
            "kind": "lens_artifact",
            "payload": {
                "action": "set",
                "title": "repo-state",
                "distillation": "from-events",
                "source_pointers": ["n2"],
                "use_when": "handoff",
            },
        }
    ]
    packet = build_context_packet(working=working, project_messages_fn=lambda m: m, events=events)
    assert len(packet.artifacts) == 1
    assert packet.artifacts[0].distillation == "from-events"


def test_shape_messages_for_packet_preserves_no_artifact_parity():
    packet = build_context_packet(
        working=[{"role": "user", "content": "hi"}],
        project_messages_fn=lambda _m: [{"role": "user", "content": "hi"}],
    )
    assert shape_messages_for_packet(packet) == [{"role": "user", "content": "hi"}]


def test_shape_messages_for_packet_prepends_system_packet_when_artifacts_exist():
    working = [
        {"id": "n1", "role": "user", "content": "ship it"},
        {
            "id": "n2",
            "role": "assistant",
            "content": "artifact",
            "metadata": {
                "lens_artifact": {
                    "title": "repo-state",
                    "distillation": "tests green",
                    "source_pointers": ["n1"],
                    "use_when": "planning",
                }
            },
        },
    ]
    packet = build_context_packet(working=working, project_messages_fn=lambda _m: [{"role": "user", "content": "ship it"}])
    shaped = shape_messages_for_packet(packet)
    assert shaped[0]["role"] == "system"
    assert "Context Assembly Packet" in shaped[0]["content"]
    assert "lens_distillations:" in shaped[0]["content"]
    assert "evidence_refs:" in shaped[0]["content"]
    assert "[repo-state] n1: ship it" in shaped[0]["content"]
    assert "constraints:" in shaped[0]["content"]
    assert "repo-state" in shaped[0]["content"]
    assert shaped[1:] == [{"role": "user", "content": "ship it"}]


def test_shape_messages_for_packet_enforces_deterministic_size_limits():
    working = [{"id": "n1", "role": "user", "content": "goal line"}]
    for index in range(10):
        working.append(
            {
                "id": f"n{index + 2}",
                "role": "assistant",
                "content": f"artifact {index}",
                "metadata": {
                    "lens_artifact": {
                        "title": f"title-{index}",
                        "distillation": "x" * 400,
                        "source_pointers": ["n1", f"n{index + 2}"],
                        "use_when": "planning",
                    }
                },
            }
        )
    packet = build_context_packet(working=working, project_messages_fn=lambda _m: [{"role": "user", "content": "goal line"}])
    shaped = shape_messages_for_packet(packet)
    content = shaped[0]["content"]
    assert "artifacts_shown: 6/10" in content
    assert "truncated_artifacts: 4" in content
    assert "distillation_chars_per_item: 220" in content
    assert "evidence_refs_per_item: 2" in content


def test_build_folded_packet_outline_is_deterministic_and_reports_hidden_counts():
    working = [{"id": "n1", "role": "user", "content": "goal line"}]
    for index in range(8):
        working.append(
            {
                "id": f"n{index + 2}",
                "role": "assistant",
                "content": f"artifact {index}",
                "metadata": {
                    "lens_artifact": {
                        "title": f"title-{index}",
                        "distillation": f"distillation-{index}",
                        "source_pointers": ["n1", f"n{index + 2}", f"n{index + 20}"],
                        "use_when": "planning",
                    }
                },
            }
        )
    packet = build_context_packet(working=working, project_messages_fn=lambda _m: [{"role": "user", "content": "goal line"}])
    outline_a = build_folded_packet_outline(packet)
    outline_b = build_folded_packet_outline(packet)
    assert outline_a == outline_b
    assert outline_a.visible_artifacts == 6
    assert outline_a.hidden_artifacts == 2
    assert all(node.hidden_ref_count == 2 for node in outline_a.nodes)
    assert outline_a.depth_counts == ((1, 6),)
    assert outline_a.expanded_text_chars >= outline_a.folded_text_chars


def test_build_folded_packet_outline_expands_when_reference_requested():
    working = [
        {"id": "n1", "role": "user", "content": "goal line"},
        {
            "id": "n2",
            "role": "assistant",
            "content": "artifact",
            "metadata": {
                "lens_artifact": {
                    "title": "repo-state",
                    "distillation": "tests green",
                    "source_pointers": ["n1", "n2", "n3"],
                    "use_when": "planning",
                }
            },
        },
    ]
    packet = build_context_packet(working=working, project_messages_fn=lambda _m: [{"role": "user", "content": "goal line"}])
    outline = build_folded_packet_outline(packet, expanded_refs={"n2", "n3"})
    rendered = render_folded_packet_outline(outline)
    assert outline.nodes[0].refs == ("n2", "n3")
    assert outline.nodes[0].expansion_reason == "explicit_ref"
    assert "expanded_refs: n2,n3" in rendered
    assert "[expand=explicit_ref]" in rendered
    assert "text_budget_chars: folded=" in rendered
    assert "depth_counts: 1:1" in rendered


def test_build_folded_packet_outline_handles_empty_artifacts():
    packet = build_context_packet(
        working=[{"id": "n1", "role": "user", "content": "goal"}],
        project_messages_fn=lambda _m: [{"role": "user", "content": "goal"}],
    )
    outline = build_folded_packet_outline(packet)
    rendered = render_folded_packet_outline(outline)
    assert outline.total_artifacts == 0
    assert outline.nodes == ()
    assert "- nodes:" in rendered
    assert "text_budget_chars: folded=0 expanded=0" in rendered
    assert "depth_counts: -" in rendered


def test_build_folded_packet_outline_respects_ref_cap_without_expansion():
    working = [
        {"id": "n1", "role": "user", "content": "goal line"},
        {
            "id": "n2",
            "role": "assistant",
            "content": "artifact",
            "metadata": {
                "lens_artifact": {
                    "title": "repo-state",
                    "distillation": "tests green",
                    "source_pointers": ["n1", "n2", "n3"],
                    "use_when": "planning",
                }
            },
        },
    ]
    packet = build_context_packet(working=working, project_messages_fn=lambda _m: [{"role": "user", "content": "goal line"}])
    outline = build_folded_packet_outline(packet, max_refs_per_artifact=1)
    assert outline.nodes[0].refs == ("n1",)
    assert outline.nodes[0].hidden_ref_count == 2
    assert outline.nodes[0].expansion_reason is None
