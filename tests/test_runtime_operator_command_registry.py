from __future__ import annotations

import pytest

from toas.config import OperatorConfig
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_command_registry import (
    OperatorCommandDescriptor,
    OperatorCommandRegistry,
    build_command_result_node,
    get_default_operator_command_registry,
    reset_default_operator_command_registry,
)


def _make_context() -> OperatorCommandContext:
    return OperatorCommandContext(
        execute=None,
        generate=None,
        events=[],
        working=[],
        frontier_role="user",
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[],
        config=OperatorConfig(),
        config_sources={},
        already_executed_indices=None,
    )


def test_build_command_result_node_single_line():
    ctx = _make_context()
    node = build_command_result_node("hello", context=ctx, source="command.test")
    assert node["content"] == "hello"
    assert node["role"] == "result"
    assert node["origin_role"] == "user"
    assert node["origin_kind"] == "slash_command"


def test_build_command_result_node_multiline_fenced():
    ctx = _make_context()
    node = build_command_result_node("line 1\nline 2", context=ctx, source="command.test", fenced=True)
    assert "kind=view" in node["content"]
    assert "source=command.test" in node["content"]

    node_unfenced = build_command_result_node("line 1\nline 2", context=ctx, source="command.test", fenced=False)
    assert node_unfenced["content"] == "line 1\nline 2"


def test_registry_register_and_lookup():
    reg = OperatorCommandRegistry()
    with pytest.raises(ValueError, match="command descriptor name cannot be empty"):
        reg.register(OperatorCommandDescriptor(name=""))

    desc = OperatorCommandDescriptor(
        name="test",
        summary="A test command",
        usage="usage: /test",
        aliases=("t", "tst"),
        source="command.test",
        handler=lambda args, ctx, step: f"handled: {args}",
    )
    reg.register(desc)

    assert reg.has_command("test")
    assert reg.has_command("t")
    assert reg.has_command("tst")
    assert not reg.has_command("unknown")

    assert reg.get("test") == desc
    assert reg.get("t") == desc
    assert reg.get("tst") == desc
    assert reg.get("unknown") is None

    assert reg.list_descriptors() == (desc,)

    reg.unregister("test")
    assert not reg.has_command("test")
    assert not reg.has_command("t")
    # idempotent unregister
    reg.unregister("test")


def test_registry_dispatch_unregistered():
    reg = OperatorCommandRegistry()
    ctx = _make_context()
    assert reg.dispatch("missing", [], context=ctx, step_mod=None) is None


def test_registry_dispatch_no_handler():
    reg = OperatorCommandRegistry()
    desc = OperatorCommandDescriptor(name="dummy")
    reg.register(desc)
    ctx = _make_context()
    assert reg.dispatch("dummy", ["arg"], context=ctx, step_mod=None) is None


def test_registry_dispatch_help_interception():
    reg = OperatorCommandRegistry()
    ctx = _make_context()

    # 1. Custom help handler
    desc_custom = OperatorCommandDescriptor(
        name="custom",
        help_handler=lambda ctx, step: "custom help output",
    )
    reg.register(desc_custom)
    res = reg.dispatch("custom", ["--help"], context=ctx, step_mod=None)
    assert res is not None
    assert res[0]["content"] == "custom help output"

    # 2. Standard usage fallback on -h
    desc_usage = OperatorCommandDescriptor(
        name="with_usage",
        usage="usage: /with_usage [opts]",
    )
    reg.register(desc_usage)
    res_usage = reg.dispatch("with_usage", ["-h"], context=ctx, step_mod=None)
    assert res_usage is not None
    assert res_usage[0]["content"] == "usage: /with_usage [opts]"

    # 3. No help_handler and no usage falls through
    desc_bare = OperatorCommandDescriptor(
        name="bare",
        handler=lambda args, ctx, step: "bare output",
    )
    reg.register(desc_bare)
    res_bare = reg.dispatch("bare", ["--help"], context=ctx, step_mod=None)
    assert res_bare is not None
    assert res_bare[0]["content"] == "bare output"


def test_registry_dispatch_coercion():
    reg = OperatorCommandRegistry()
    ctx = _make_context()

    # Handler returns str
    reg.register(OperatorCommandDescriptor(name="str_cmd", handler=lambda args, ctx, step: "result text"))
    res_str = reg.dispatch("str_cmd", [], context=ctx, step_mod=None)
    assert res_str is not None
    assert res_str[0]["content"] == "result text"

    # Handler returns tuple (content, metadata)
    reg.register(OperatorCommandDescriptor(name="tuple_cmd", handler=lambda args, ctx, step: ("tuple text", {"custom_field": "val"})))
    res_tuple = reg.dispatch("tuple_cmd", [], context=ctx, step_mod=None)
    assert res_tuple is not None
    assert res_tuple[0]["content"] == "tuple text"
    assert res_tuple[0]["custom_field"] == "val"

    # Handler returns dict
    reg.register(OperatorCommandDescriptor(name="dict_cmd", handler=lambda args, ctx, step: {"custom": "dict"}))
    res_dict = reg.dispatch("dict_cmd", [], context=ctx, step_mod=None)
    assert res_dict == [{"custom": "dict"}]

    # Handler returns list
    reg.register(OperatorCommandDescriptor(name="list_cmd", handler=lambda args, ctx, step: [{"item": 1}, {"item": 2}]))
    res_list = reg.dispatch("list_cmd", [], context=ctx, step_mod=None)
    assert res_list == [{"item": 1}, {"item": 2}]

    # Handler returns invalid type
    reg.register(OperatorCommandDescriptor(name="bad_cmd", handler=lambda args, ctx, step: 12345))
    with pytest.raises(TypeError, match="unexpected command handler result type: int"):
        reg.dispatch("bad_cmd", [], context=ctx, step_mod=None)


def test_default_registry_builtin_commands(monkeypatch):
    import toas.step as step_mod

    reset_default_operator_command_registry()
    reg = get_default_operator_command_registry()
    assert reg is get_default_operator_command_registry()
    assert reg.has_command("config")
    assert reg.has_command("help")

    ctx = _make_context()

    # Test /config --help
    monkeypatch.setattr(step_mod, "render_help_config", lambda *args: "mocked config help")
    res_config_help = reg.dispatch("config", ["--help"], context=ctx, step_mod=step_mod)
    assert res_config_help is not None
    assert res_config_help[0]["content"] == "mocked config help"

    # Test /config paths
    res_paths = reg.dispatch("config", ["paths"], context=ctx, step_mod=step_mod)
    assert res_paths is not None
    assert "discovered config paths" in res_paths[0]["content"]

    # Test /help commands
    monkeypatch.setattr(step_mod, "render_help_commands_inert", lambda: "mocked help commands")
    res_help = reg.dispatch("help", ["commands"], context=ctx, step_mod=step_mod)
    assert res_help is not None
    assert res_help[0]["content"] == "mocked help commands"
