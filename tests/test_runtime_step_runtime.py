from __future__ import annotations

from types import SimpleNamespace

from toas.config import OperatorConfig
from toas.runtime.step_runtime import (
    _build_new_transcript_nodes,
    _collect_frontier_intents,
    _execute_frontier_consequences,
    _resolve_execution_dependencies,
    run_step,
)


def test_run_step_generates_on_user_frontier():
    transcript = """\
## TOAS:USER
hello
"""

    generated = {"role": "assistant", "content": "hi"}

    new_nodes, out = run_step(
        transcript,
        [],
        generate=lambda _working: generated,
    )

    assert new_nodes[0]["role"] == "user"
    assert out == [generated]


def test_run_step_flips_on_assistant_frontier_without_callable_intent():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
plain assistant text
"""

    new_nodes, out = run_step(transcript, [])

    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]
    assert new_nodes[-1] == out[0]


def test_step_runtime_helper_dependency_resolution_uses_explicit_functions():
    step_mod = SimpleNamespace(_execute_plan=lambda *_args, **_kwargs: [])
    gen = lambda _w: [{"role": "assistant", "content": "x"}]
    exe = lambda _w, _p: [{"role": "result", "content": "ok"}]
    out_gen, out_exe = _resolve_execution_dependencies(
        step_mod=step_mod,
        command_cwd=".",
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        generate=gen,
        execute=exe,
    )
    assert out_gen is gen
    assert out_exe is exe


def test_step_runtime_helper_collect_frontier_intents_obeys_extraction_flags():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="any": ([{"tool_name": "echo_block", "args": {"content": "x"}}], False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: ("config", []),
        _extract_user_shell_command=lambda _content: "echo hi",
        _extract_user_shell_argv=lambda _cmd: ["echo", "hi"],
        _extract_loose_command=lambda _content: ("echo hi", False),
        resolve_effective_env_modifiers=lambda _working: {},
    )
    frontier = {"role": "user", "content": "/config"}
    config = OperatorConfig()
    out = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=[frontier], config=config)
    assert out[0] is False
    assert out[1] == [{"tool_name": "echo_block", "args": {"content": "x"}}]
    assert out[2] == ("config", [])
    assert out[3] == [("config", [])]
    assert out[4] == "echo hi"


def test_step_runtime_helper_collect_frontier_intents_honors_turn_header_inert():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="any": ([{"tool_name": "echo_block", "args": {"content": "x"}}], False),
        _has_turn_header_inert_directive=lambda _content: True,
        _extract_operator_command=lambda _content: ("help", []),
        _extract_user_shell_command=lambda _content: "echo hi",
        _extract_user_shell_argv=lambda _cmd: ["echo", "hi"],
        _extract_loose_command=lambda _content: ("echo hi", False),
        resolve_effective_env_modifiers=lambda _working: {},
    )
    frontier = {"role": "user", "content": "!inert\n/help"}
    config = OperatorConfig()
    out = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=[frontier], config=config)
    assert out[0] is True
    assert out[1] is None
    assert out[2] == ("help", [])
    assert out[3] == [("help", [])]
    assert out[4] is None
    assert out[6] is None


def test_step_runtime_helper_build_new_transcript_nodes_smoke():
    import toas.step as step_mod

    transcript = "## TOAS:USER\nhello\n"
    bind_index, lcp_index, nodes = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=[],
        bind_index=None,
        anchor_index=None,
        bind_parent=None,
        storage_tip_parent=None,
    )
    assert bind_index == 0
    assert lcp_index == 0
    assert nodes[0]["role"] == "user"


def test_step_runtime_helper_execute_frontier_consequences_flip_assistant():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="tail": (None, False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: None,
        _extract_user_shell_command=lambda _content: None,
        _extract_user_shell_argv=lambda _cmd: None,
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
    )
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=[],
        working=[{"role": "assistant", "content": "x"}],
        transcript="",
        execute=lambda _working, _plan: [],
        generate=lambda _working: [],
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        config_sources=None,
        already_executed_indices=None,
    )
    assert should_return_early is False
    assert consequences == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


def test_step_runtime_helper_execute_frontier_consequences_user_respects_text_order():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="tail": ([{"tool_name": "echo", "args": {"text": "x"}}], False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: ("help", []),
        _extract_user_shell_command=lambda _content: None,
        _extract_user_shell_argv=lambda _cmd: None,
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
        _execute_plan_for_frontier=lambda *_args, **_kwargs: [{"role": "result", "content": "plan-branch"}],
        _plan_contains_shell=lambda _plan: False,
        _assistant_results_include_shell_block=lambda _results: False,
        _execute_operator_command=lambda *_args, **_kwargs: [{"role": "result", "content": "operator-branch"}],
    )
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=[],
        working=[{"role": "user", "content": "```yaml\n- tool_name: echo\n  args:\n    text: x\n```\n/help"}],
        transcript="",
        execute=lambda _working, _plan: [],
        generate=lambda _working: [],
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        config_sources=None,
        already_executed_indices=None,
    )
    assert should_return_early is False
    assert consequences == [
        {
            "role": "result",
            "content": "plan-branch",
            "intent_execution": {"id": "d1", "kind": "plan", "order": 1, "total": 2, "arbitration": "in_order"},
        },
        {
            "role": "result",
            "content": "operator-branch",
            "intent_execution": {"id": "d2", "kind": "operator", "order": 2, "total": 2, "arbitration": "in_order"},
        },
    ]


def test_step_runtime_helper_execute_frontier_consequences_user_first_wins_uses_text_order():
    calls: list[str] = []
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="tail": ([{"tool_name": "echo", "args": {"text": "x"}}], False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: ("help", []),
        _extract_user_shell_command=lambda _content: None,
        _extract_user_shell_argv=lambda _cmd: None,
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
        _execute_plan_for_frontier=lambda *_args, **_kwargs: calls.append("plan") or [{"role": "result", "content": "plan-branch"}],
        _execute_user_shell=lambda *_args, **_kwargs: calls.append("shell") or [{"role": "result", "content": "shell-branch"}],
        _execute_operator_command=lambda *_args, **_kwargs: calls.append("operator") or [{"role": "result", "content": "operator-branch"}],
    )
    config = OperatorConfig()
    config = config.__class__(extraction=config.extraction.__class__(**{**config.extraction.__dict__, "intent_arbitration": "first_wins"}))
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=[],
        working=[{"role": "user", "content": "```yaml\n- tool_name: echo\n  args:\n    text: x\n```\n/help"}],
        transcript="",
        execute=lambda _working, _plan: [],
        generate=lambda _working: [],
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=config,
        config_sources=None,
        already_executed_indices=None,
    )
    assert should_return_early is False
    assert calls == ["plan"]
    assert consequences == [
        {
            "role": "result",
            "content": "plan-branch",
            "intent_execution": {"id": "d1", "kind": "plan", "order": 1, "total": 2, "arbitration": "first_wins"},
        }
    ]


def test_step_runtime_helper_execute_frontier_consequences_user_last_wins_uses_text_order():
    calls: list[str] = []
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="tail": ([{"tool_name": "echo", "args": {"text": "x"}}], False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: ("help", []),
        _extract_user_shell_command=lambda _content: None,
        _extract_user_shell_argv=lambda _cmd: None,
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
        _execute_plan_for_frontier=lambda *_args, **_kwargs: calls.append("plan") or [{"role": "result", "content": "plan-branch"}],
        _execute_user_shell=lambda *_args, **_kwargs: calls.append("shell") or [{"role": "result", "content": "shell-branch"}],
        _execute_operator_command=lambda *_args, **_kwargs: calls.append("operator") or [{"role": "result", "content": "operator-branch"}],
    )
    config = OperatorConfig()
    config = config.__class__(extraction=config.extraction.__class__(**{**config.extraction.__dict__, "intent_arbitration": "last_wins"}))
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=[],
        working=[{"role": "user", "content": "```yaml\n- tool_name: echo\n  args:\n    text: x\n```\n/help"}],
        transcript="",
        execute=lambda _working, _plan: [],
        generate=lambda _working: [],
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=config,
        config_sources=None,
        already_executed_indices=None,
    )
    assert should_return_early is False
    assert calls == ["operator"]
    assert consequences == [
        {
            "role": "result",
            "content": "operator-branch",
            "intent_execution": {"id": "d2", "kind": "operator", "order": 2, "total": 2, "arbitration": "last_wins"},
        }
    ]


def test_step_runtime_helper_execute_frontier_consequences_user_strict_rejects_mixed_intent():
    calls: list[str] = []
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="tail": ([{"tool_name": "echo", "args": {"text": "x"}}], False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: ("help", []),
        _extract_user_shell_command=lambda _content: "echo hi",
        _extract_user_shell_argv=lambda _cmd: ["echo", "hi"],
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
        _execute_plan_for_frontier=lambda *_args, **_kwargs: calls.append("plan") or [{"role": "result", "content": "plan-branch"}],
        _execute_user_shell=lambda *_args, **_kwargs: calls.append("shell") or [{"role": "result", "content": "shell-branch"}],
        _execute_operator_command=lambda *_args, **_kwargs: calls.append("operator") or [{"role": "result", "content": "operator-branch"}],
    )
    config = OperatorConfig()
    config = config.__class__(extraction=config.extraction.__class__(**{**config.extraction.__dict__, "intent_arbitration": "strict"}))
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=[],
        working=[{"role": "user", "content": "mixed"}],
        transcript="",
        execute=lambda _working, _plan: [],
        generate=lambda _working: [],
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=config,
        config_sources=None,
        already_executed_indices=None,
    )
    assert should_return_early is False
    assert calls == []
    assert len(consequences) == 1
    assert "mixed-intent strict mode" in consequences[0]["content"]
    assert "#d1:operator" in consequences[0]["content"]
