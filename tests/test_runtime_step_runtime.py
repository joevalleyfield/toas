from __future__ import annotations

import logging
from dataclasses import replace
from types import SimpleNamespace

import pytest

import toas.step as real_step_mod
from toas.config import OperatorConfig, SessionPolicy
from toas.runtime.step_runtime import (
    _append_plan_frontier_results,
    _append_strict_mixed_intent_error_if_needed,
    _bootstrap_seed_consequences,
    _build_assistant_auto_staged_plan,
    _build_bootstrap_node,
    _build_new_transcript_nodes,
    _build_repair_frontier,
    _build_run_step_frontier_context,
    _collect_frontier_intents,
    _execute_frontier_consequences,
    _execute_plan_frontier_results,
    _expand_in_order_operator_candidates,
    _frontier_callable_near_miss_error,
    _frontier_has_callable_intent,
    _handle_assistant_non_plan_frontier,
    _handle_plan_frontier,
    _handle_user_generation_fallback,
    _map_lcp_index_to_lineage_boundary_index,
    _resolve_execution_dependencies,
    _route_frontier_consequence_path,
    _should_auto_stage_assistant_shell_block,
    _should_project_assistant_single_shell,
    _should_return_after_user_or_control,
    _stabilize_lcp_for_assistant_tail_replay,
    _working_with_transcript_tail_frontier,
    run_step,
)


def _last_shared_real_message_id(*, step_mod, transcript: str, log: list[dict], sentinel_id: str = "n0") -> str | None:
    nodes = step_mod.parse_transcript(transcript)
    i = step_mod._lcp(nodes, log)
    if i <= 0:
        return sentinel_id
    idx = i - 1
    if idx >= len(log):
        return None
    node_id = log[idx].get("id")
    return node_id if isinstance(node_id, str) else None


def _result(content: str, *, origin_role: str = "user", origin_kind: str = "tool_call", **fields) -> dict:
    return real_step_mod.make_result_node(content, origin_role=origin_role, origin_kind=origin_kind, **fields)


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


def test_run_step_bootstrap_empty_transcript_uses_bootstrap_prompt(monkeypatch):
    monkeypatch.setattr(real_step_mod, "load_prompt_ref", lambda *_args, **_kwargs: "bootstrap text")

    config = OperatorConfig(session=SessionPolicy(bootstrap_prompt_ref="demo/bootstrap"))

    new_nodes, out = run_step("", [], config=config)

    assert new_nodes == [{"role": "user", "content": "bootstrap text", "provenance": {"source": "bootstrap_seed"}}]
    assert [node["content"] for node in out] == ["bootstrap text", ""]


def test_run_step_returns_early_when_consequence_handler_requests_it(mocker):
    import toas.runtime.step_runtime as sr

    transcript = """\
## TOAS:USER
hello
"""
    consequence = {"role": "result", "content": "guarded"}
    mocker.patch.object(sr, "_execute_frontier_consequences", return_value=([consequence], True))

    new_nodes, out = run_step(transcript, [], generate=lambda _working: [])

    assert out == [consequence]
    assert new_nodes[-1] == consequence


def test_run_step_frontier_context_logs_debug_record(caplog):
    transcript = """\
## TOAS:USER
hello
"""

    with caplog.at_level(logging.DEBUG, logger="toas.runtime.step_runtime"):
        context = _build_run_step_frontier_context(step_mod=real_step_mod, transcript=transcript, log=[])

    assert context.bind_index == 0
    assert context.lcp_index == 0
    assert context.frontier == {"role": "user", "content": "hello"}
    assert context.new_from_transcript == [{"role": "user", "content": "hello", "provenance": {"source": "user_authored"}}]
    assert any('"phase": "run_step_frontier"' in record.message for record in caplog.records)


def test_working_with_transcript_tail_frontier_empty_reconstructed_uses_transcript_tail():
    out = _working_with_transcript_tail_frontier(
        transcript_nodes=[{"role": "user", "content": "tail"}],
        reconstructed_working=[],
    )

    assert out == [{"role": "user", "content": "tail"}]


def test_working_with_transcript_tail_frontier_empty_transcript_keeps_reconstructed():
    reconstructed = [{"role": "assistant", "content": "kept"}]

    out = _working_with_transcript_tail_frontier(transcript_nodes=[], reconstructed_working=reconstructed)

    assert out is reconstructed


def test_map_lcp_index_to_lineage_boundary_index_root_returns_none():
    assert _map_lcp_index_to_lineage_boundary_index(lcp_index=0) is None


def test_map_lcp_index_to_lineage_boundary_index_non_root_is_trivial_i_minus_one():
    assert _map_lcp_index_to_lineage_boundary_index(lcp_index=1) == 0
    assert _map_lcp_index_to_lineage_boundary_index(lcp_index=2) == 1
    assert _map_lcp_index_to_lineage_boundary_index(lcp_index=7) == 6


def test_map_lcp_index_to_lineage_boundary_index_same_space_alignment_uses_i_minus_one():
    bound_log = [{"id": "n1"}, {"id": "n2"}]
    bound_lineage = [{"id": "n1"}, {"id": "n2"}]
    assert (
        _map_lcp_index_to_lineage_boundary_index(
            lcp_index=2,
            bound_log=bound_log,
            bound_lineage=bound_lineage,
        )
        == 1
    )


def test_stabilize_lcp_returns_non_tail_index_unchanged():
    assert (
        _stabilize_lcp_for_assistant_tail_replay(
            nodes=[{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
            bound_log=[{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
            lcp_index=0,
        )
        == 0
    )


def test_map_lcp_index_to_lineage_boundary_index_sentinel_shift_still_uses_i_minus_one():
    bound_log = [{"id": "n1"}, {"id": "n2"}]
    bound_lineage = [{"id": "n0"}, {"id": "n1"}, {"id": "n2"}]
    assert (
        _map_lcp_index_to_lineage_boundary_index(
            lcp_index=2,
            bound_log=bound_log,
            bound_lineage=bound_lineage,
        )
        == 1
    )


def test_map_lcp_index_to_lineage_boundary_index_ignores_optional_context_for_now():
    assert _map_lcp_index_to_lineage_boundary_index(lcp_index=3, bound_log=[{"id": "n1"}], bound_lineage=[{"id": "n1"}]) == 2


def test_stabilize_lcp_for_assistant_tail_replay_guard_edges():
    assert _stabilize_lcp_for_assistant_tail_replay(nodes=[], bound_log=[], lcp_index=-1) == -1
    nodes = [
        {"role": "user", "content": "changed"},
        {"role": "assistant", "content": "## RESULT\nnew"},
    ]
    bound_log = [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "## RESULT\nold"},
    ]
    assert _stabilize_lcp_for_assistant_tail_replay(nodes=nodes, bound_log=bound_log, lcp_index=1) == 1


def test_frontier_callable_near_miss_error_guard_edges():
    config = OperatorConfig()
    assert _frontier_callable_near_miss_error(step_mod=SimpleNamespace(), frontier=None, config=config) is None
    assert _frontier_callable_near_miss_error(step_mod=SimpleNamespace(), frontier={"role": "user", "content": "operation: x"}, config=config) is None
    assert _frontier_callable_near_miss_error(step_mod=SimpleNamespace(), frontier={"role": "assistant", "content": ""}, config=config) is None
    assert _frontier_callable_near_miss_error(step_mod=SimpleNamespace(), frontier={"role": "assistant", "content": "plain"}, config=config) is None
    assert _frontier_callable_near_miss_error(step_mod=SimpleNamespace(), frontier={"role": "assistant", "content": "operation: x"}, config=config) is None

    extractor_with_candidate = SimpleNamespace(_extract_frontier_assistant_candidates=lambda *_args, **_kwargs: ([{"x": 1}], []))
    assert (
        _frontier_callable_near_miss_error(
            step_mod=extractor_with_candidate,
            frontier={"role": "assistant", "content": "operation: x"},
            config=config,
        )
        is None
    )

    extractor_with_non_yaml_skip = SimpleNamespace(_extract_frontier_assistant_candidates=lambda *_args, **_kwargs: ([], ["other skip"]))
    assert (
        _frontier_callable_near_miss_error(
            step_mod=extractor_with_non_yaml_skip,
            frontier={"role": "assistant", "content": "operation: x"},
            config=config,
        )
        is None
    )


def test_frontier_has_callable_intent_returns_false_for_missing_frontier():
    assert _frontier_has_callable_intent(step_mod=SimpleNamespace(), frontier=None, working=[], config=OperatorConfig()) is False


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


def test_run_step_frontier_is_always_transcript_tail_not_reconstructed_n_minus_1():
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B"},
        {"id": "n2", "parent": "n1", "role": "assistant", "content": "old tail"},
    ]
    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B

## TOAS:ASSISTANT
new tail
"""
    new_nodes, out = run_step(
        transcript,
        log,
        generate=lambda _working: {"role": "assistant", "content": "gen"},
    )
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]
    assert new_nodes[-1] == out[0]


def test_working_with_transcript_tail_frontier_replaces_reconstructed_tail():
    transcript_nodes = [{"role": "user", "content": "u"}, {"role": "assistant", "content": "tail"}]
    reconstructed = [{"role": "user", "content": "u"}, {"role": "assistant", "content": "stale"}]
    out = _working_with_transcript_tail_frontier(
        transcript_nodes=transcript_nodes,
        reconstructed_working=reconstructed,
    )
    assert out[-1]["content"] == "tail"


def test_working_with_transcript_tail_frontier_uses_transcript_when_reconstructed_empty():
    transcript_nodes = [{"role": "user", "content": "only"}]
    out = _working_with_transcript_tail_frontier(
        transcript_nodes=transcript_nodes,
        reconstructed_working=[],
    )
    assert out == transcript_nodes


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
        events=[],
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


def test_step_runtime_helper_collect_frontier_intents_prefers_status_helper_when_available():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="any": (None, False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: None,
        extract_user_tail_shell_command_with_status=lambda _content: ("echo hi", True),
        _extract_user_shell_command=lambda _content: (_ for _ in ()).throw(AssertionError("fallback should not run")),
        _extract_user_shell_argv=lambda _cmd: ["echo", "hi"],
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
    )
    frontier = {"role": "user", "content": "$ echo hi"}
    config = OperatorConfig()
    out = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=[frontier], config=config)
    assert out[4] == "echo hi"
    assert out[5] == ["echo", "hi"]


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


def test_step_runtime_helper_collect_frontier_intents_falls_back_when_status_helper_missing():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="any": (None, False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: None,
        _extract_user_shell_command=lambda _content: "echo hi",
        _extract_user_shell_argv=lambda _cmd: ["echo", "hi"],
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
    )
    frontier = {"role": "user", "content": "$ echo hi"}
    config = OperatorConfig()
    out = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=[frontier], config=config)
    assert out[4] == "echo hi"
    assert out[5] == ["echo", "hi"]


def test_step_runtime_helper_collect_frontier_intents_with_user_shell_disabled():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="any": (None, False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: None,
        _extract_user_shell_command=lambda _content: "echo hi",
        _extract_user_shell_argv=lambda _cmd: ["echo", "hi"],
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
    )
    frontier = {"role": "user", "content": "$ echo hi"}
    config = OperatorConfig(extraction=replace(OperatorConfig().extraction, user_shell=False))
    out = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=[frontier], config=config)
    assert out[4] is None
    assert out[5] is None


def test_step_runtime_helper_build_new_transcript_nodes_smoke():
    import toas.step as step_mod

    transcript = "## TOAS:USER\nhello\n"
    bind_index, lcp_index, nodes, divergence_parent, diagnostics = _build_new_transcript_nodes(
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


def test_build_new_transcript_nodes_marks_user_correction_of_generated_user():
    transcript = "## TOAS:USER\ncorrected\n"
    log = [
        {
            "role": "user",
            "content": "generated",
            "id": "n-generated",
            "provenance": {"source": "llm_generated"},
        }
    ]

    _, _, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=real_step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent=None,
        storage_tip_parent=None,
    )

    assert nodes[0]["provenance"] == {"source": "user_correction", "corrects": "n-generated"}


def test_build_new_transcript_nodes_sets_parent_to_divergence_boundary_not_tip():
    import toas.step as step_mod

    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
D

## TOAS:USER
C
"""
    log = [
        {"id": "n0", "role": "user", "content": "A"},
        {"id": "n1", "role": "assistant", "content": "B"},
        {"id": "n2", "role": "user", "content": "C"},
    ]
    bind_index, lcp_index, nodes, divergence_parent, diagnostics = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n2",
        storage_tip_parent="n2",
    )

    assert bind_index == 0
    assert lcp_index == 1
    assert nodes[0]["role"] == "assistant"
    assert nodes[0]["content"] == "D"
    assert nodes[0]["parent"] == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)


def test_build_new_transcript_nodes_root_divergence_sets_root_parent():
    import toas.step as step_mod

    root_like = "You are a helpful assistant kind of thing."
    root_like_variant = "You are a big helpful assistant kind of thing."
    transcript = f"""\
## TOAS:USER
{root_like_variant}

## TOAS:ASSISTANT
next
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": root_like},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "setup"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "work"},
    ]
    bind_index, lcp_index, nodes, divergence_parent, diagnostics = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n2",
        storage_tip_parent="n2",
    )

    assert bind_index == 0
    assert lcp_index == 0
    assert nodes[0]["role"] == "user"
    assert nodes[0]["content"] == root_like_variant
    assert nodes[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)
    assert nodes[1]["role"] == "assistant"


@pytest.mark.parametrize(
    ("bind_parent", "storage_tip_parent"),
    [
        ("n2", "n2"),
        ("n9", "n9"),
        ("n1", "n2"),
    ],
)
def test_build_new_transcript_nodes_root_divergence_never_inherits_selected_tip_parent(
    bind_parent: str,
    storage_tip_parent: str,
):
    import toas.step as step_mod

    transcript = """\
## TOAS:USER
A revised
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C"},
    ]
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent=bind_parent,
        storage_tip_parent=storage_tip_parent,
    )

    assert lcp_index == 0
    assert nodes[0]["role"] == "user"
    assert nodes[0]["content"] == "A revised"
    assert nodes[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)
    assert nodes[0].get("parent") != bind_parent


def test_build_new_transcript_nodes_non_root_whitespace_only_edit_stays_in_lineage():
    import toas.step as step_mod

    root = "Alpha beta"
    changed_ws = "Alpha beta"
    transcript = f"""\
## TOAS:USER
{changed_ws}
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": root},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "branch"},
    ]
    _, _, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n1",
        storage_tip_parent="n1",
    )
    assert nodes == []


def test_build_new_transcript_nodes_regenerated_assistant_reuses_same_boundary_parent():
    import toas.step as step_mod

    # Original lineage: A -> B -> C -> D
    # Transcript edit shape: keep A, replace B, delete C/D, regenerate B'
    # LCP boundary is after A, so regenerated assistant must parent to A (n0).
    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B-regenerated
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B-old"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C-adopt"},
        {"id": "n3", "parent": "n2", "role": "assistant", "content": "D-old"},
    ]
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n3",
        storage_tip_parent="n3",
    )

    assert lcp_index == 1
    assert nodes[0]["role"] == "assistant"
    assert nodes[0]["content"] == "B-regenerated"
    assert nodes[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)


def test_build_new_transcript_nodes_prefix_preservation_and_suffix_rebase_shape():
    import toas.step as step_mod

    # Existing: A -> B -> C -> D
    # Edited transcript: A -> B2 -> C2 -> D2
    # Prefix A preserved by LCP, suffix must be rebased from boundary parent A.
    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B2

## TOAS:USER
C2

## TOAS:ASSISTANT
D2
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C"},
        {"id": "n3", "parent": "n2", "role": "assistant", "content": "D"},
    ]
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n3",
        storage_tip_parent="n3",
    )

    assert lcp_index == 1
    assert [n["role"] for n in nodes] == ["assistant", "user", "assistant"]
    assert [n["content"] for n in nodes] == ["B2", "C2", "D2"]
    assert nodes[0].get("parent") == "n0"
    assert "parent" not in nodes[1]
    assert "parent" not in nodes[2]


def test_build_new_transcript_nodes_branch_non_interference_original_lineage_unchanged():
    import toas.step as step_mod

    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B-alt
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C"},
    ]
    original_snapshot = [dict(node) for node in log]

    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n2",
        storage_tip_parent="n2",
    )

    assert lcp_index == 1
    assert nodes[0]["content"] == "B-alt"
    assert nodes[0].get("parent") == "n0"
    # Non-interference: existing lineage input remains untouched.
    assert log == original_snapshot


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


def test_build_new_transcript_nodes_idempotent_when_transcript_matches_log():
    import toas.step as step_mod

    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B"},
    ]
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n1",
        storage_tip_parent="n1",
    )

    assert lcp_index == 2
    assert nodes == []


def test_build_new_transcript_nodes_result_marker_is_not_structural_boundary():
    import toas.step as step_mod

    transcript = """\
## TOAS:USER
work log

## RESULT

green
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "work log\n\n## RESULT\n\ngreen"},
    ]
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n0",
        storage_tip_parent="n0",
    )

    assert lcp_index == 1
    assert nodes == []


def test_build_new_transcript_nodes_result_text_edit_branches_as_user_content_sibling():
    import toas.step as step_mod

    transcript = """\
## TOAS:USER
work log

## RESULT

failure
"""
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "setup"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "ran command"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "work log\n\n## RESULT\n\nsuccess"},
    ]
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n2",
        storage_tip_parent="n2",
    )

    assert lcp_index == 0
    assert len(nodes) == 1
    assert nodes[0]["role"] == "user"
    assert nodes[0]["content"] == "work log\n\n## RESULT\n\nfailure"
    assert nodes[0].get("parent") == "n0"


def test_build_new_transcript_nodes_repeated_tail_rewrites_do_not_pin_old_boundary():
    import toas.step as step_mod

    # Step 1: initial history from transcript
    t1 = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B

## TOAS:USER
C
"""
    _, i1, n1, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=t1,
        log=[],
        lineage=[],
        bind_index=None,
        anchor_index=None,
        bind_parent=None,
        storage_tip_parent=None,
    )
    assert i1 == 0
    assert [node["role"] for node in n1] == ["user", "assistant", "user"]
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C"},
    ]

    # Step 2: append result-like content in user turn and adopt once
    t2 = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B

## TOAS:USER
C

## RESULT

ok
"""
    _, i2, n2, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=t2,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n2",
        storage_tip_parent="n2",
    )
    assert i2 == 2
    assert len(n2) == 1
    assert n2[0]["role"] == "user"
    assert n2[0]["content"] == "C\n\n## RESULT\n\nok"
    assert n2[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=t2, log=log)
    log2 = log[:2] + [{"id": "n3", "parent": "n1", "role": "user", "content": "C\n\n## RESULT\n\nok"}]

    # Step 3: rewrite tail and ensure divergence is from latest matching boundary.
    # Regression signal from field logs was pinning to stale older boundary.
    t3 = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B

## TOAS:USER
C

## RESULT

fail
"""
    _, i3, n3, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=t3,
        log=log2,
        lineage=log2,
        bind_index=None,
        anchor_index=None,
        bind_parent="n3",
        storage_tip_parent="n3",
    )
    assert i3 == 2
    assert len(n3) == 1
    assert n3[0]["role"] == "user"
    assert n3[0]["content"] == "C\n\n## RESULT\n\nfail"
    # Must branch from the latest stable boundary ('B' / n1), not root/stale collapse.
    assert n3[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=t3, log=log2)


def test_build_new_transcript_nodes_truncate_rebuild_tail_keeps_latest_shared_boundary():
    import toas.step as step_mod

    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C"},
        {"id": "n3", "parent": "n2", "role": "assistant", "content": "D"},
        {"id": "n4", "parent": "n3", "role": "user", "content": "E"},
    ]
    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B

## TOAS:USER
rebuild tail

## TOAS:USER
## RESULT

Z2
"""
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n4",
        storage_tip_parent="n4",
    )

    # Shared prefix should keep A/B boundary (index 2) rather than collapsing
    # toward root-level mismatch under tail rewrite.
    assert lcp_index >= 2
    assert len(nodes) == 2
    assert nodes[0]["role"] == "user"
    assert nodes[0]["content"] == "rebuild tail"
    assert nodes[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)


def test_build_new_transcript_nodes_parent_selection_invariant_to_storage_tip_parent():
    import toas.step as step_mod

    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
D

## TOAS:USER
C
"""
    log = [
        {"id": "n0", "role": "user", "content": "A"},
        {"id": "n1", "role": "assistant", "content": "B"},
        {"id": "n2", "role": "user", "content": "C"},
    ]

    a = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n2",
        storage_tip_parent="n2",
    )
    b = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n2",
        storage_tip_parent="n999",
    )

    assert a[0] == b[0]  # bind_index
    assert a[1] == b[1]  # lcp_index
    assert a[2] == b[2]  # parentage/content of new nodes


@pytest.mark.parametrize(
    ("bind_parent", "storage_tip_parent"),
    [
        ("n4", "n4"),
        ("n4", "n7"),
        ("n7", "n4"),
        ("n7", "n7"),
    ],
)
def test_build_new_transcript_nodes_multistep_tail_rewrite_boundary_depends_on_shared_prefix_not_tip(
    bind_parent: str,
    storage_tip_parent: str,
):
    import toas.step as step_mod

    # Simulate a deeper replayed state where a stale/advanced tip exists beyond
    # transcript-shared prefix; boundary should remain transcript-driven.
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "A"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B"},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C"},
        {"id": "n3", "parent": "n2", "role": "assistant", "content": "D"},
        {"id": "n4", "parent": "n3", "role": "user", "content": "E"},
        {"id": "n5", "parent": "n4", "role": "assistant", "content": "T1"},
        {"id": "n6", "parent": "n5", "role": "user", "content": "T2"},
        {"id": "n7", "parent": "n6", "role": "assistant", "content": "T3"},
    ]
    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B

## TOAS:USER
rebuild tail

## TOAS:USER
## RESULT

Z2
"""
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent=bind_parent,
        storage_tip_parent=storage_tip_parent,
    )

    # Shared prefix is A/B => boundary id n1. Tail rewrite should branch there.
    assert lcp_index == 2
    assert len(nodes) == 2
    assert nodes[0]["role"] == "user"
    assert nodes[0]["content"] == "rebuild tail"
    assert nodes[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)


def test_build_new_transcript_nodes_s17_long_suffix_rewrite_branches_from_last_shared_prefix():
    import toas.step as step_mod

    # Build N1..N25 alternating roles, with deterministic ids n0..n24.
    log: list[dict] = []
    parent = None
    for i in range(1, 26):
        node_id = f"n{i-1}"
        role = "user" if i % 2 == 1 else "assistant"
        log.append({"id": node_id, "parent": parent, "role": role, "content": f"N{i}"})
        parent = node_id

    # Transcript keeps N1..N7 and rewrites from N8 onward (N8'..N25').
    lines = []
    for i in range(1, 8):
        role = "USER" if i % 2 == 1 else "ASSISTANT"
        lines.append(f"## TOAS:{role}\n\nN{i}\n")
    for i in range(8, 26):
        role = "USER" if i % 2 == 1 else "ASSISTANT"
        lines.append(f"## TOAS:{role}\n\nN{i}_prime\n")
    transcript = "\n".join(lines)

    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent="n24",
        storage_tip_parent="n24",
    )

    # Shared prefix is exactly first seven turns.
    assert lcp_index == 7
    assert len(nodes) == 18
    assert nodes[0]["content"] == "N8_prime"
    # First rewritten node must branch from N7 (id n6), not an older/stale boundary.
    assert nodes[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)


def test_alignment_anchor_index_result_heavy_tail_variants_without_anchor_fall_back_to_zero():
    from toas.graph import alignment_anchor_index

    events = [
        {"id": "n0", "parent": None, "role": "user", "content": "A", "metadata": {}},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B", "metadata": {}},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C", "metadata": {}},
        {"id": "n3", "parent": "n2", "role": "assistant", "content": "D", "metadata": {}},
        {"id": "n4", "parent": "n3", "role": "user", "content": "E", "metadata": {}},
    ]

    base = """\
## TOAS:USER

A

## TOAS:ASSISTANT

B

## TOAS:USER

rebuild tail
"""
    result_tail = """\
## TOAS:USER

A

## TOAS:ASSISTANT

B

## TOAS:USER

rebuild tail

## TOAS:USER

## RESULT

Z2
"""
    result_tail_edited = """\
## TOAS:USER

A

## TOAS:ASSISTANT

B

## TOAS:USER

rebuild tail

## TOAS:USER

## RESULT

Z2 edited
"""

    a0 = alignment_anchor_index(events, base)
    a1 = alignment_anchor_index(events, result_tail)
    a2 = alignment_anchor_index(events, result_tail_edited)

    # Current contract: without a matching durable anchor, alignment fallback is 0.
    assert a0 == 0
    assert a1 == 0
    assert a2 == 0


def test_build_new_transcript_nodes_with_result_heavy_tail_and_anchor_keeps_shared_prefix_parent():
    import toas.step as step_mod
    from toas.graph import alignment_anchor_index

    events = [
        {"id": "n0", "parent": None, "role": "user", "content": "A", "metadata": {}},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "B", "metadata": {}},
        {"id": "n2", "parent": "n1", "role": "user", "content": "C", "metadata": {}},
        {"id": "n3", "parent": "n2", "role": "assistant", "content": "D", "metadata": {}},
        {"id": "n4", "parent": "n3", "role": "user", "content": "E", "metadata": {}},
    ]
    log = [{"id": e["id"], "role": e["role"], "content": e["content"]} for e in events]
    transcript = """\
## TOAS:USER

A

## TOAS:ASSISTANT

B

## TOAS:USER

rebuild tail

## TOAS:USER

## RESULT

Z2 edited
"""

    anchor_index = alignment_anchor_index(events, transcript)
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=anchor_index,
        bind_parent="n4",
        storage_tip_parent="n4",
    )

    # Anchor fallback remains 0; shared-prefix behavior is still protected by LCP.
    assert anchor_index == 0
    assert lcp_index == 2
    assert len(nodes) == 2
    assert nodes[0]["content"] == "rebuild tail"
    assert nodes[0].get("parent") == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)


def test_build_new_transcript_nodes_replay_captured_control_tail_rewrite_red_signature():
    import toas.step as step_mod

    transcript = """\
## TOAS:USER

A

## TOAS:ASSISTANT

B

## TOAS:CONTROL

/session show

## TOAS:USER

rebuild tail

## TOAS:USER

## RESULT

Z2
"""
    log = [
        {"role": "user", "content": "A", "id": "n0"},
        {"role": "assistant", "content": "B", "id": "n1"},
        {"role": "user", "content": "C", "id": "n2"},
        {"role": "assistant", "content": "GEN", "id": "n3"},
    ]
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=0,
        bind_parent="n3",
        storage_tip_parent="n3",
    )
    assert nodes
    first_parent = nodes[0].get("parent")
    assert first_parent == _last_shared_real_message_id(step_mod=step_mod, transcript=transcript, log=log)
    assert lcp_index == 2


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
    from toas.runtime.step_runtime import _run_user_intent_candidate

    with pytest.raises(RuntimeError, match="unknown user intent candidate kind"):
        _run_user_intent_candidate(
            candidate={"kind": "unknown", "value": None, "total": 1, "intent_id": "x", "order": 1},
            frontier_role="user",
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


def test_step_runtime_helper_run_user_intent_candidate_wraps_operator_errors():
    from toas.runtime.step_runtime import _run_user_intent_candidate

    step_mod = SimpleNamespace(
        _execute_operator_command=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad op")),
    )
    consequences: list[dict] = []

    _run_user_intent_candidate(
        candidate={"kind": "operator", "value": ("demo", []), "total": 1, "intent_id": 1, "order": 1},
        frontier_role="user",
        step_mod=step_mod,
        consequences=consequences,
        execute=lambda *_a, **_k: [],
        events=[],
        working=[],
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        config_sources={},
        already_executed_indices=set(),
        env_modifiers={},
        stream_stdout_enabled=True,
        arbitration_mode="in_order",
    )

    assert consequences[0]["role"] == "result"
    assert "[ERROR] /demo: bad op" in consequences[0]["content"]


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
        _execute_plan_for_frontier=lambda *_args, **_kwargs: [_result("plan-branch")],
        _plan_contains_shell=lambda _plan: False,
        _assistant_results_include_shell_block=lambda _results: False,
        _execute_operator_command=lambda *_args, **_kwargs: [_result("operator-branch", origin_kind="slash_command")],
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
            "origin_role": "user",
            "origin_kind": "tool_call",
            "projection_lane": "user",
            "intent_execution": {"id": "d1", "kind": "plan", "order": 1, "total": 2, "arbitration": "in_order"},
        },
        {
            "role": "result",
            "content": "operator-branch",
            "origin_role": "user",
            "origin_kind": "slash_command",
            "projection_lane": "user",
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
        _execute_plan_for_frontier=lambda *_args, **_kwargs: calls.append("plan") or [_result("plan-branch")],
        _execute_user_shell=lambda *_args, **_kwargs: calls.append("shell") or [_result("shell-branch", origin_kind="user_shell")],
        _execute_operator_command=lambda *_args, **_kwargs: calls.append("operator") or [_result("operator-branch", origin_kind="slash_command")],
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
            "origin_role": "user",
            "origin_kind": "tool_call",
            "projection_lane": "user",
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
        _execute_plan_for_frontier=lambda *_args, **_kwargs: calls.append("plan") or [_result("plan-branch")],
        _execute_user_shell=lambda *_args, **_kwargs: calls.append("shell") or [_result("shell-branch", origin_kind="user_shell")],
        _execute_operator_command=lambda *_args, **_kwargs: calls.append("operator") or [_result("operator-branch", origin_kind="slash_command")],
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
            "origin_role": "user",
            "origin_kind": "slash_command",
            "projection_lane": "user",
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
        _execute_plan_for_frontier=lambda *_args, **_kwargs: calls.append("plan") or [_result("plan-branch")],
        _execute_user_shell=lambda *_args, **_kwargs: calls.append("shell") or [_result("shell-branch", origin_kind="user_shell")],
        _execute_operator_command=lambda *_args, **_kwargs: calls.append("operator") or [_result("operator-branch", origin_kind="slash_command")],
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


def test_execute_frontier_consequences_control_operator_stamps_result_provenance():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="tail": (None, False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: ("help", []),
        extract_operator_commands=lambda _content: [("help", [])],
        _extract_user_shell_command=lambda _content: None,
        _extract_user_shell_argv=lambda _cmd: None,
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
        _execute_plan_for_frontier=lambda *_args, **_kwargs: [_result("plan-branch", origin_role="control")],
        _execute_user_shell=lambda *_args, **_kwargs: [_result("shell-branch", origin_kind="user_shell")],
        _execute_operator_command=lambda *_args, **_kwargs: [_result("operator-branch", origin_role="control", origin_kind="slash_command")],
    )
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=[],
        working=[{"role": "control", "content": "/help"}],
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
            "content": "operator-branch",
            "origin_role": "control",
            "origin_kind": "slash_command",
            "projection_lane": "control",
        }
    ]


def test_execute_frontier_consequences_user_shell_stamps_result_provenance():
    step_mod = SimpleNamespace(
        extract_plan_with_status=lambda _content, yaml_position="tail": (None, False),
        _has_turn_header_inert_directive=lambda _content: False,
        _extract_operator_command=lambda _content: None,
        extract_operator_commands=lambda _content: [],
        _extract_user_shell_command=lambda _content: "echo hi",
        _extract_user_shell_argv=lambda _cmd: ["echo", "hi"],
        _extract_loose_command=lambda _content: (None, False),
        resolve_effective_env_modifiers=lambda _working: {},
        _execute_plan_for_frontier=lambda *_args, **_kwargs: [_result("plan-branch")],
        _execute_user_shell=lambda *_args, **_kwargs: [_result("shell-branch", origin_kind="user_shell")],
        _execute_operator_command=lambda *_args, **_kwargs: [_result("operator-branch", origin_kind="slash_command")],
    )
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=[],
        working=[{"role": "user", "content": "show cwd\n$ pwd"}],
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
            "content": "shell-branch",
            "origin_role": "user",
            "origin_kind": "user_shell",
            "projection_lane": "user",
        }
    ]


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


def test_step_runtime_helper_plan_frontier_phase_helpers():
    step_mod = SimpleNamespace(
        _execute_plan_for_frontier=lambda *args, **kwargs: [{"role": "result", "content": "ok"}],
        _plan_contains_shell=lambda _plan: True,
        _assistant_results_include_shell_block=lambda _results: True,
    )
    results = _execute_plan_frontier_results(
        step_mod=step_mod,
        working=[{"role": "user", "content": "x"}],
        plan=[{"tool_name": "shell", "args": {"argv": ["echo", "hi"]}}],
        frontier_role="assistant",
        execute=lambda _working, _plan: [],
        command_cwd=".",
        workspace_mode="strict",
        workspace_roots=["."],
        env_modifiers={},
        stream_stdout_enabled=True,
    )
    assert results == [{"role": "result", "content": "ok"}]

    consequences: list[dict] = []
    _append_plan_frontier_results(consequences=consequences, results=results)
    assert consequences == results

    config = OperatorConfig()
    assert _should_auto_stage_assistant_shell_block(
        step_mod=step_mod,
        frontier_role="assistant",
        plan=[{"tool_name": "shell", "args": {"argv": ["echo", "hi"]}}],
        results=results,
        config=config,
    )


def test_collect_frontier_intents_stream_stdout_override_beats_ambient_env(monkeypatch):
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    frontier = {"role": "user", "content": "$ echo hi"}
    collected = _collect_frontier_intents(
        step_mod=real_step_mod,
        frontier=frontier,
        working=[frontier],
        config=OperatorConfig(),
        stream_stdout_enabled=False,
    )

    assert collected[-1] is False


def test_resolve_execution_dependencies_stream_stdout_override_beats_resolver():
    seen = {}
    step_mod = SimpleNamespace(
        resolve_effective_env_modifiers=lambda _working: {},
        resolve_effective_shell_allowed=lambda _working, _config, _events: ("echo",),
        resolve_effective_shell_stream_stdout=lambda _config, _env_modifiers: True,
        _execute_plan=lambda _plan, **kwargs: seen.update(kwargs) or [],
    )
    _generate, execute = _resolve_execution_dependencies(
        step_mod=step_mod,
        command_cwd=".",
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        generate=None,
        execute=None,
        events=[],
        stream_stdout_enabled=False,
    )

    execute([{"role": "user", "content": "x"}], [{"tool_name": "shell"}])

    assert seen["stream_stdout_enabled"] is False


def test_step_runtime_helper_route_frontier_consequence_path_assistant_shell_projection():
    step_mod = SimpleNamespace(
        _plan_is_single_shell=lambda _plan: True,
        _assistant_loose_command_projection=lambda cmd, recovered=False: {"role": "user", "content": cmd, "recovered": recovered},
    )
    consequences: list[dict] = []
    should_return_early = _route_frontier_consequence_path(
        step_mod=step_mod,
        frontier={"role": "assistant", "content": "x"},
        consequences=consequences,
        plan=[{"tool_name": "shell", "args": {"argv": ["echo", "hi"]}}],
        operator_command=None,
        operator_commands=[],
        shell_command=None,
        shell_argv=None,
        loose_command="echo hi",
        loose_command_recovered=True,
        turn_inert=False,
        execute=lambda *_a, **_k: [],
        events=[],
        working=[{"role": "assistant", "content": "x"}],
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        config_sources={},
        already_executed_indices=set(),
        env_modifiers={},
        stream_stdout_enabled=True,
        generate=lambda _working: [],
    )
    assert should_return_early is False
    assert consequences == [{"role": "user", "content": "echo hi", "recovered": True}]


def test_step_runtime_helper_route_frontier_consequence_path_assistant_plan():
    step_mod = SimpleNamespace(
        _execute_plan_for_frontier=lambda *_args, **_kwargs: [{"role": "result", "content": "ok"}],
        _plan_contains_shell=lambda _plan: False,
        _assistant_results_include_shell_block=lambda _results: False,
    )
    consequences: list[dict] = []

    should_return_early = _route_frontier_consequence_path(
        step_mod=step_mod,
        frontier={"role": "assistant", "content": "x"},
        consequences=consequences,
        plan=[{"tool_name": "echo"}],
        operator_command=None,
        operator_commands=[],
        shell_command=None,
        shell_argv=None,
        loose_command=None,
        loose_command_recovered=False,
        turn_inert=False,
        execute=lambda *_a, **_k: [],
        events=[],
        working=[{"role": "assistant", "content": "x"}],
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        config_sources={},
        already_executed_indices=set(),
        env_modifiers={},
        stream_stdout_enabled=True,
        generate=lambda *_a, **_k: [],
    )

    assert should_return_early is False
    assert consequences == [{"role": "result", "content": "ok"}]


def test_step_runtime_helper_route_frontier_consequence_path_control_without_candidates():
    step_mod = SimpleNamespace(
        _generation_guard_result=lambda **_kwargs: None,
    )
    consequences: list[dict] = []

    should_return_early = _route_frontier_consequence_path(
        step_mod=step_mod,
        frontier={"role": "control", "content": ""},
        consequences=consequences,
        plan=None,
        operator_command=None,
        operator_commands=[],
        shell_command=None,
        shell_argv=None,
        loose_command=None,
        loose_command_recovered=False,
        turn_inert=False,
        execute=lambda *_a, **_k: [],
        events=[],
        working=[{"role": "control", "content": ""}],
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
        config_sources={},
        already_executed_indices=set(),
        env_modifiers={},
        stream_stdout_enabled=True,
        generate=lambda *_a, **_k: [],
    )

    assert should_return_early is False
    assert consequences == []


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


def test_handle_plan_frontier_helper_stages_repair_frontier_for_replace_block_indent_only():
    step_mod = SimpleNamespace(
        _execute_plan_for_frontier=lambda *_args, **_kwargs: [
            {
                "role": "result",
                "content": "[ERROR] replace_block: tool replace_block found no matches",
                "payload": {
                    "tool_name": "replace_block",
                    "ok": False,
                    "error": "tool replace_block found no matches",
                    "summary": "tool replace_block found no matches",
                    "repair_suggestion": {
                        "type": "frontier_repair",
                        "tool_name": "replace_block",
                        "args_patch": {"search_indent": 4},
                    },
                },
            }
        ],
        _plan_contains_shell=lambda _plan: False,
        _assistant_results_include_shell_block=lambda _results: False,
    )
    consequences: list[dict] = []
    _handle_plan_frontier(
        step_mod=step_mod,
        frontier={"role": "assistant", "content": "x"},
        consequences=consequences,
        working=[{"role": "assistant", "content": "x"}],
        plan=[{"tool_name": "replace_block", "args": {"path": "x", "search_block": "a", "replacement_block": "b"}}],
        execute=lambda *_a, **_k: [],
        command_cwd=".",
        workspace_mode="strict",
        workspace_roots=["."],
        env_modifiers={},
        stream_stdout_enabled=True,
        config=OperatorConfig(),
    )
    repair_nodes = [node for node in consequences if node.get("role") == "user" and "search_indent" in str(node.get("content"))]
    assert repair_nodes == [
        {
            "role": "user",
            "content": "/heal search_indent=4",
            "provenance": {"source": "adopted"},
        }
    ]


def test_handle_plan_frontier_stages_one_indexed_heal_for_multiple_failures():
    def result(tool_name, *, indent=None):
        payload = {"tool_name": tool_name, "ok": indent is None}
        if indent is not None:
            payload["repair_suggestion"] = {
                "type": "frontier_repair",
                "tool_name": "replace_block",
                "args_patch": {"search_indent": indent},
            }
        return {"role": "result", "content": tool_name, "payload": payload}

    results = [
        result("read_file"),
        result("replace_block", indent=4),
        result("search"),
        result("replace_block", indent=8),
    ]
    plan = [
        {"tool_name": "read_file", "args": {"path": "x"}},
        {"tool_name": "replace_block", "args": {"path": "a", "search_block": "a", "replacement_block": "A"}},
        {"tool_name": "search", "args": {"path": ".", "query": "x"}},
        {"tool_name": "replace_block", "args": {"path": "b", "search_block": "b", "replacement_block": "B"}},
    ]
    step_mod = SimpleNamespace(
        _execute_plan_for_frontier=lambda *_args, **_kwargs: results,
        _plan_contains_shell=lambda _plan: False,
        _assistant_results_include_shell_block=lambda _results: False,
    )
    consequences = []

    _handle_plan_frontier(
        step_mod=step_mod,
        frontier={"role": "assistant", "content": "x"},
        consequences=consequences,
        working=[{"role": "assistant", "content": "x"}],
        plan=plan,
        execute=lambda *_a, **_k: [],
        command_cwd=".",
        workspace_mode="strict",
        workspace_roots=["."],
        env_modifiers={},
        stream_stdout_enabled=True,
        config=OperatorConfig(),
    )

    assert [node["content"] for node in consequences if node.get("role") == "user"] == [
        "/heal 2:search_indent=4 4:search_indent=8"
    ]


@pytest.mark.parametrize(
    "suggestion",
    [
        {"type": "other", "tool_name": "replace_block", "args_patch": {"search_indent": 4}},
        {"type": "frontier_repair", "tool_name": "search", "args_patch": {"search_indent": 4}},
        {"type": "frontier_repair", "tool_name": "replace_block", "args_patch": {"search_indent": -1}},
    ],
)
def test_build_repair_frontier_rejects_unsupported_repairs(suggestion):
    assert _build_repair_frontier(result={"repair_suggestion": suggestion}) is None


def test_build_repair_frontier_renders_supported_single_repair():
    result = {
        "repair_suggestion": {
            "type": "frontier_repair",
            "tool_name": "replace_block",
            "args_patch": {"search_indent": 4},
        }
    }

    assert _build_repair_frontier(result=result)["content"] == "/heal search_indent=4"

def test_stabilize_lcp_for_assistant_tail_replay_promotes_n_minus_1_to_full_match():
    nodes = [
        {"role": "user", "content": "Look around."},
        {"role": "assistant", "content": "```yaml\noperation: shell\narguments:\n  argv: [\"pwd\"]\n```\n\n/Users/tim/Documents/Projects/toas\n## RESULT\n..."},
    ]
    bound_log = [
        {"role": "user", "content": "Look around."},
        {"role": "assistant", "content": "```yaml\noperation: shell\narguments:\n  argv: [\"pwd\"]\n```"},
    ]
    assert _stabilize_lcp_for_assistant_tail_replay(nodes=nodes, bound_log=bound_log, lcp_index=1) == 2


def test_stabilize_lcp_for_assistant_tail_replay_keeps_lcp_when_prefix_differs():
    nodes = [
        {"role": "user", "content": "Look around changed"},
        {"role": "assistant", "content": "assistant drift"},
    ]
    bound_log = [
        {"role": "user", "content": "Look around."},
        {"role": "assistant", "content": "assistant"},
    ]
    assert _stabilize_lcp_for_assistant_tail_replay(nodes=nodes, bound_log=bound_log, lcp_index=1) == 1


def test_stabilize_lcp_for_assistant_tail_replay_does_not_apply_for_user_tail():
    nodes = [
        {"role": "assistant", "content": "A"},
        {"role": "user", "content": "B updated"},
    ]
    bound_log = [
        {"role": "assistant", "content": "A"},
        {"role": "user", "content": "B"},
    ]
    assert _stabilize_lcp_for_assistant_tail_replay(nodes=nodes, bound_log=bound_log, lcp_index=1) == 1


def test_stabilize_lcp_for_assistant_tail_replay_does_not_apply_without_result_marker():
    nodes = [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": "D"},
    ]
    bound_log = [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": "B"},
    ]
    assert _stabilize_lcp_for_assistant_tail_replay(nodes=nodes, bound_log=bound_log, lcp_index=1) == 1


def test_build_new_transcript_nodes_boundary_idx_out_of_range():
    import toas.step as step_mod
    log = [
        {"id": "n0", "role": "user", "content": "A"},
    ]
    transcript = """\
## TOAS:USER
A

## TOAS:ASSISTANT
B
"""
    _, lcp_index, nodes, _, _ = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=[],
        bind_index=None,
        anchor_index=None,
        bind_parent="n0",
        storage_tip_parent="n0",
    )
    assert lcp_index == 1
    assert nodes[0].get("parent") is None


def test_step_runtime_callable_near_miss_error():
    from toas.runtime.step_runtime import run_step
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
```yaml
operation:
  invalid: [
```
"""
    log = [
        {"role": "user", "content": "hello", "id": "n0"},
        {"role": "assistant", "content": "```yaml\noperation:\n  invalid: [\n```", "id": "n1"},
    ]
    results, consequences = run_step(transcript=transcript, log=log)
    assert len(consequences) == 1
    assert consequences[0]["role"] == "result"
    assert "callable-looking assistant block is not valid YAML" in consequences[0]["content"]


def test_step_runtime_callable_frontier_no_consequences_raises(mocker):
    import toas.runtime.step_runtime as sr
    from toas.runtime.step_runtime import run_step
    mocker.patch.object(sr, "_execute_frontier_consequences", return_value=([], False))
    transcript = """\
## TOAS:USER
$ echo hi
"""
    log = [
        {"role": "user", "content": "$ echo hi", "id": "n0"},
    ]
    with pytest.raises(RuntimeError, match="callable frontier produced no consequences"):
        run_step(transcript=transcript, log=log)
