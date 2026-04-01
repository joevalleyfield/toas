import pytest

from toas.tools import REGISTRY, get_tool


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
