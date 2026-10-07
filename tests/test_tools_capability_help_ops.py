from __future__ import annotations

from dataclasses import dataclass

import pytest

from toas.tools_cluster.capability_help_ops import (
    CapabilityHelpDeps,
    resolve_capability_topic,
    run_capability_help,
    select_tools_for_topic,
    tool_definitions,
    tool_detail_lines,
    tool_summary,
)


@dataclass(frozen=True)
class _Tool:
    required_args: tuple[str, ...]


def _deps() -> CapabilityHelpDeps:
    return CapabilityHelpDeps(
        registry={
            "shell": _Tool(("argv",)),
            "shell_script": _Tool(("script",)),
            "capability_help": _Tool(()),
            "replace_block": _Tool(("path", "search_block", "replacement_block")),
            "write_file": _Tool(("path", "content")),
        },
        shell_allowed={"echo", "pwd"},
        assistant_timeout_s=900,
        assistant_timeout_source="session_override",
    )


def test_capability_help_topic_resolution_and_selection():
    deps = _deps()
    assert resolve_capability_topic("tools", deps=deps) == "all"
    assert resolve_capability_topic("capaility_help", deps=deps) == "capability_help"
    assert select_tools_for_topic("shell", deps=deps) == ("shell", "shell_script")
    assert select_tools_for_topic("all", deps=deps) == tuple(sorted(deps.registry))


def test_capability_help_detail_lines_and_errors():
    deps = _deps()
    lines = tool_detail_lines("shell", deps=deps)
    assert any("arguments.argv" in line for line in lines)
    assert any("default 900s" in line and "session_override" in line for line in lines)
    assert all("max 30" not in line for line in lines)
    write_lines = tool_detail_lines("write_file", deps=deps)
    assert any("tool_writes.newline_style" in line for line in write_lines)
    assert any("force=true" in line or "overwrite policy" in line for line in write_lines)
    replace_lines = tool_detail_lines("replace_block", deps=deps)
    assert any("one uniform extra leading prefix" in line for line in replace_lines)
    assert any("strict/lax modes" in line for line in replace_lines)
    assert tool_summary("unknown") == "unknown"
    with pytest.raises(RuntimeError, match="unknown tool for capability help"):
        tool_detail_lines("missing", deps=deps)


def test_run_capability_help_happy_and_error_paths():
    deps = _deps()
    out = run_capability_help({"topic": "shell"}, deps=deps)
    assert out["ok"] is True
    assert out["tools"] == ["shell", "shell_script"]

    with pytest.raises(RuntimeError, match="unknown capability_help topic"):
        run_capability_help({"topic": "missing"}, deps=deps)
    with pytest.raises(RuntimeError, match="topic must be a non-empty string"):
        run_capability_help({"topic": "   "}, deps=deps)


def test_capability_help_all_and_unknown_topic_selection_errors():
    deps = _deps()
    out = run_capability_help({"topic": "all"}, deps=deps)
    assert out["ok"] is True
    assert select_tools_for_topic("write_file", deps=deps) == ("write_file",)
    with pytest.raises(RuntimeError, match="unknown capability_help topic"):
        select_tools_for_topic("nope", deps=deps)


def test_tool_summary_script_and_task_tools():
    assert "defer side threads" in tool_summary("capture_task_thread")
    assert "Python scripts" in tool_summary("python_script")
    assert "PowerShell scripts" in tool_summary("powershell_script")
    assert "language scripts" in tool_summary("interpreter_script")


def test_tool_definitions_default_and_custom_registry():
    defs = tool_definitions()
    assert "read_file" in defs
    assert defs["read_file"]["required_args"] == ["path"]
    assert "start_line" in defs["read_file"]["optional_args"]
    assert "read UTF-8" in defs["read_file"]["description"]
    assert "search" in defs
    assert defs["search"]["required_args"] == ["query"]
    assert "default_args" in defs["search"]

    # Custom registry with minimal ToolSpec
    from toas.tools_cluster.registry import ToolSpec
    custom_registry = {
        "dummy": ToolSpec("dummy", ("arg1", "arg2"), None),
    }
    custom_defs = tool_definitions(custom_registry)
    assert "dummy" in custom_defs
    assert custom_defs["dummy"]["required_args"] == ["arg1", "arg2"]
    assert custom_defs["dummy"]["optional_args"] == []
    assert "default_args" not in custom_defs["dummy"]

