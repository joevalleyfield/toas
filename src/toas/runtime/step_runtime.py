from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from ..config import OperatorConfig
from ..transcript import (
    _lcp,
    _normalize_anchor_index,
    _normalize_bind_index,
)
from .intent_arbitration_edges import select_user_intent_candidates
from .reconciliation_handoff import (
    ReconciliationDiagnostics,
    ReconciliationHandoff,
)
from .result_nodes import make_result_node, validate_result_node

logger = logging.getLogger(__name__)



def _append_frontier_debug(record: dict) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", json.dumps(record, ensure_ascii=True))


def _resolve_execution_dependencies(
    *,
    step_mod,
    command_cwd,
    workspace_mode,
    workspace_roots,
    config,
    generate,
    execute,
    events,
    stream_stdout_enabled: bool | None = None,
):
    generate_fn = generate or (lambda _: None)
    execute_fn = execute or (
        lambda _working, plan: step_mod._execute_plan(
            plan,
            origin_role=_working[-1]["role"] if _working else "assistant",
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=step_mod.resolve_effective_env_modifiers(_working),
            shell_allowed_commands=step_mod.resolve_effective_shell_allowed(_working, config, events),
            stream_stdout_enabled=(
                stream_stdout_enabled
                if stream_stdout_enabled is not None
                else step_mod.resolve_effective_shell_stream_stdout(
                    config,
                    step_mod.resolve_effective_env_modifiers(_working),
                )
            ),
        )
    )
    return generate_fn, execute_fn


def _collect_frontier_intents(*, step_mod, frontier, working, config, stream_stdout_enabled: bool | None = None):
    turn_inert = frontier.get("role") == "user" and step_mod._has_turn_header_inert_directive(frontier["content"])
    plan, _ = step_mod.extract_plan_with_status(
        frontier["content"],
        yaml_position=config.extraction.yaml_position,
    )
    if turn_inert:
        plan = None
    operator_command = step_mod._extract_operator_command(frontier["content"]) if config.extraction.operator_command else None
    extract_operator_commands = getattr(step_mod, "extract_operator_commands", None)
    operator_commands = (
        extract_operator_commands(frontier["content"])
        if config.extraction.operator_command and callable(extract_operator_commands)
        else ([operator_command] if operator_command is not None else [])
    )
    shell_command = step_mod._extract_user_shell_command(frontier["content"]) if config.extraction.user_shell else None
    if turn_inert:
        shell_command = None
    shell_argv = step_mod._extract_user_shell_argv(shell_command) if shell_command is not None else None
    loose_command, loose_command_recovered = (
        step_mod._extract_loose_command(frontier["content"]) if config.extraction.loose_command_fallback else (None, False)
    )
    if turn_inert:
        loose_command, loose_command_recovered = (None, False)
    env_modifiers = step_mod.resolve_effective_env_modifiers(working)
    resolve_stream = getattr(step_mod, "resolve_effective_shell_stream_stdout", None)
    if stream_stdout_enabled is not None:
        resolved_stream_stdout_enabled = stream_stdout_enabled
    elif callable(resolve_stream):
        resolved_stream_stdout_enabled = resolve_stream(config, env_modifiers)
    else:
        resolved_stream_stdout_enabled = config.runtime.streaming_mode == "enabled"
    return (
        turn_inert,
        plan,
        operator_command,
        operator_commands,
        shell_command,
        shell_argv,
        loose_command,
        loose_command_recovered,
        env_modifiers,
        resolved_stream_stdout_enabled,
    )


def _select_user_intent_candidates(
    *,
    content: str,
    plan,
    operator_command,
    shell_command,
    shell_argv,
    yaml_position: str,
    arbitration_mode: str,
    include_plan_candidates: bool = True,
) -> list[dict]:
    return select_user_intent_candidates(
        content=content,
        plan=plan,
        operator_command=operator_command,
        shell_command=shell_command,
        shell_argv=shell_argv,
        yaml_position=yaml_position,
        arbitration_mode=arbitration_mode,
        include_plan_candidates=include_plan_candidates,
        include_shell_candidates=shell_command is not None and shell_argv is not None,
    )


def _run_user_intent_candidate(  # noqa: PLR0913
    *,
    candidate: dict,
    frontier_role: str,
    step_mod,
    consequences: list[dict],
    execute,
    events: list[dict],
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd,
    workspace_mode: str,
    workspace_roots: list[str],
    config,
    config_sources: dict[str, str] | None,
    already_executed_indices,
    env_modifiers: dict,
    stream_stdout_enabled: bool = True,
    arbitration_mode: str,
) -> None:
    def _append_nodes(nodes: list[dict]) -> None:
        appended_nodes: list[dict] = []
        for node in nodes:
            if isinstance(node, dict) and node.get("role") == "result":
                validate_result_node(node)
            if isinstance(node, dict) and candidate["total"] > 1:
                node["intent_execution"] = {
                    "id": candidate["intent_id"],
                    "kind": candidate["kind"],
                    "order": candidate["order"],
                    "total": candidate["total"],
                    "arbitration": arbitration_mode,
                }
            appended_nodes.append(node)
        consequences.extend(appended_nodes)

    kind = candidate["kind"]
    if kind == "operator":
        command, args = candidate["value"]
        try:
            _append_nodes(
                step_mod._execute_operator_command(
                    command,
                    args,
                    execute=execute,
                    events=events,
                    working=working,
                    transcript=transcript,
                    command_cwd=command_cwd,
                    previous_command_cwd=previous_command_cwd,
                    workspace_mode=workspace_mode,
                    workspace_roots=workspace_roots,
                    config=config,
                    config_sources=config_sources,
                    already_executed_indices=already_executed_indices,
                )
            )
        except (RuntimeError, ValueError) as exc:
            consequences.append(
                make_result_node(
                    f"[ERROR] /{command}: {exc}",
                    origin_role=frontier_role,
                    origin_kind="slash_command",
                )
            )
        return
    if kind == "plan":
        plan = candidate["value"]
        results = step_mod._execute_plan_for_frontier(
            working,
            plan,
            frontier_role="user",
            execute=execute,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
        )
        _append_nodes(results)
        return
    if kind == "shell":
        _append_nodes(
            step_mod._execute_user_shell(
                candidate["value"],
                origin_role=frontier_role,
                base_cwd=command_cwd,
                env_modifiers=env_modifiers,
                stream_stdout_enabled=stream_stdout_enabled,
            )
        )
        return
    raise RuntimeError(f"unknown user intent candidate kind: {kind}")


def _build_new_transcript_nodes(
    *,
    step_mod,
    transcript: str,
    log: list[dict],
    lineage: list[dict] | None = None,
    bind_index,
    anchor_index,
    bind_parent,
    storage_tip_parent,
):
    nodes = step_mod.parse_transcript(transcript)
    # Step reconstruction is transcript/LCP authoritative.
    bind_index = _normalize_bind_index(None, log)
    bound_log = log[bind_index:]
    anchor_index = _normalize_anchor_index(None, nodes, bound_log)
    i = anchor_index + _lcp(nodes[anchor_index:], bound_log[anchor_index:])
    i = _stabilize_lcp_for_assistant_tail_replay(nodes=nodes, bound_log=bound_log, lcp_index=i)
    new_from_transcript = nodes[i:]

    corrections: dict[int, str] = {}
    uncertain: set[int] = set()
    for j, node in enumerate(new_from_transcript):
        old = bound_log[i + j] if i + j < len(bound_log) else None
        if old is None or node.get("role") != "user":
            continue
        old_prov = old.get("provenance")
        if isinstance(old_prov, dict) and old_prov.get("source") == "llm_generated" and "id" in old:
            corrections[j] = old["id"]
        elif old_prov is None and old.get("role") != "user":
            uncertain.add(j)

    divergence_parent = None
    bound_lineage = (lineage or [])[bind_index:] if lineage else []
    if i == 0 and bound_lineage:
        root_id = bound_lineage[0].get("id")
        if isinstance(root_id, str) and root_id:
            divergence_parent = root_id
    elif i > 0:
        boundary_idx = _map_lcp_index_to_lineage_boundary_index(
            lcp_index=i,
            bound_log=bound_log,
            bound_lineage=bound_lineage,
        )
        if boundary_idx is None or boundary_idx < 0 or boundary_idx >= len(bound_lineage):
            boundary_id = None
        else:
            boundary_id = bound_lineage[boundary_idx].get("id")
        if isinstance(boundary_id, str) and boundary_id:
            divergence_parent = boundary_id

    new_from_transcript = step_mod._annotate_branch_parent(
        new_from_transcript,
        continuation_parent=divergence_parent,
        storage_tip_parent=None,
    )
    annotated = []
    for j, node in enumerate(new_from_transcript):
        if j in corrections:
            annotated.append({**node, "provenance": {"source": "user_correction", "corrects": corrections[j]}})
        elif node.get("role") == "user" and "provenance" not in node and j not in uncertain:
            annotated.append({**node, "provenance": {"source": "user_authored"}})
        else:
            annotated.append(node)
    _append_frontier_debug(
        {
            "phase": "build_new_transcript_nodes",
            "bind_index": bind_index,
            "anchor_index": anchor_index,
            "lcp_index": i,
            "parsed_nodes_len": len(nodes),
            "bound_log_len": len(bound_log),
            "new_from_transcript_len": len(annotated),
            "divergence_parent": divergence_parent,
            "bind_parent": None,
            "storage_tip_parent": None,
        }
    )
    diagnostics = ReconciliationDiagnostics(
        corrections=corrections,
        uncertain=uncertain,
        parsed_nodes_len=len(nodes),
        bound_log_len=len(bound_log),
        new_from_transcript_len=len(annotated),
    )
    return bind_index, i, annotated, divergence_parent, diagnostics



def _stabilize_lcp_for_assistant_tail_replay(*, nodes: list[dict], bound_log: list[dict], lcp_index: int) -> int:
    """Prevent n-1 fallback when only terminal assistant replay text drifts.

    This protects transcript-first progression for the observed sequence:
    step without append -> append replayed consequence -> repeated append.
    """
    if lcp_index < 0:
        return lcp_index
    if len(nodes) != len(bound_log):
        return lcp_index
    if not nodes or not bound_log:
        return lcp_index
    if lcp_index != len(nodes) - 1:
        return lcp_index
    tail_node = nodes[-1]
    tail_bound = bound_log[-1]
    tail_role = tail_node.get("role")
    if tail_role != "assistant" or tail_role != tail_bound.get("role"):
        return lcp_index
    tail_content = str(tail_node.get("content", ""))
    bound_content = str(tail_bound.get("content", ""))
    if "## RESULT" not in tail_content and "## RESULT" not in bound_content:
        return lcp_index
    # If all prior messages remain identical and only the final body differs,
    # keep full frontier alignment to avoid reusing n-1.
    for left, right in zip(nodes[:-1], bound_log[:-1], strict=False):
        if left.get("role") != right.get("role") or left.get("content") != right.get("content"):
            return lcp_index
    return len(nodes)


def _map_lcp_index_to_lineage_boundary_index(
    *,
    lcp_index: int,
    bound_log: list[dict] | None = None,
    bound_lineage: list[dict] | None = None,
) -> int | None:
    """Map transcript/message-space LCP index to bound-lineage boundary index."""
    if lcp_index <= 0:
        return None
    # Keep translation explicit in one seam; current policy is trivial i-1.
    return lcp_index - 1


def _execute_frontier_consequences(  # noqa: PLR0913
    *,
    step_mod,
    events: list[dict],
    working: list[dict],
    transcript: str,
    execute,
    generate,
    command_cwd: str,
    previous_command_cwd,
    workspace_mode: str,
    workspace_roots: list[str],
    config,
    config_sources: dict[str, str] | None,
    already_executed_indices,
    stream_stdout_enabled: bool | None = None,
):
    consequences: list[dict] = []
    should_return_early = False
    if not working:
        return consequences, should_return_early
    frontier = working[-1]
    (
        turn_inert,
        plan,
        operator_command,
        operator_commands,
        shell_command,
        shell_argv,
        loose_command,
        loose_command_recovered,
        env_modifiers,
        stream_stdout_enabled,
    ) = _collect_frontier_intents(
        step_mod=step_mod,
        frontier=frontier,
        working=working,
        config=config,
        stream_stdout_enabled=stream_stdout_enabled,
    )
    should_return_early = _route_frontier_consequence_path(
        step_mod=step_mod,
        frontier=frontier,
        consequences=consequences,
        plan=plan,
        operator_command=operator_command,
        operator_commands=operator_commands,
        shell_command=shell_command,
        shell_argv=shell_argv,
        loose_command=loose_command,
        loose_command_recovered=loose_command_recovered,
        turn_inert=turn_inert,
        execute=execute,
        events=events,
        working=working,
        transcript=transcript,
        command_cwd=command_cwd,
        previous_command_cwd=previous_command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        config_sources=config_sources,
        already_executed_indices=already_executed_indices,
        env_modifiers=env_modifiers,
        stream_stdout_enabled=stream_stdout_enabled,
        generate=generate,
    )
    return consequences, should_return_early


def _working_with_transcript_tail_frontier(*, transcript_nodes: list[dict], reconstructed_working: list[dict]) -> list[dict]:
    """Use transcript tail as the only frontier candidate."""
    transcript_tail = transcript_nodes[-1] if transcript_nodes else None
    if transcript_tail is None:
        return reconstructed_working
    if not reconstructed_working:
        return [transcript_tail]
    return reconstructed_working[:-1] + [transcript_tail]


def _route_frontier_consequence_path(  # noqa: PLR0913
    *,
    step_mod,
    frontier: dict,
    consequences: list[dict],
    plan,
    operator_command,
    operator_commands,
    shell_command,
    shell_argv,
    loose_command,
    loose_command_recovered: bool,
    turn_inert: bool,
    execute,
    events: list[dict],
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd,
    workspace_mode: str,
    workspace_roots: list[str],
    config,
    config_sources: dict[str, str] | None,
    already_executed_indices,
    env_modifiers,
    stream_stdout_enabled: bool,
    generate,
) -> bool:
    if _should_project_assistant_single_shell(step_mod=step_mod, frontier=frontier, loose_command=loose_command, plan=plan):
        consequences.append(step_mod._assistant_loose_command_projection(loose_command, recovered=loose_command_recovered))
        return False
    if frontier["role"] in {"user", "control"}:
        should_return_early = _handle_user_or_control_frontier(
            step_mod=step_mod,
            frontier=frontier,
            consequences=consequences,
            plan=plan,
            operator_command=operator_command,
            operator_commands=operator_commands,
            shell_command=shell_command,
            shell_argv=shell_argv,
            turn_inert=turn_inert,
            execute=execute,
            events=events,
            working=working,
            transcript=transcript,
            command_cwd=command_cwd,
            previous_command_cwd=previous_command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            config=config,
            config_sources=config_sources,
            already_executed_indices=already_executed_indices,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
            generate=generate,
        )
        if _should_return_after_user_or_control(consequences):
            return should_return_early
        return False
    if plan is not None:
        _handle_plan_frontier(
            step_mod=step_mod,
            frontier=frontier,
            consequences=consequences,
            working=working,
            plan=plan,
            execute=execute,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
            config=config,
        )
        return False
    if frontier["role"] == "assistant":
        consequences.append(
            _handle_assistant_non_plan_frontier(
                step_mod=step_mod,
                loose_command=loose_command,
                loose_command_recovered=loose_command_recovered,
            )
        )
    return False


def _should_project_assistant_single_shell(*, step_mod, frontier: dict, loose_command, plan) -> bool:
    return (
        frontier["role"] == "assistant"
        and loose_command is not None
        and plan is not None
        and step_mod._plan_is_single_shell(plan)
    )


def _should_return_after_user_or_control(consequences: list[dict]) -> bool:
    return bool(consequences)


def _handle_plan_frontier(  # noqa: PLR0913
    *,
    step_mod,
    frontier: dict,
    consequences: list[dict],
    working: list[dict],
    plan,
    execute,
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers,
    stream_stdout_enabled: bool,
    config,
) -> None:
    results = _execute_plan_frontier_results(
        step_mod=step_mod,
        working=working,
        plan=plan,
        frontier_role=frontier["role"],
        execute=execute,
        command_cwd=command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        env_modifiers=env_modifiers,
        stream_stdout_enabled=stream_stdout_enabled,
    )
    _append_plan_frontier_results(consequences=consequences, results=results)
    repair_frontier = _build_plan_repair_frontier(results=results, plan_size=len(plan))
    if repair_frontier is not None:
        consequences.append(repair_frontier)
    if _should_auto_stage_assistant_shell_block(
        step_mod=step_mod,
        frontier_role=frontier["role"],
        plan=plan,
        results=results,
        config=config,
    ):
        consequences.append(_build_assistant_auto_staged_plan(step_mod=step_mod, plan=plan, config=config))


def _execute_plan_frontier_results(  # noqa: PLR0913
    *,
    step_mod,
    working: list[dict],
    plan,
    frontier_role: str,
    execute,
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers,
    stream_stdout_enabled: bool,
) -> list[dict]:
    return step_mod._execute_plan_for_frontier(
        working,
        plan,
        frontier_role=frontier_role,
        execute=execute,
        command_cwd=command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        env_modifiers=env_modifiers,
        stream_stdout_enabled=stream_stdout_enabled,
    )


def _append_plan_frontier_results(*, consequences: list[dict], results: list[dict]) -> None:
    consequences.extend(results)


def _repair_command_arg(*, result: dict, operation_index: int | None = None) -> str | None:
    suggestion = result.get("repair_suggestion")
    if not isinstance(suggestion, dict):
        payload = result.get("payload")
        if isinstance(payload, dict):
            suggestion = payload.get("repair_suggestion")
    if not isinstance(suggestion, dict):
        return None
    if suggestion.get("type") != "frontier_repair":
        return None
    tool_name = suggestion.get("tool_name")
    args_patch = suggestion.get("args_patch")
    if tool_name != "replace_block" or not isinstance(args_patch, dict):
        return None
    search_indent = args_patch.get("search_indent")
    if set(args_patch) != {"search_indent"} or not isinstance(search_indent, int) or search_indent < 0:
        return None
    prefix = f"{operation_index}:" if operation_index is not None else ""
    return f"{prefix}search_indent={search_indent}"


def _build_repair_frontier(*, result: dict) -> dict | None:
    command_arg = _repair_command_arg(result=result)
    if command_arg is None:
        return None
    return {
        "role": "user",
        "content": f"/heal {command_arg}",
        "provenance": {"source": "adopted"},
    }


def _build_plan_repair_frontier(*, results: list[dict], plan_size: int) -> dict | None:
    indexed = plan_size > 1
    command_args = [
        command_arg
        for index, result in enumerate(results, start=1)
        if (command_arg := _repair_command_arg(result=result, operation_index=index if indexed else None)) is not None
    ]
    if not command_args:
        return None
    return {
        "role": "user",
        "content": f"/heal {' '.join(command_args)}",
        "provenance": {"source": "adopted"},
    }


def _should_auto_stage_assistant_shell_block(*, step_mod, frontier_role: str, plan, results: list[dict], config) -> bool:
    has_shell = step_mod._plan_contains_shell(plan)
    auto_stage = config.extraction.shell_staging == "auto"
    blocked_shell = step_mod._assistant_results_include_shell_block(results)
    return frontier_role == "assistant" and has_shell and auto_stage and blocked_shell


def _handle_assistant_non_plan_frontier(*, step_mod, loose_command, loose_command_recovered: bool) -> dict:
    if loose_command is not None:
        return step_mod._assistant_loose_command_projection(loose_command, recovered=loose_command_recovered)
    return {
        "role": "user",
        "content": "",
        "metadata": {"transient_projection": "frontier_flip"},
    }


def _build_assistant_auto_staged_plan(*, step_mod, plan, config) -> dict:
    staged_content = step_mod._render_plan_as_yaml_preview(
        plan,
        projection_shape=getattr(config.extraction, "projection_shape", "auto"),
    )
    staged_plan, _ = step_mod.extract_plan_with_status(
        staged_content,
        yaml_position=config.extraction.yaml_position,
    )
    staged_shell_command = step_mod._extract_user_shell_command(staged_content)
    if staged_plan is None and staged_shell_command is None:
        staged_content = step_mod._render_plan_as_yaml_preview(plan, verbose=True)
    return {
        "role": "user",
        "content": staged_content,
        "provenance": {"source": "adopted"},
    }


def _handle_user_or_control_frontier(  # noqa: PLR0913
    *,
    step_mod,
    frontier: dict,
    consequences: list[dict],
    plan,
    operator_command,
    operator_commands,
    shell_command,
    shell_argv,
    turn_inert: bool,
    execute,
    events: list[dict],
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd,
    workspace_mode: str,
    workspace_roots: list[str],
    config,
    config_sources: dict[str, str] | None,
    already_executed_indices,
    env_modifiers,
    stream_stdout_enabled: bool,
    generate,
) -> bool:
    arbitration_mode = getattr(config.extraction, "intent_arbitration", "in_order")
    candidates = _select_user_intent_candidates(
        content=frontier["content"],
        plan=plan,
        operator_command=operator_command,
        shell_command=shell_command,
        shell_argv=shell_argv,
        yaml_position=config.extraction.yaml_position,
        arbitration_mode=arbitration_mode,
        include_plan_candidates=not turn_inert,
    )
    candidates = _expand_in_order_operator_candidates(
        candidates=candidates,
        operator_commands=operator_commands,
        arbitration_mode=arbitration_mode,
    )
    if _append_strict_mixed_intent_error_if_needed(
        step_mod=step_mod,
        consequences=consequences,
        candidates=candidates,
        arbitration_mode=arbitration_mode,
    ):
        return False
    for candidate in candidates:
        _run_user_intent_candidate(
            candidate=candidate,
            frontier_role=frontier["role"],
            step_mod=step_mod,
            consequences=consequences,
            execute=execute,
            events=events,
            working=working,
            transcript=transcript,
            command_cwd=command_cwd,
            previous_command_cwd=previous_command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            config=config,
            config_sources=config_sources,
            already_executed_indices=already_executed_indices,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
            arbitration_mode=arbitration_mode,
        )
    return _handle_user_generation_fallback(
        step_mod=step_mod,
        frontier=frontier,
        consequences=consequences,
        candidates=candidates,
        working=working,
        config=config,
        generate=generate,
    )


def _expand_in_order_operator_candidates(*, candidates: list[dict], operator_commands: list, arbitration_mode: str) -> list[dict]:
    if arbitration_mode != "in_order" or not operator_commands:
        return candidates
    kinds = {candidate.get("kind") for candidate in candidates}
    if not kinds <= {"operator"}:
        return candidates
    return [
        {
            "kind": "operator",
            "value": command_tuple,
            "order": idx + 1,
            "total": len(operator_commands),
            "intent_id": idx + 1,
        }
        for idx, command_tuple in enumerate(operator_commands)
    ]


def _append_strict_mixed_intent_error_if_needed(*, step_mod=None, consequences: list[dict], candidates: list[dict], arbitration_mode: str) -> bool:
    if arbitration_mode != "strict" or len(candidates) <= 1:
        return False
    handles = ", ".join(f"#{candidate['intent_id']}:{candidate['kind']}" for candidate in candidates)
    consequences.append(
        make_result_node(
            (
                f"[ERROR] mixed-intent strict mode: {len(candidates)} intents detected; "
                "resolve to one intent or change extraction.intent_arbitration\n"
                f"detected intents: {handles}"
            ),
            origin_role="user",
            origin_kind="tool_call",
        )
    )
    return True


def _handle_user_generation_fallback(*, step_mod, frontier: dict, consequences: list[dict], candidates: list[dict], working: list[dict], config, generate) -> bool:
    if candidates or frontier["role"] != "user":
        return False
    guarded = step_mod._generation_guard_result(working=working, config=config)
    if guarded is not None:
        consequences.append(guarded)
        return True
    consequences.extend(step_mod._as_nodes(generate(working)))
    return False


def _build_bootstrap_node(*, step_mod, config) -> dict:
    bootstrap_content = step_mod.load_prompt_ref(
        config.session.bootstrap_prompt_ref,
        mode=config.prompt.mode,
        constraints=list(config.prompt.constraints),
        policy=step_mod.generation_policy_from_config(config),
        capability_profile=config.capability_advertisement.profile,
        capability_hidden_tools=config.capability_advertisement.hidden_tools,
    )
    return {
        "role": "user",
        "content": bootstrap_content,
        "provenance": {"source": "bootstrap_seed"},
    }


def _bootstrap_seed_consequences(*, step_mod, config) -> tuple[list[dict], list[dict]]:
    bootstrap_node = _build_bootstrap_node(step_mod=step_mod, config=config)
    next_user_slot = {"role": "user", "content": "", "provenance": {"source": "bootstrap_seed"}}
    return [bootstrap_node], [bootstrap_node, next_user_slot]


def _build_run_step_frontier_context(*, step_mod, transcript: str, log: list[dict]) -> ReconciliationHandoff:
    bind_index, lcp_index, new_from_transcript, divergence_parent, diagnostics = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=None,
        anchor_index=None,
        bind_parent=None,
        storage_tip_parent=None,
    )
    reconstructed_working = log[: bind_index + lcp_index] + new_from_transcript
    transcript_nodes = step_mod.parse_transcript(transcript)
    working_for_frontier = _working_with_transcript_tail_frontier(
        transcript_nodes=transcript_nodes,
        reconstructed_working=reconstructed_working,
    )
    frontier = working_for_frontier[-1] if working_for_frontier else None
    handoff = ReconciliationHandoff(
        working_for_frontier=working_for_frontier,
        new_from_transcript=new_from_transcript,
        frontier=frontier if isinstance(frontier, dict) else None,
        divergence_parent=divergence_parent,
        bind_index=bind_index,
        lcp_index=lcp_index,
        diagnostics=diagnostics,
    )
    _log_run_step_frontier_context(handoff, log=log)
    return handoff



def _preview_content(node: dict | None) -> str | None:
    if not isinstance(node, dict) or not node.get("content"):
        return None
    return str(node.get("content", ""))[:160]


def _log_run_step_frontier_context(handoff: ReconciliationHandoff, *, log: list[dict]) -> None:
    lineage_tail = log[-1] if log else None
    lcp_lineage_tail = log[handoff.lcp_index - 1] if handoff.lcp_index > 0 and handoff.lcp_index - 1 < len(log) else None
    frontier = handoff.frontier
    _append_frontier_debug(
        {
            "phase": "run_step_frontier",
            "log_len": len(log),
            "working_len": len(handoff.working_for_frontier),
            "bind_index": handoff.bind_index,
            "lcp_index": handoff.lcp_index,
            "divergence_parent": handoff.divergence_parent,
            "frontier_role": frontier.get("role") if isinstance(frontier, dict) else None,
            "frontier_id": frontier.get("id") if isinstance(frontier, dict) else None,
            "frontier_preview": _preview_content(frontier),
            "lineage_tail_id": lineage_tail.get("id") if isinstance(lineage_tail, dict) else None,
            "lineage_tail_role": lineage_tail.get("role") if isinstance(lineage_tail, dict) else None,
            "lineage_tail_preview": _preview_content(lineage_tail),
            "lcp_lineage_tail_id": lcp_lineage_tail.get("id") if isinstance(lcp_lineage_tail, dict) else None,
            "lcp_lineage_tail_role": lcp_lineage_tail.get("role") if isinstance(lcp_lineage_tail, dict) else None,
            "lcp_lineage_tail_preview": _preview_content(lcp_lineage_tail),
        }
    )


def run_step(  # noqa: PLR0913
    transcript: str,
    log: list[dict],
    generate=None,
    execute=None,
    command_cwd=".",
    previous_command_cwd=None,
    workspace_mode="strict",
    workspace_roots=None,
    config=None,
    config_sources: dict[str, str] | None = None,
    already_executed_indices=None,
    events: list[dict] | None = None,
    stream_stdout_enabled: bool | None = None,
):
    step_mod = importlib.import_module("toas.step")

    workspace_roots = workspace_roots or [str(Path.cwd().resolve())]
    config = config or OperatorConfig()
    durable_events = events if events is not None else log
    generate, execute = _resolve_execution_dependencies(
        step_mod=step_mod,
        command_cwd=command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        generate=generate,
        execute=execute,
        events=durable_events,
        stream_stdout_enabled=stream_stdout_enabled,
    )

    handoff = _build_run_step_frontier_context(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
    )

    if not handoff.working_for_frontier and config.session.bootstrap_prompt_ref:
        return _bootstrap_seed_consequences(step_mod=step_mod, config=config)

    callable_intent_present = _frontier_has_callable_intent(
        step_mod=step_mod,
        frontier=handoff.frontier,
        working=handoff.working_for_frontier,
        config=config,
    )
    callable_near_miss_error = _frontier_callable_near_miss_error(
        step_mod=step_mod,
        frontier=handoff.frontier,
        config=config,
    )
    if callable_near_miss_error and not callable_intent_present:
        consequences = [
            make_result_node(
                callable_near_miss_error,
                origin_role=handoff.frontier["role"] if isinstance(handoff.frontier, dict) else "user",
                origin_kind="tool_call",
            )
        ]
        return handoff.new_from_transcript + consequences, consequences
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=durable_events,
        working=handoff.working_for_frontier,
        transcript=transcript,
        execute=execute,
        generate=generate,
        command_cwd=command_cwd,
        previous_command_cwd=previous_command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        config_sources=config_sources,
        already_executed_indices=already_executed_indices,
        stream_stdout_enabled=stream_stdout_enabled,
    )
    if callable_intent_present and not consequences:
        _append_frontier_debug(
            {
                "phase": "run_step_callable_guard",
                "error": "callable frontier produced no consequences",
                "frontier_role": handoff.frontier.get("role") if isinstance(handoff.frontier, dict) else None,
                "frontier_preview": (
                    str(handoff.frontier.get("content", ""))[:160]
                    if isinstance(handoff.frontier, dict) and handoff.frontier.get("content")
                    else None
                ),
                "log_len": len(log),
                "working_len": len(handoff.working_for_frontier),
                "lcp_index": handoff.lcp_index,
            }
        )
        raise RuntimeError("callable frontier produced no consequences")
    if should_return_early:
        return handoff.new_from_transcript + consequences, consequences

    return handoff.new_from_transcript + consequences, consequences



def _frontier_has_callable_intent(*, step_mod, frontier: dict | None, working: list[dict], config) -> bool:
    if not isinstance(frontier, dict):
        return False
    (
        _turn_inert,
        plan,
        operator_command,
        _operator_commands,
        shell_command,
        shell_argv,
        loose_command,
        _loose_command_recovered,
        _env_modifiers,
        _stream_stdout_enabled,
    ) = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=working, config=config)
    return any(
        (
            plan is not None,
            operator_command is not None,
            shell_command is not None,
            shell_argv is not None,
            loose_command is not None,
        )
    )


def _frontier_callable_near_miss_error(*, step_mod, frontier: dict | None, config) -> str | None:
    if not isinstance(frontier, dict) or frontier.get("role") != "assistant":
        return None
    content = str(frontier.get("content", ""))
    if not content:
        return None
    looks_callable = any(token in content for token in ("operation:", "tool_name:", "command:", "cmd:"))
    if not looks_callable:
        return None
    extractor = getattr(step_mod, "_extract_frontier_assistant_candidates", None)
    if not callable(extractor):
        return None
    candidates, skipped = extractor(content, projection_shape=getattr(config.extraction, "projection_shape", "auto"))
    if candidates or not skipped:
        return None
    first = skipped[0]
    if "yaml parse error" not in first:
        return None
    return "[ERROR] callable-looking assistant block is not valid YAML for extraction\n" + first
