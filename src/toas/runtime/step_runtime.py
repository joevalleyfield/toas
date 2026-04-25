from __future__ import annotations

import importlib
from pathlib import Path

from ..config import OperatorConfig


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
        )
    )
    return generate_fn, execute_fn


def _collect_frontier_intents(*, step_mod, frontier, working, config):
    plan, _ = step_mod.extract_plan_with_status(
        frontier["content"],
        yaml_position=config.extraction.yaml_position,
    )
    operator_command = step_mod._extract_operator_command(frontier["content"]) if config.extraction.operator_command else None
    shell_command = step_mod._extract_user_shell_command(frontier["content"]) if config.extraction.user_shell else None
    shell_argv = step_mod._extract_user_shell_argv(shell_command) if shell_command is not None else None
    loose_command, loose_command_recovered = (
        step_mod._extract_loose_command(frontier["content"]) if config.extraction.loose_command_fallback else (None, False)
    )
    env_modifiers = step_mod.resolve_effective_env_modifiers(working)
    return plan, operator_command, shell_command, shell_argv, loose_command, loose_command_recovered, env_modifiers


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
        plan,
        operator_command,
        shell_command,
        shell_argv,
        loose_command,
        loose_command_recovered,
        env_modifiers,
    ) = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=working, config=config)

    if frontier["role"] == "assistant" and loose_command is not None and plan is not None and step_mod._plan_is_single_shell(plan):
        consequences.append(step_mod._assistant_loose_command_projection(loose_command, recovered=loose_command_recovered))
    elif frontier["role"] == "user" and operator_command is not None:
        command, args = operator_command
        try:
            consequences.extend(
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
    elif plan is not None:
        results = step_mod._execute_plan_for_frontier(
            working,
            plan,
            frontier_role=frontier["role"],
            execute=execute,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
        )
        consequences.extend(results)

        has_shell = step_mod._plan_contains_shell(plan)
        auto_stage = config.extraction.shell_staging == "auto"
        blocked_shell = step_mod._assistant_results_include_shell_block(results)
        if frontier["role"] == "assistant" and has_shell and auto_stage and blocked_shell:
            staged_content = step_mod._render_plan_as_yaml_preview(plan)
            staged_plan, _ = step_mod.extract_plan_with_status(
                staged_content,
                yaml_position=config.extraction.yaml_position,
            )
            staged_shell_command = step_mod._extract_user_shell_command(staged_content)
            if staged_plan is None and staged_shell_command is None:
                # Compact projection can be non-executable for multiline shell_script
                # and similar shapes; force canonical YAML so user-frontier execution
                # can still recover callable intent deterministically.
                staged_content = step_mod._render_plan_as_yaml_preview(plan, verbose=True)
            consequences.append(
                {
                    "role": "user",
                    "content": staged_content,
                    "provenance": {"source": "adopted"},
                }
            )
    elif frontier["role"] == "assistant" and loose_command is not None:
        consequences.append(step_mod._assistant_loose_command_projection(loose_command, recovered=loose_command_recovered))
    elif frontier["role"] == "user" and shell_argv is not None and shell_command is not None:
        consequences.extend(
            step_mod._execute_user_shell(
                {"argv": shell_argv, "command": shell_command},
                base_cwd=command_cwd,
                env_modifiers=env_modifiers,
            )
        )
    elif frontier["role"] == "user":
        guarded = step_mod._generation_guard_result(working=working, config=config)
        if guarded is not None:
            consequences.append(guarded)
            should_return_early = True
        else:
            consequences.extend(step_mod._as_nodes(generate(working)))
    elif frontier["role"] == "assistant":
        consequences.append(
            {
                "role": "user",
                "content": "",
                "metadata": {"transient_projection": "frontier_flip"},
            }
        )
    return consequences, should_return_early


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
