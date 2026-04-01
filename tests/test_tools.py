import pytest

from toas.tools import REGISTRY, execute_call, execute_plan, get_tool, shape_result_content, validate_call


def test_get_tool_returns_registered_tool():
    tool = get_tool("echo")

    assert tool.name == "echo"
    assert tool.required_args == ("text",)
    assert tool.runner({"text": "hi"}) == "hi"


def test_registry_contains_echo():
    assert "echo" in REGISTRY


def test_get_tool_rejects_unknown_tool():
    with pytest.raises(RuntimeError, match="unknown tool: missing"):
        get_tool("missing")


def test_validate_call_returns_tool_and_args():
    tool, args = validate_call({"tool_name": "echo", "args": {"text": "hi"}})

    assert tool.name == "echo"
    assert args == {"text": "hi"}


def test_validate_call_rejects_missing_required_args():
    with pytest.raises(RuntimeError, match="invalid arguments for tool echo: missing text"):
        validate_call({"tool_name": "echo", "args": {}})


def test_execute_call_runs_validated_tool():
    assert execute_call({"tool_name": "echo", "args": {"text": "hi"}}) == "hi"


def test_execute_plan_returns_success_and_error_results():
    assert execute_plan(
        [
            {"tool_name": "echo", "args": {"text": "hi"}},
            {"tool_name": "missing", "args": {}},
        ]
    ) == [
        {"tool_name": "echo", "ok": True, "content": "hi"},
        {"tool_name": "missing", "ok": False, "content": "unknown tool: missing"},
    ]


def test_shape_result_content_formats_canonical_result_text():
    assert shape_result_content({"tool_name": "echo", "ok": True, "content": "hi"}) == "[OK] echo: hi"
    assert (
        shape_result_content({"tool_name": "echo", "ok": False, "content": "bad args"})
        == "[ERROR] echo: bad args"
    )
