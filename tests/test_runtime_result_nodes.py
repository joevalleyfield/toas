import pytest

from toas.runtime.result_nodes import (
    make_result_node,
    projection_lane_for_result_origin,
    validate_result_node,
)


def test_make_result_node_stamps_projection_lane_and_extra_fields():
    node = make_result_node(
        "ok",
        origin_role="control",
        origin_kind="slash_command",
        transcript_inert=False,
    )

    assert node == {
        "role": "result",
        "content": "ok",
        "origin_role": "control",
        "origin_kind": "slash_command",
        "projection_lane": "control",
        "transcript_inert": False,
    }
    validate_result_node(node)


@pytest.mark.parametrize(
    ("origin_role", "origin_kind", "expected"),
    [
        ("user", "tool_call", "user"),
        ("user", "slash_command", "user"),
        ("user", "user_shell", "user"),
        ("assistant", "tool_call", "user"),
        ("control", "slash_command", "control"),
        ("control", "tool_call", "control"),
    ],
)
def test_projection_lane_for_result_origin(origin_role, origin_kind, expected):
    assert projection_lane_for_result_origin(origin_role=origin_role, origin_kind=origin_kind) == expected


def test_validate_result_node_ignores_non_result_nodes():
    validate_result_node({"role": "user", "content": "hello"})


def test_make_result_node_rejects_unknown_origin_role():
    with pytest.raises(ValueError, match="invalid result origin_role: system"):
        make_result_node("ok", origin_role="system", origin_kind="tool_call")


def test_make_result_node_rejects_unknown_origin_kind():
    with pytest.raises(ValueError, match="invalid result origin_kind: timer"):
        make_result_node("ok", origin_role="user", origin_kind="timer")


def test_validate_result_node_rejects_unknown_origin_role():
    with pytest.raises(ValueError, match="result node missing valid origin_role"):
        validate_result_node(
            {
                "role": "result",
                "content": "ok",
                "origin_role": "system",
                "origin_kind": "tool_call",
                "projection_lane": "user",
            }
        )


def test_validate_result_node_rejects_unknown_origin_kind():
    with pytest.raises(ValueError, match="result node missing valid origin_kind"):
        validate_result_node(
            {
                "role": "result",
                "content": "ok",
                "origin_role": "user",
                "origin_kind": "timer",
                "projection_lane": "user",
            }
        )


def test_validate_result_node_rejects_inconsistent_projection_lane():
    with pytest.raises(ValueError, match="result node missing valid projection_lane"):
        validate_result_node(
            {
                "role": "result",
                "content": "ok",
                "origin_role": "control",
                "origin_kind": "slash_command",
                "projection_lane": "user",
            }
        )
