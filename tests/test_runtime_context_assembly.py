from __future__ import annotations

from toas.runtime.context_assembly import build_context_packet, shape_messages_for_packet, validate_context_packet


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
    assert "repo-state" in shaped[0]["content"]
    assert shaped[1:] == [{"role": "user", "content": "ship it"}]
