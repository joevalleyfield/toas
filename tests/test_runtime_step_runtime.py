from __future__ import annotations

from types import SimpleNamespace

from toas.config import OperatorConfig
from toas.runtime.step_runtime import (
    _collect_frontier_intents,
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
