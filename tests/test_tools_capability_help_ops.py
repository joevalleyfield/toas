from __future__ import annotations

from dataclasses import dataclass

import pytest

from toas.tools_cluster.capability_help_ops import (
    CapabilityHelpDeps,
    resolve_capability_topic,
    run_capability_help,
    select_tools_for_topic,
    tool_summary,
    tool_detail_lines,
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
        },
        shell_allowed={"echo", "pwd"},
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
    with pytest.raises(RuntimeError, match="unknown capability_help topic"):
        select_tools_for_topic("nope", deps=deps)
