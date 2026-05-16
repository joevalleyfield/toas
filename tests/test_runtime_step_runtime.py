from __future__ import annotations

from types import SimpleNamespace

from toas.config import OperatorConfig
from toas.runtime.step_runtime import (
    _append_strict_mixed_intent_error_if_needed,
    _bootstrap_seed_consequences,
    _build_bootstrap_node,
    _build_assistant_auto_staged_plan,
    _build_new_transcript_nodes,
    _collect_frontier_intents,
    _execute_frontier_consequences,
    _expand_in_order_operator_candidates,
    _handle_assistant_non_plan_frontier,
    _handle_user_generation_fallback,
    _handle_plan_frontier,
    _resolve_execution_dependencies,
    _should_project_assistant_single_shell,
    _should_return_after_user_or_control,
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


def test_step_runtime_bootstrap_helpers_build_expected_shapes():
    seen = {}

    def _load_prompt_ref(ref, **kwargs):
        seen["ref"] = ref
        seen.update(kwargs)
        return "seed content"

    step_mod = SimpleNamespace(
        load_prompt_ref=_load_prompt_ref,
        generation_policy_from_config=lambda _cfg: "policy",
    )
    cfg = OperatorConfig()
    cfg = cfg.__class__(session=cfg.session.__class__(**{**cfg.session.__dict__, "bootstrap_prompt_ref": "session-start"}))
    node = _build_bootstrap_node(step_mod=step_mod, config=cfg)
    assert node == {"role": "user", "content": "seed content", "provenance": {"source": "bootstrap_seed"}}
    assert seen["ref"] == "session-start"

    new_nodes, out = _bootstrap_seed_consequences(step_mod=step_mod, config=cfg)
    assert new_nodes == [node]
    assert out == [node, {"role": "user", "content": "", "provenance": {"source": "bootstrap_seed"}}]


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


def test_step_runtime_helper_run_user_intent_candidate_unknown_kind_raises():
    import pytest
    from toas.runtime.step_runtime import _run_user_intent_candidate

    with pytest.raises(RuntimeError, match="unknown user intent candidate kind"):
        _run_user_intent_candidate(
            candidate={"kind": "unknown", "value": None, "total": 1, "intent_id": "x", "order": 1},
            step_mod=SimpleNamespace(),
            consequences=[],
            execute=lambda *_a, **_k: [],
            events=[],
            working=[],
            transcript="",
            command_cwd=".",
            previous_command_cwd=None,
            workspace_mode="strict",
            workspace_roots=["."],
            config=OperatorConfig(),
            config_sources=None,
            already_executed_indices=None,
            env_modifiers={},
            arbitration_mode="in_order",
        )


def test_step_runtime_helper_execute_frontier_consequences_empty_working():
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=SimpleNamespace(),
        events=[],
        working=[],
        transcript="",
        execute=lambda *_a, **_k: [],
        generate=lambda *_a, **_k: [],
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        config_sources=None,
        already_executed_indices=None,
    )
    assert consequences == []
    assert should_return_early is False


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


def test_step_runtime_helper_expand_in_order_operator_candidates_replaces_operator_only_set():
    candidates = [{"kind": "operator", "value": ("config", ["show"]), "intent_id": 1, "order": 1, "total": 1}]
    operator_commands = [("config", ["show"]), ("config", ["set", "a", "b"])]
    expanded = _expand_in_order_operator_candidates(
        candidates=candidates,
        operator_commands=operator_commands,
        arbitration_mode="in_order",
    )
    assert [c["value"] for c in expanded] == operator_commands
    assert [c["order"] for c in expanded] == [1, 2]
    assert [c["total"] for c in expanded] == [2, 2]


def test_step_runtime_helper_append_strict_mixed_intent_error_if_needed():
    consequences: list[dict] = []
    appended = _append_strict_mixed_intent_error_if_needed(
        consequences=consequences,
        candidates=[
            {"intent_id": 1, "kind": "operator"},
            {"intent_id": 2, "kind": "plan"},
        ],
        arbitration_mode="strict",
    )
    assert appended is True
    assert "mixed-intent strict mode" in consequences[0]["content"]


def test_step_runtime_helper_user_generation_fallback_guard_and_generate_paths():
    step_mod = SimpleNamespace(
        _generation_guard_result=lambda **_kwargs: {"role": "result", "content": "guarded"},
        _as_nodes=lambda nodes: nodes,
    )
    consequences: list[dict] = []
    should_return_early = _handle_user_generation_fallback(
        step_mod=step_mod,
        frontier={"role": "user", "content": "prompt"},
        consequences=consequences,
        candidates=[],
        working=[{"role": "user", "content": "prompt"}],
        config=OperatorConfig(),
        generate=lambda _working: [{"role": "assistant", "content": "x"}],
    )
    assert should_return_early is True
    assert consequences == [{"role": "result", "content": "guarded"}]

    step_mod2 = SimpleNamespace(
        _generation_guard_result=lambda **_kwargs: None,
        _as_nodes=lambda nodes: nodes,
    )
    consequences2: list[dict] = []
    should_return_early2 = _handle_user_generation_fallback(
        step_mod=step_mod2,
        frontier={"role": "user", "content": "prompt"},
        consequences=consequences2,
        candidates=[],
        working=[{"role": "user", "content": "prompt"}],
        config=OperatorConfig(),
        generate=lambda _working: [{"role": "assistant", "content": "x"}],
    )
    assert should_return_early2 is False
    assert consequences2 == [{"role": "assistant", "content": "x"}]


def test_should_project_assistant_single_shell_helper():
    step_mod = SimpleNamespace(_plan_is_single_shell=lambda _plan: True)
    assert _should_project_assistant_single_shell(
        step_mod=step_mod,
        frontier={"role": "assistant"},
        loose_command="echo hi",
        plan=[{"tool_name": "shell", "args": {"argv": ["echo", "hi"]}}],
    )
    assert not _should_project_assistant_single_shell(
        step_mod=step_mod,
        frontier={"role": "user"},
        loose_command="echo hi",
        plan=[{"tool_name": "shell", "args": {"argv": ["echo", "hi"]}}],
    )


def test_should_return_after_user_or_control_helper():
    assert _should_return_after_user_or_control([]) is False
    assert _should_return_after_user_or_control([{"role": "result", "content": "x"}]) is True


def test_handle_assistant_non_plan_frontier_helper():
    step_mod = SimpleNamespace(_assistant_loose_command_projection=lambda cmd, recovered=False: {"role": "user", "content": cmd})
    loose = _handle_assistant_non_plan_frontier(step_mod=step_mod, loose_command="echo hi", loose_command_recovered=False)
    assert loose == {"role": "user", "content": "echo hi"}
    flip = _handle_assistant_non_plan_frontier(step_mod=step_mod, loose_command=None, loose_command_recovered=False)
    assert flip["metadata"]["transient_projection"] == "frontier_flip"


def test_build_assistant_auto_staged_plan_helper_fallback_verbose():
    step_mod = SimpleNamespace(
        _render_plan_as_yaml_preview=lambda _plan, projection_shape="auto", verbose=False: "compact" if not verbose else "verbose",
        extract_plan_with_status=lambda _content, yaml_position="tail": (None, False),
        _extract_user_shell_command=lambda _content: None,
    )
    config = OperatorConfig()
    node = _build_assistant_auto_staged_plan(step_mod=step_mod, plan=[{"tool_name": "shell_script"}], config=config)
    assert node["role"] == "user"
    assert node["content"] == "verbose"
    assert node["provenance"]["source"] == "adopted"


def test_handle_plan_frontier_helper_auto_stages_assistant_shell_block():
    step_mod = SimpleNamespace(
        _execute_plan_for_frontier=lambda *_args, **_kwargs: [{"role": "result", "content": "blocked"}],
        _plan_contains_shell=lambda _plan: True,
        _assistant_results_include_shell_block=lambda _results: True,
        _render_plan_as_yaml_preview=lambda _plan, projection_shape="auto", verbose=False: "rendered",
        extract_plan_with_status=lambda _content, yaml_position="tail": ([{"tool_name": "shell"}], False),
        _extract_user_shell_command=lambda _content: "echo hi",
    )
    config = OperatorConfig()
    consequences: list[dict] = []
    _handle_plan_frontier(
        step_mod=step_mod,
        frontier={"role": "assistant", "content": "x"},
        consequences=consequences,
        working=[{"role": "assistant", "content": "x"}],
        plan=[{"tool_name": "shell", "args": {"argv": ["echo", "hi"]}}],
        execute=lambda *_a, **_k: [],
        command_cwd=".",
        workspace_mode="strict",
        workspace_roots=["."],
        env_modifiers={},
        stream_stdout_enabled=True,
        config=config,
    )
    assert consequences[0]["role"] == "result"
    assert consequences[1]["role"] == "user"
    assert consequences[1]["provenance"]["source"] == "adopted"
