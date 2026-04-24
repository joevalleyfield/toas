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
        _extract_operator_command=lambda _content: ("config", []),
        _extract_user_shell_command=lambda _content: "echo hi",
        _extract_user_shell_argv=lambda _cmd: ["echo", "hi"],
        _extract_loose_command=lambda _content: ("echo hi", False),
        resolve_effective_env_modifiers=lambda _working: {},
    )
    frontier = {"role": "user", "content": "/config"}
    config = OperatorConfig()
    out = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=[frontier], config=config)
    assert out[0] is not None
    assert out[1] == ("config", [])
    assert out[2] == "echo hi"


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
