from __future__ import annotations

from toas.runtime.intent_arbitration_edges import select_user_intent_candidates


def test_select_user_intent_candidates_orders_by_text_position():
    content = "```yaml\n- operation: echo\n  arguments:\n    text: hi\n```\n/help\n$ echo hi"
    out = select_user_intent_candidates(
        content=content,
        plan=[{"tool_name": "echo", "args": {"text": "hi"}}],
        operator_command=("help", []),
        shell_command="echo hi",
        shell_argv=["echo", "hi"],
        yaml_position="tail",
        arbitration_mode="in_order",
    )
    assert [item["kind"] for item in out] == ["plan", "operator", "shell"]
    assert [item["intent_id"] for item in out] == ["d1", "d2", "d3"]


def test_select_user_intent_candidates_first_and_last_wins_use_text_position():
    content = "```yaml\n- operation: echo\n  arguments:\n    text: hi\n```\n/help"
    first = select_user_intent_candidates(
        content=content,
        plan=[{"tool_name": "echo", "args": {"text": "hi"}}],
        operator_command=("help", []),
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
        arbitration_mode="first_wins",
    )
    last = select_user_intent_candidates(
        content=content,
        plan=[{"tool_name": "echo", "args": {"text": "hi"}}],
        operator_command=("help", []),
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
        arbitration_mode="last_wins",
    )
    assert [item["kind"] for item in first] == ["plan"]
    assert [item["kind"] for item in last] == ["operator"]


def test_select_user_intent_candidates_falls_back_to_stable_kind_order_when_positions_unknown():
    out = select_user_intent_candidates(
        content="mixed without markers",
        plan=[{"tool_name": "echo", "args": {"text": "x"}}],
        operator_command=("help", []),
        shell_command="echo hi",
        shell_argv=["echo", "hi"],
        yaml_position="tail",
        arbitration_mode="in_order",
    )
    assert [item["kind"] for item in out] == ["operator", "plan", "shell"]
