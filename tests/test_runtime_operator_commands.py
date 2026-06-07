from __future__ import annotations

import pytest

from toas.config import OperatorConfig
from toas.runtime.operator_commands import execute_operator_command
from toas.runtime.result_nodes import make_result_node


def _noop_execute(_working, _plan):
    return []


def test_execute_operator_command_prompts_uses_legacy_renderer(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda prefix: f"rendered:{prefix}")

    out = execute_operator_command(
        "prompts",
        ["dynamic"],
        execute=_noop_execute,
        events=[],
        working=[],
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
    )

    assert out == [
        make_result_node(
            "rendered:dynamic",
            origin_role="user",
            origin_kind="slash_command",
            transcript_inert=False,
        )
    ]


def test_execute_operator_command_graph_renders_result(tmp_path):
    events_dir = tmp_path / ".toas"
    events_dir.mkdir()
    (events_dir / "events.jsonl").write_text(
        '{"id":"n1","parent":null,"role":"user","content":"hello"}\n',
        encoding="utf-8",
    )

    out = execute_operator_command(
        "graph",
        [],
        execute=_noop_execute,
        events=[],
        working=[],
        transcript="",
        command_cwd=str(tmp_path),
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
    )

    assert out == [make_result_node("○ n1 u hello", origin_role="user", origin_kind="slash_command")]


def test_execute_operator_command_unknown_raises():
    with pytest.raises(ValueError, match="unknown command: /nope"):
        execute_operator_command(
            "nope",
            [],
            execute=_noop_execute,
            events=[],
            working=[],
            transcript="",
            command_cwd=".",
            previous_command_cwd=None,
            workspace_mode="strict",
            workspace_roots=["."],
            config=OperatorConfig(),
        )
