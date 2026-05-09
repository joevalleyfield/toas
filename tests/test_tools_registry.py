import pytest

from toas.tools_cluster.registry import ToolSpec, execute_call, get_tool, validate_call


def _registry():
    return {
        "echo": ToolSpec(name="echo", required_args=("text",), runner=lambda args: {"ok": True, "text": args["text"]}),
        "nop": ToolSpec(name="nop", required_args=(), runner=lambda _args: {"ok": True}),
    }


def test_get_tool_success():
    tool = get_tool(_registry(), "echo")
    assert tool.name == "echo"
    assert tool.required_args == ("text",)


def test_get_tool_unknown_raises_runtime_error():
    with pytest.raises(RuntimeError, match="unknown tool: missing"):
        get_tool(_registry(), "missing")


def test_validate_call_success_with_required_args():
    tool, args = validate_call(_registry(), {"tool_name": "echo", "args": {"text": "hi"}})
    assert tool.name == "echo"
    assert args == {"text": "hi"}


def test_validate_call_uses_default_empty_args_when_omitted():
    tool, args = validate_call(_registry(), {"tool_name": "nop"})
    assert tool.name == "nop"
    assert args == {}


def test_validate_call_missing_required_args_raises_runtime_error():
    with pytest.raises(RuntimeError, match="invalid arguments for tool echo: missing text"):
        validate_call(_registry(), {"tool_name": "echo", "args": {}})


def test_execute_call_runs_runner_with_validated_args():
    output = execute_call(_registry(), {"tool_name": "echo", "args": {"text": "hello"}})
    assert output == {"ok": True, "text": "hello"}
