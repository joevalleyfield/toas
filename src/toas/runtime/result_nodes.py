"""Transient result-node construction and validation for TOAS projection.

Ownership boundary: shared runtime projection semantics, not step orchestration.
Result nodes are transient projected output — durable history lives in the graph.

Extracted from step.py (674) as part of the 400 decomposition arc.
"""
from __future__ import annotations

RESULT_ORIGIN_KINDS = {"tool_call", "slash_command", "user_shell"}
RESULT_ORIGIN_ROLES = {"user", "assistant", "control"}


def projection_lane_for_result_origin(*, origin_role: str, origin_kind: str) -> str:
    """Determine the projection lane for a result node based on its origin.

    Control-originated slash-commands and tool-calls project to the control
    lane; everything else projects to the user lane.
    """
    lane_map = {
        ("user", "tool_call"): "user",
        ("user", "slash_command"): "user",
        ("user", "user_shell"): "user",
        ("assistant", "tool_call"): "user",
        ("control", "slash_command"): "control",
        ("control", "tool_call"): "control",
    }
    return lane_map[(origin_role, origin_kind)]


def make_result_node(
    content: str,
    *,
    origin_role: str,
    origin_kind: str,
    **fields,
) -> dict:
    """Construct a provenance-complete transient result node.

    Validates origin_role and origin_kind, computes projection_lane from
    the origin, and merges any additional fields.
    """
    if origin_role not in RESULT_ORIGIN_ROLES:
        raise ValueError(f"invalid result origin_role: {origin_role}")
    if origin_kind not in RESULT_ORIGIN_KINDS:
        raise ValueError(f"invalid result origin_kind: {origin_kind}")
    return {
        "role": "result",
        "content": content,
        "origin_role": origin_role,
        "origin_kind": origin_kind,
        "projection_lane": projection_lane_for_result_origin(
            origin_role=origin_role,
            origin_kind=origin_kind,
        ),
        **fields,
    }


def validate_result_node(node: dict) -> None:
    """Validate a result node has correct provenance fields.

    Raises ValueError if origin_role, origin_kind, or projection_lane are
    invalid or inconsistent.
    """
    if node.get("role") != "result":
        return
    origin_role = node.get("origin_role")
    origin_kind = node.get("origin_kind")
    projection_lane = node.get("projection_lane")
    if not isinstance(origin_role, str) or origin_role not in RESULT_ORIGIN_ROLES:
        raise ValueError("result node missing valid origin_role")
    if not isinstance(origin_kind, str) or origin_kind not in RESULT_ORIGIN_KINDS:
        raise ValueError("result node missing valid origin_kind")
    expected_lane = projection_lane_for_result_origin(
        origin_role=origin_role,
        origin_kind=origin_kind,
    )
    if projection_lane != expected_lane:
        raise ValueError("result node missing valid projection_lane")
