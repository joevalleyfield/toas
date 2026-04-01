import pytest

from toas.tools import REGISTRY, execute_call, get_tool, validate_call


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
