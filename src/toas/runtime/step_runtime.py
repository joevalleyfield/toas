from __future__ import annotations

import importlib
from pathlib import Path

from ..config import OperatorConfig
from .intent_arbitration_edges import select_user_intent_candidates


def _resolve_execution_dependencies(*, step_mod, command_cwd, workspace_mode, workspace_roots, config, generate, execute):
    generate_fn = generate or (lambda _: None)
    execute_fn = execute or (
        lambda _working, plan: step_mod._execute_plan(
            plan,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=step_mod.resolve_effective_env_modifiers(_working),
            shell_allowed_commands=step_mod.resolve_effective_shell_allowed(_working, config),
            stream_stdout_enabled=step_mod.resolve_effective_shell_stream_stdout(
                config,
                step_mod.resolve_effective_env_modifiers(_working),
            ),
        )
    )
    return generate_fn, execute_fn


def _collect_frontier_intents(*, step_mod, frontier, working, config):
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
    if callable(resolve_stream):
        stream_stdout_enabled = resolve_stream(config, env_modifiers)
    else:
        stream_stdout_enabled = config.runtime.streaming_mode == "enabled"
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
        stream_stdout_enabled,
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
        for node in nodes:
            if isinstance(node, dict) and candidate["total"] > 1:
                node["intent_execution"] = {
                    "id": candidate["intent_id"],
                    "kind": candidate["kind"],
                    "order": candidate["order"],
                    "total": candidate["total"],
                    "arbitration": arbitration_mode,
                }
        consequences.extend(nodes)

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
            consequences.append({"role": "result", "content": f"[ERROR] /{command}: {exc}"})
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
                base_cwd=command_cwd,
                env_modifiers=env_modifiers,
                stream_stdout_enabled=stream_stdout_enabled,
            )
        )
        return
    raise RuntimeError(f"unknown user intent candidate kind: {kind}")


def _build_new_transcript_nodes(*, step_mod, transcript: str, log: list[dict], bind_index, anchor_index, bind_parent, storage_tip_parent):
    nodes = step_mod.parse_transcript(transcript)
    bind_index = step_mod._normalize_bind_index(bind_index, log)
    bound_log = log[bind_index:]
    anchor_index = step_mod._normalize_anchor_index(anchor_index, nodes, bound_log)
    i = anchor_index + step_mod._lcp(nodes[anchor_index:], bound_log[anchor_index:])
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

    new_from_transcript = step_mod._annotate_branch_parent(
        new_from_transcript,
        continuation_parent=bind_parent,
        storage_tip_parent=storage_tip_parent,
    )
    annotated = []
    for j, node in enumerate(new_from_transcript):
        if j in corrections:
            annotated.append({**node, "provenance": {"source": "user_correction", "corrects": corrections[j]}})
        elif node.get("role") == "user" and "provenance" not in node and j not in uncertain:
            annotated.append({**node, "provenance": {"source": "user_authored"}})
        else:
            annotated.append(node)
    return bind_index, i, annotated


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
    ) = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=working, config=config)

    if _should_project_assistant_single_shell(step_mod=step_mod, frontier=frontier, loose_command=loose_command, plan=plan):
        consequences.append(step_mod._assistant_loose_command_projection(loose_command, recovered=loose_command_recovered))
    elif frontier["role"] in {"user", "control"}:
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
            return consequences, should_return_early
    elif plan is not None:
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
    elif frontier["role"] == "assistant":
        consequences.append(
            _handle_assistant_non_plan_frontier(
                step_mod=step_mod,
                loose_command=loose_command,
                loose_command_recovered=loose_command_recovered,
            )
        )
    return consequences, should_return_early


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
    results = step_mod._execute_plan_for_frontier(
        working,
        plan,
        frontier_role=frontier["role"],
        execute=execute,
        command_cwd=command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        env_modifiers=env_modifiers,
        stream_stdout_enabled=stream_stdout_enabled,
    )
    consequences.extend(results)

    has_shell = step_mod._plan_contains_shell(plan)
    auto_stage = config.extraction.shell_staging == "auto"
    blocked_shell = step_mod._assistant_results_include_shell_block(results)
    if frontier["role"] == "assistant" and has_shell and auto_stage and blocked_shell:
        consequences.append(_build_assistant_auto_staged_plan(step_mod=step_mod, plan=plan, config=config))


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
    if arbitration_mode == "in_order" and operator_commands:
        operator_multi = [
            {
                "kind": "operator",
                "value": command_tuple,
                "order": idx + 1,
                "total": len(operator_commands),
                "intent_id": idx + 1,
            }
            for idx, command_tuple in enumerate(operator_commands)
        ]
        kinds = {c.get("kind") for c in candidates}
        if kinds <= {"operator"}:
            candidates = operator_multi
    if arbitration_mode == "strict" and len(candidates) > 1:
        handles = ", ".join(f"#{candidate['intent_id']}:{candidate['kind']}" for candidate in candidates)
        consequences.append(
            {
                "role": "result",
                "content": (
                    f"[ERROR] mixed-intent strict mode: {len(candidates)} intents detected; "
                    "resolve to one intent or change extraction.intent_arbitration\n"
                    f"detected intents: {handles}"
                ),
            }
        )
        return False
    for candidate in candidates:
        _run_user_intent_candidate(
            candidate=candidate,
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
    if candidates:
        return False
    if frontier["role"] != "user":
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


def run_step(  # noqa: PLR0913
    transcript: str,
    log: list[dict],
    generate=None,
    execute=None,
    bind_index=None,
    bind_parent=None,
    anchor_index=None,
    storage_tip_parent=None,
    command_cwd=".",
    previous_command_cwd=None,
    workspace_mode="strict",
    workspace_roots=None,
    config=None,
    config_sources: dict[str, str] | None = None,
    already_executed_indices=None,
):
    step_mod = importlib.import_module("toas.step")

    workspace_roots = workspace_roots or [str(Path.cwd().resolve())]
    config = config or OperatorConfig()
    generate, execute = _resolve_execution_dependencies(
        step_mod=step_mod,
        command_cwd=command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        generate=generate,
        execute=execute,
    )

    bind_index, i, new_from_transcript = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        bind_index=bind_index,
        anchor_index=anchor_index,
        bind_parent=bind_parent,
        storage_tip_parent=storage_tip_parent,
    )

    working = log[: bind_index + i] + new_from_transcript

    if not working and config.session.bootstrap_prompt_ref:
        return _bootstrap_seed_consequences(step_mod=step_mod, config=config)

    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=log,
        working=working,
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
    )
    if should_return_early:
        return new_from_transcript + consequences, consequences

    return new_from_transcript + consequences, consequences
