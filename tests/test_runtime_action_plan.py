from __future__ import annotations

from toas.runtime.action_plan import ActionPlan, ToolRequest


def test_tool_request_is_inert_and_serializes_to_incumbent_shape():
    request = ToolRequest("read_file", {"path": "README.md"}, "inspect the readme")

    assert request.as_dict() == {
        "tool_name": "read_file",
        "args": {"path": "README.md"},
        "intention": "inspect the readme",
    }


def test_action_plan_keeps_plan_context_outside_tool_request_arguments():
    plan = ActionPlan.from_normalized_plan(
        [{"tool_name": "echo", "args": {"text": "done"}}],
        origin="assistant",
        ingress="plan",
        source="42",
        plan_position=2,
        selection_id="d2",
    )

    assert plan.origin == "assistant"
    assert plan.ingress == "plan"
    assert plan.source == "42"
    assert plan.plan_position == 2
    assert plan.selection_id == "d2"
    assert plan.as_normalized_plan() == [{"tool_name": "echo", "args": {"text": "done"}}]
