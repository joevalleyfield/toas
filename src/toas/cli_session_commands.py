from __future__ import annotations

import inspect
import json
import sys  # noqa: F401
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .graph import (
    list_heads,
    message_lineage,
    read_log,
    write_llm_call_record,  # noqa: F401
)
from .runtime.model_invocation_contracts import GenerationCompletion
from .runtime.session_file_edges import (
    write_text_with_newline_style as _write_text_with_newline_style,
)
from .runtime.step_context_runtime import (
    build_runtime_context as _build_runtime_context,
)
from .runtime.step_context_runtime import (
    prepare_session_transcript as _prepare_session_transcript,
)
from .runtime.step_context_runtime import (
    resolve_runtime_generation_context as _resolve_runtime_generation_context,
)
from .runtime.step_generation_runtime import StepCliDeps, build_step_cli_deps
from .runtime.step_result_runtime import persist_step_outputs_runtime
from .transcript import _lcp, parse_transcript, render_transcript

write_text_with_newline_style = _write_text_with_newline_style

_build_step_cli_deps = build_step_cli_deps





def _derive_best_prefix_head_id(*, events: list[dict], normalized_transcript: str) -> str | None:
    configured_head = None
    if not normalized_transcript.strip():
        return configured_head

    import toas.step as step_mod

    nodes = step_mod.parse_transcript(normalized_transcript)
    if not nodes:
        return configured_head

    candidates: list[str | None] = [configured_head]
    for head in list_heads(events):
        head_id = head.get("id")
        if isinstance(head_id, str) and head_id not in candidates:
            candidates.append(head_id)

    best_head = configured_head
    best_lcp = -1
    best_len = -1
    for head_id in candidates:
        lineage = message_lineage(events, head_id=head_id)
        log = [{"role": event["role"], "content": event["content"], "id": event.get("id")} for event in lineage]
        lcp = _lcp(nodes, log)
        if lcp > best_lcp or (lcp == best_lcp and len(log) > best_len):
            best_head = head_id
            best_lcp = lcp
            best_len = len(log)
    return best_head


def _build_step_kwargs(
    *,
    deps: StepCliDeps,
    runtime_ctx: dict,
    operator_config,
    config_sources,
    generation_fn,
    stream_stdout_enabled: bool | None = None,
):
    step_kwargs = {
        "generate": generation_fn,
    }
    params = inspect.signature(deps.step_fn).parameters
    if "command_cwd" in params:
        step_kwargs["command_cwd"] = runtime_ctx["command_cwd"]
    if "previous_command_cwd" in params:
        step_kwargs["previous_command_cwd"] = runtime_ctx["previous_command_cwd"]
    if "workspace_mode" in params:
        step_kwargs["workspace_mode"] = runtime_ctx["workspace_mode"]
    if "workspace_roots" in params:
        step_kwargs["workspace_roots"] = runtime_ctx["workspace_roots"]
    if "config" in params:
        step_kwargs["config"] = operator_config
    if "config_sources" in params:
        step_kwargs["config_sources"] = config_sources
    if "events" in params:
        step_kwargs["events"] = runtime_ctx["events"]
    if "bind_index" in params:
        step_kwargs["bind_index"] = runtime_ctx["bind_index"]
    if runtime_ctx.get("injected_control") and "injected_control" in params:
        step_kwargs["injected_control"] = True
    if stream_stdout_enabled is not None and "stream_stdout_enabled" in params:
        step_kwargs["stream_stdout_enabled"] = stream_stdout_enabled
    return step_kwargs


def _persist_step_outputs(
    *,
    deps: StepCliDeps,
    events_path: Path,
    session_path: Path,
    session_newline: str,
    normalized_transcript: str,
    materialized_head_id,
    materialized_lineage: list[dict],
    operator_config,
    append_set: list[dict],
    stdout_set: list[dict],
    stream_state: dict[str, object],
    on_projection_nodes: Callable[[list[dict]], None] | None = None,
    on_projection_delta: Callable[[str], None] | None = None,
) -> None:
    persistence = persist_step_outputs_runtime(
        events_path=events_path,
        deps=deps,
        session_path=session_path,
        session_newline=session_newline,
        normalized_transcript=normalized_transcript,
        materialized_head_id=materialized_head_id,
        materialized_lineage=materialized_lineage,
        operator_config=operator_config,
        append_set=append_set,
        stdout_set=stdout_set,
        stream_state=stream_state,
    )
    if on_projection_nodes is not None:
        on_projection_nodes(persistence.projection_nodes)
    if persistence.needs_trailing_newline:
        if on_projection_delta is not None:
            on_projection_delta("\n")
        else:
            print()
    if on_projection_delta is not None:
        rendered = deps.render_output_with_newline_style(
            rendered=deps.render_blocks(persistence.projection_nodes),
            newline="\n",
            apply_newline_style_fn=deps.apply_newline_style,
        )
        if rendered:
            on_projection_delta(rendered)
    else:
        deps.print_blocks_with_newline(persistence.projection_nodes, "\n")


def run_step(
    *,
    generate_override: Callable[[list[dict]], dict] | None = None,
    preview: bool = False,
    preview_request_pretty: bool = False,
    preview_response: bool = False,
    stdin_mode: bool = False,
    control: str | None = None,
    session_path: str | None = None,
    stream_stdout_enabled: bool | None = None,
    stream_thinking_enabled: bool | None = None,
    stream_prompt_progress_enabled: bool | None = None,
    llm_stream_mode: str | None = None,
    debug_prompt_progress_enabled: bool | None = None,
    debug_prompt_progress_file: str | None = None,
    on_llm_answer_delta: Callable[[str], None] | None = None,
    on_llm_reasoning_delta: Callable[[str], None] | None = None,
    on_llm_prompt_progress: Callable[[object], None] | None = None,
    on_llm_stream_open: Callable[[Callable[[], None]], None] | None = None,
    on_llm_completion: Callable[[GenerationCompletion], None] | None = None,
    on_projection_nodes: Callable[[list[dict]], None] | None = None,
    on_projection_delta: Callable[[str], None] | None = None,
    infer_from: str | None = None,
) -> None:
    deps = _build_step_cli_deps()
    events_path = deps.resolve_events_path()
    deps.ensure_file(events_path)
    events = read_log(str(events_path))
    resolved_session_path, transcript, normalized_transcript, session_newline = _prepare_session_transcript(
        deps=deps,
        events=events,
        stdin_mode=stdin_mode,
        control=control,
        session_path=session_path,
    )
    turns = parse_transcript(normalized_transcript)
    state_turn_indices = [
        index for index, turn in enumerate(turns)
        if turn.get("role") in {"state", "state-diff"}
    ]
    if state_turn_indices:
        _run_state_step(
            deps=deps,
            events_path=events_path,
            session_path=resolved_session_path,
            normalized_transcript=normalized_transcript,
            session_newline=session_newline,
            events=events,
            turns=turns,
            state_index=state_turn_indices[-1],
            preview=preview,
            preview_request_pretty=preview_request_pretty,
            preview_response=preview_response,
            infer_from=infer_from,
            on_projection_nodes=on_projection_nodes,
            on_projection_delta=on_projection_delta,
            generate_override=generate_override,
            on_llm_answer_delta=on_llm_answer_delta,
            on_llm_reasoning_delta=on_llm_reasoning_delta,
            on_llm_prompt_progress=on_llm_prompt_progress,
            on_llm_stream_open=on_llm_stream_open,
            on_llm_completion=on_llm_completion,
            stream_stdout_enabled=stream_stdout_enabled,
            stream_thinking_enabled=stream_thinking_enabled,
            stream_prompt_progress_enabled=stream_prompt_progress_enabled,
            llm_stream_mode=llm_stream_mode,
            debug_prompt_progress_enabled=debug_prompt_progress_enabled,
            debug_prompt_progress_file=debug_prompt_progress_file,
        )
        return
    if infer_from is not None:
        raise ValueError("--infer-from is only supported in state-oriented transcripts")
    if preview or preview_response:
        raise SystemExit("step --preview currently requires a typed state turn at the transcript frontier")
    runtime_ctx = _build_runtime_context(
        events=events,
        normalized_transcript=normalized_transcript,
        session_path=resolved_session_path,
        workdir=Path.cwd(),
    )
    runtime_ctx["events"] = events

    try:
        operator_config, config_sources, generation_runner, stream_state = _resolve_runtime_generation_context(
            deps=deps,
            events_path=events_path,
            events=events,
        )
        generation_runner.on_llm_answer_delta = on_llm_answer_delta
        generation_runner.on_llm_reasoning_delta = on_llm_reasoning_delta
        generation_runner.on_llm_prompt_progress = on_llm_prompt_progress
        generation_runner.on_llm_stream_open = on_llm_stream_open
        generation_runner.on_llm_completion = on_llm_completion
    except RuntimeError as exc:
        raise SystemExit(f"failed to resolve llm api key: {exc}") from exc

    if stream_stdout_enabled is not None:
        generation_runner.stream_stdout_enabled = stream_stdout_enabled
    if stream_thinking_enabled is not None:
        generation_runner.stream_thinking_enabled = stream_thinking_enabled
    if stream_prompt_progress_enabled is not None:
        generation_runner.stream_prompt_progress_enabled = stream_prompt_progress_enabled
    if llm_stream_mode is not None:
        generation_runner.llm_stream_mode = llm_stream_mode
    if debug_prompt_progress_enabled is not None:
        generation_runner.debug_prompt_progress_enabled = debug_prompt_progress_enabled
    if debug_prompt_progress_file is not None:
        generation_runner.debug_prompt_progress_file = debug_prompt_progress_file

    runtime_ctx["injected_control"] = control is not None
    build_kwargs = {
        "deps": deps,
        "runtime_ctx": runtime_ctx,
        "operator_config": operator_config,
        "config_sources": config_sources,
        "generation_fn": generate_override or generation_runner.generate,
    }
    if stream_stdout_enabled is not None:
        build_kwargs["stream_stdout_enabled"] = stream_stdout_enabled
    step_kwargs = _build_step_kwargs(**build_kwargs)

    append_set, stdout_set = deps.step_fn(normalized_transcript, runtime_ctx["log"], **step_kwargs)
    _persist_step_outputs(
        deps=deps,
        events_path=events_path,
        session_path=resolved_session_path,
        session_newline=session_newline,
        normalized_transcript=normalized_transcript,
        materialized_head_id=runtime_ctx["head_id"],
        materialized_lineage=runtime_ctx["lineage"],
        operator_config=operator_config,
        append_set=append_set,
        stdout_set=stdout_set,
        stream_state=stream_state,
        on_projection_nodes=on_projection_nodes,
        on_projection_delta=on_projection_delta,
    )


def _resolve_state_input_turns(
    *, deps, events_path: Path, session_path: Path, session_newline: str,
    normalized_transcript: str,
    prefix_turns: list[dict] | None = None,
    state_turn: dict | None = None,
    input_turns: list[dict] | None = None,
    parsed_turn: dict | None = None,
    on_projection_nodes: Callable[[list[dict]], None] | None = None,
    on_projection_delta: Callable[[str], None] | None = None,
) -> tuple[str, list[dict], list[dict], bool]:
    """Resolve appended USER/CONTROL turns through the ordinary step runtime."""
    from . import step as step_mod
    from .graph import read_log as read_current_log
    from .runtime.rendering_edges import render_transcript_blocks
    from .runtime.state_step import partition_state_transcript
    from .runtime.step_runtime import _frontier_has_callable_intent

    if prefix_turns is None or state_turn is None or input_turns is None:
        p_turns, s_turn, suf_turns = partition_state_transcript(normalized_transcript)
        prefix_turns = prefix_turns if prefix_turns is not None else p_turns
        state_turn = state_turn if state_turn is not None else s_turn
        input_turns = input_turns if input_turns is not None else [
            turn for turn in suf_turns if turn.get("role") in {"user", "control"}
        ]

    resolved_input_turns = [dict(turn) for turn in input_turns]
    if not resolved_input_turns:
        return normalized_transcript, resolved_input_turns, read_current_log(str(events_path)), False

    from .runtime.state_step import materialize_state_turns, reconcile_state_lineage

    if events_path.exists() and state_turn and "role" in state_turn:
        reconciliation = reconcile_state_lineage(
            events=read_current_log(str(events_path)),
            transcript_turns=[*prefix_turns, state_turn],
            state_index=len(prefix_turns),
        )
        if reconciliation.unmaterialized_turns:
            materialize_state_turns(
                events_path=events_path,
                unmaterialized_turns=reconciliation.unmaterialized_turns,
                parent_id=reconciliation.parent_id,
            )

    prefix_and_state = [*prefix_turns, state_turn] if state_turn and "role" in state_turn else list(prefix_turns)
    intent_resolved = False

    index = 0
    while index < len(resolved_input_turns):
        turn = resolved_input_turns[index]
        content_stripped = turn.get("content", "").lstrip()
        if content_stripped.startswith("## RESULT"):
            index += 1
            continue
        if index + 1 < len(resolved_input_turns) and resolved_input_turns[index + 1].get("content", "").lstrip().startswith("## RESULT"):
            index += 1
            continue

        step_input_turns = [
            t for t in resolved_input_turns[: index + 1]
            if not t.get("content", "").lstrip().startswith("## RESULT")
        ]
        step_working = [*prefix_and_state, *step_input_turns]
        ordinary_transcript = render_transcript(step_working, spaced=True)
        events = read_current_log(str(events_path))
        runtime_ctx = _build_runtime_context(
            events=events,
            normalized_transcript=ordinary_transcript,
            session_path=session_path,
            workdir=Path.cwd(),
        )
        runtime_ctx["events"] = events
        operator_config, config_sources, generation_runner, stream_state = (
            _resolve_runtime_generation_context(
                deps=deps, events_path=events_path, events=events
            )
        )
        if isinstance(stream_state, dict):
            stream_state.setdefault("enabled", False)
            stream_state.setdefault("emitted", False)
            stream_state.setdefault("ends_with_newline", True)
        step_kwargs = _build_step_kwargs(
            deps=deps,
            runtime_ctx=runtime_ctx,
            operator_config=operator_config,
            config_sources=config_sources,
            generation_fn=getattr(generation_runner, "generate", None),
        )
        was_callable = _frontier_has_callable_intent(
            step_mod=step_mod,
            frontier=turn,
            working=step_working,
            config=operator_config,
        )
        if not was_callable:
            index += 1
            continue
        append_set, stdout_set = deps.step_fn(
            ordinary_transcript, runtime_ctx["log"], **step_kwargs
        )
        result_nodes = [node for node in append_set if node.get("role") == "result"]
        intent_resolved = intent_resolved or was_callable or bool(result_nodes) or bool(stdout_set)

        if append_set or stdout_set:
            _persist_step_outputs(
                deps=deps,
                events_path=events_path,
                session_path=session_path,
                session_newline=session_newline,
                normalized_transcript=ordinary_transcript,
                materialized_head_id=runtime_ctx["head_id"],
                materialized_lineage=runtime_ctx["lineage"],
                operator_config=operator_config,
                append_set=append_set,
                stdout_set=stdout_set,
                stream_state=stream_state,
                on_projection_nodes=on_projection_nodes,
                on_projection_delta=on_projection_delta,
            )

        if result_nodes:
            rendered_results = render_transcript_blocks(result_nodes)
            result_turns = parse_transcript(rendered_results)
            resolved_input_turns = (
                resolved_input_turns[: index + 1]
                + [dict(item) for item in result_turns]
                + resolved_input_turns[index + 1 :]
            )
            normalized_transcript = render_transcript(
                [*prefix_turns, state_turn, *resolved_input_turns], spaced=True
            )
            index += len(result_turns) + 1
        else:
            index += 1

    return normalized_transcript, resolved_input_turns, read_current_log(str(events_path)), intent_resolved


def _preview_request_display(request: Any, *, pretty: bool) -> str:
    if not pretty:
        return json.dumps(request, ensure_ascii=False, indent=2)

    def unpack_json_strings(value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped[:1] in {"[", "{"}:
                try:
                    return unpack_json_strings(json.loads(stripped))
                except (json.JSONDecodeError, ValueError):
                    return value
            return value
        if isinstance(value, list):
            return [unpack_json_strings(item) for item in value]
        if isinstance(value, dict):
            return {key: unpack_json_strings(item) for key, item in value.items()}
        return value

    return json.dumps(unpack_json_strings(request), ensure_ascii=False, indent=2)


def _run_state_step(*, deps, events_path: Path, session_path: Path, normalized_transcript: str,
                    session_newline: str, events: list[dict],
                    turns: list[dict] | None = None, state_index: int | None = None,
                    parsed_turn: dict | None = None,
                    preview: bool = False, preview_request_pretty: bool = False, preview_response: bool = False,
                    infer_from: str | None = None,
                    on_projection_nodes: Callable[[list[dict]], None] | None = None,
                    on_projection_delta: Callable[[str], None] | None = None,
                    generate_override: Callable[..., Any] | None = None,
                    on_llm_answer_delta: Callable[[str], None] | None = None,
                    on_llm_reasoning_delta: Callable[[str], None] | None = None,
                    on_llm_prompt_progress: Callable[[object], None] | None = None,
                    on_llm_stream_open: Callable[[Callable[[], None]], None] | None = None,
                    on_llm_completion: Callable[[GenerationCompletion], None] | None = None,
                    stream_stdout_enabled: bool | None = None,
                    stream_thinking_enabled: bool | None = None,
                    stream_prompt_progress_enabled: bool | None = None,
                    llm_stream_mode: str | None = None,
                    debug_prompt_progress_enabled: bool | None = None,
                    debug_prompt_progress_file: str | None = None) -> None:
    """Adapt a typed state transcript to the independent state-step runtime."""
    from .tools_cluster.rendering import active_single_turn_ephemeral

    with active_single_turn_ephemeral(True):
        return _run_state_step_impl(
            deps=deps,
            events_path=events_path,
            session_path=session_path,
            normalized_transcript=normalized_transcript,
            session_newline=session_newline,
            events=events,
            turns=turns,
            state_index=state_index,
            parsed_turn=parsed_turn,
            preview=preview,
            preview_request_pretty=preview_request_pretty,
            preview_response=preview_response,
            infer_from=infer_from,
            on_projection_nodes=on_projection_nodes,
            on_projection_delta=on_projection_delta,
            generate_override=generate_override,
            on_llm_answer_delta=on_llm_answer_delta,
            on_llm_reasoning_delta=on_llm_reasoning_delta,
            on_llm_prompt_progress=on_llm_prompt_progress,
            on_llm_stream_open=on_llm_stream_open,
            on_llm_completion=on_llm_completion,
            stream_stdout_enabled=stream_stdout_enabled,
            stream_thinking_enabled=stream_thinking_enabled,
            stream_prompt_progress_enabled=stream_prompt_progress_enabled,
            llm_stream_mode=llm_stream_mode,
            debug_prompt_progress_enabled=debug_prompt_progress_enabled,
            debug_prompt_progress_file=debug_prompt_progress_file,
        )


def _run_state_step_impl(*, deps, events_path: Path, session_path: Path, normalized_transcript: str,
                         session_newline: str, events: list[dict],
                         turns: list[dict] | None = None, state_index: int | None = None,
                         parsed_turn: dict | None = None,
                         preview: bool = False, preview_request_pretty: bool = False, preview_response: bool = False,
                         infer_from: str | None = None,
                         on_projection_nodes: Callable[[list[dict]], None] | None = None,
                         on_projection_delta: Callable[[str], None] | None = None,
                         generate_override: Callable[..., Any] | None = None,
                         on_llm_answer_delta: Callable[[str], None] | None = None,
                         on_llm_reasoning_delta: Callable[[str], None] | None = None,
                         on_llm_prompt_progress: Callable[[object], None] | None = None,
                         on_llm_stream_open: Callable[[Callable[[], None]], None] | None = None,
                         on_llm_completion: Callable[[GenerationCompletion], None] | None = None,
                         stream_stdout_enabled: bool | None = None,
                         stream_thinking_enabled: bool | None = None,
                         stream_prompt_progress_enabled: bool | None = None,
                         llm_stream_mode: str | None = None,
                         debug_prompt_progress_enabled: bool | None = None,
                         debug_prompt_progress_file: str | None = None) -> None:
    """Adapt a typed state transcript to the independent state-step runtime."""
    from . import step as step_mod
    from .config import apply_overrides, config_from_discovered_paths
    from .graph import active_config_overrides, append_state_step_records, state_step_records
    from .runtime.state_step import (
        ToolOutcomeError,
        _merge_patch,
        find_lineage_state_snapshot,
        find_state_turn_index_by_label,
        materialize_state_turns,
        observation_with_user_turns,
        parse_infer_from_directive,
        parse_state_turn,
        parse_sync_directive,
        partition_state_transcript,
        preview_state_request,
        reconcile_state_lineage,
        render_state_turn,
        step_state,
        write_state_key_designations,
    )

    if turns is None or state_index is None:
        prefix_turns, state_turn, suffix_turns = partition_state_transcript(normalized_transcript)
        turns = [*prefix_turns, state_turn, *suffix_turns]
        state_index = len(prefix_turns)
    else:
        prefix_turns = turns[:state_index]
        state_turn = turns[state_index]
        suffix_turns = turns[state_index + 1 :]

    if parsed_turn is None:
        parsed_turn = parse_state_turn(state_turn)

    current_events = read_log(str(events_path)) if events_path.exists() else events
    reconciliation = reconcile_state_lineage(
        events=current_events,
        transcript_turns=turns,
        state_index=state_index,
    )
    current_state_message_id = None
    if reconciliation.lineage and state_index < len(reconciliation.lineage):
        current_state_message_id = reconciliation.lineage[state_index].get("id")
    if not preview and not preview_response:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        if not events_path.exists():
            events_path.touch()
        if reconciliation.unmaterialized_turns:
            materialized = materialize_state_turns(
                events_path=events_path,
                unmaterialized_turns=reconciliation.unmaterialized_turns,
                parent_id=reconciliation.parent_id,
            )
            if materialized:
                current_state_message_id = materialized[-1]["id"]
                current_events = read_log(str(events_path))
                events = current_events
        elif reconciliation.lineage and state_index < len(reconciliation.lineage):
            current_state_message_id = reconciliation.lineage[state_index].get("id")

    if parsed_turn["turn_type"] == "state":
        current_state = parsed_turn["state"]
        if parsed_turn.get("state_number", 1) == 1:
            snapshots = [s for s in state_step_records(str(events_path)) if s.get("kind") == "state_snapshot"]
            has_snapshot = any(
                s.get("message_id") == current_state_message_id
                or (s.get("message_id") is None and s.get("state") == current_state)
                for s in snapshots
            )
            if not has_snapshot and current_state_message_id and not preview and not preview_response:
                append_state_step_records(
                    str(events_path),
                    [{"kind": "state_snapshot", "transition_id": f"seed_{current_state_message_id}", "state": current_state, "message_id": current_state_message_id}],
                )
    else:
        snapshot = find_lineage_state_snapshot(
            events_path=events_path,
            events=current_events,
            lineage=reconciliation.lineage[:state_index] if reconciliation else None,
        )
        if snapshot is None:
            raise ValueError("state-diff turn has no earlier accepted state snapshot")
        current_state = _merge_patch(snapshot["state"], parsed_turn["state_patch"])
    input_turns = [turn for turn in suffix_turns if turn.get("role") in {"user", "control"}]
    directive_infer_from, cleaned_input_turns = (
        parse_infer_from_directive(input_turns) if input_turns else (None, input_turns)
    )
    directive_sync, cleaned_input_turns = (
        parse_sync_directive(cleaned_input_turns) if cleaned_input_turns else (False, cleaned_input_turns)
    )
    if directive_sync:
        all_state_turns = [t for t in [*prefix_turns, state_turn] if t.get("role") in {"state", "state-diff"}]
        key_designations = {}
        for st_turn in all_state_turns:
            parsed = parse_state_turn(st_turn)
            key_designations[parsed["handle"]] = parsed["is_key"]
        if all_state_turns:
            first_parsed = parse_state_turn(all_state_turns[0])
            key_designations[first_parsed["handle"]] = True
        write_state_key_designations(events_path, key_designations)
        print(f"[OK] synchronized transcript state: {key_designations}")
        return

    effective_infer_from = infer_from or directive_infer_from
    cleaned_all_turns = [*prefix_turns, state_turn, *(cleaned_input_turns or [])]
    if effective_infer_from:
        find_state_turn_index_by_label(cleaned_all_turns, effective_infer_from)
    current_observation = observation_with_user_turns(
        parsed_turn.get("observation"), cleaned_input_turns
    ) if cleaned_input_turns else parsed_turn.get("observation")
    request = None
    if preview or preview_response:
        if cleaned_input_turns:
            from .runtime.step_runtime import _frontier_has_callable_intent

            preview_config = apply_overrides(
                config_from_discovered_paths(workdir=Path.cwd()),
                active_config_overrides(events),
            )
            prefix_messages = [turn for turn in prefix_turns if turn.get("role") not in {"state", "state-diff"}]
            has_unresolved = False
            for index, turn in enumerate(cleaned_input_turns):
                content_stripped = turn.get("content", "").lstrip()
                if content_stripped.startswith("## RESULT"):
                    continue
                if index + 1 < len(cleaned_input_turns) and cleaned_input_turns[index + 1].get("content", "").lstrip().startswith("## RESULT"):
                    continue
                if _frontier_has_callable_intent(
                    step_mod=step_mod,
                    frontier=turn,
                    working=[*prefix_messages, *cleaned_input_turns[: index + 1]],
                    config=preview_config,
                ):
                    has_unresolved = True
                    break
            if has_unresolved:
                print(json.dumps({
                    "phase": "resolve_user_intent",
                    "status": "input_turns_have_unresolved_executable_intent",
                }, ensure_ascii=False, indent=2))
                return
        request = preview_state_request(
            events_path=events_path,
            state=current_state,
            observation=current_observation,
            instructions=parsed_turn.get("instructions"),
            protocol=parsed_turn.get("protocol"),
            session_text=normalized_transcript,
            infer_from=effective_infer_from,
            transcript_turns=cleaned_all_turns if effective_infer_from else None,
            pending_tool_calls=[] if cleaned_input_turns else parsed_turn.get("pending_tools"),
            state_message_id=current_state_message_id,
        )
        if request.get("phase") != "infer":
            print(_preview_request_display(request, pretty=preview_request_pretty))
            return
        if preview:
            print(_preview_request_display(request, pretty=preview_request_pretty))
        if not preview_response:
            return
    if cleaned_input_turns and not preview and not preview_response:
        normalized_transcript, cleaned_input_turns, events, intent_resolved = _resolve_state_input_turns(
            deps=deps,
            events_path=events_path,
            session_path=session_path,
            session_newline=session_newline,
            normalized_transcript=normalized_transcript,
            prefix_turns=prefix_turns,
            state_turn=state_turn,
            input_turns=cleaned_input_turns,
            on_projection_nodes=on_projection_nodes,
            on_projection_delta=on_projection_delta,
        )
        if intent_resolved:
            return
        cleaned_all_turns = [*prefix_turns, state_turn, *(cleaned_input_turns or [])]
        current_observation = observation_with_user_turns(
            parsed_turn.get("observation"), cleaned_input_turns
        ) if cleaned_input_turns else parsed_turn.get("observation")
    runtime_ctx = _build_runtime_context(
        events=events, normalized_transcript=normalized_transcript,
        session_path=session_path, workdir=Path.cwd(),
    )
    operator_config = apply_overrides(
        config_from_discovered_paths(workdir=Path.cwd()), active_config_overrides(events)
    )
    generation_runner = None

    def generate_state_packet(packet: dict, **kwargs: Any) -> dict:
        nonlocal generation_runner
        if generate_override is not None:
            try:
                return generate_override(packet, **kwargs)
            except TypeError:
                return generate_override(packet)
        if generation_runner is None:
            _, _, generation_runner, _ = _resolve_runtime_generation_context(
                deps=deps, events_path=events_path, events=events
            )
            generation_runner.on_llm_answer_delta = on_llm_answer_delta
            generation_runner.on_llm_reasoning_delta = on_llm_reasoning_delta
            generation_runner.on_llm_prompt_progress = on_llm_prompt_progress
            generation_runner.on_llm_stream_open = on_llm_stream_open
            generation_runner.on_llm_completion = on_llm_completion
            if stream_stdout_enabled is not None:
                generation_runner.stream_stdout_enabled = stream_stdout_enabled
            if stream_thinking_enabled is not None:
                generation_runner.stream_thinking_enabled = stream_thinking_enabled
            if stream_prompt_progress_enabled is not None:
                generation_runner.stream_prompt_progress_enabled = stream_prompt_progress_enabled
            if llm_stream_mode is not None:
                generation_runner.llm_stream_mode = llm_stream_mode
            if debug_prompt_progress_enabled is not None:
                generation_runner.debug_prompt_progress_enabled = debug_prompt_progress_enabled
            if debug_prompt_progress_file is not None:
                generation_runner.debug_prompt_progress_file = debug_prompt_progress_file
        try:
            return generation_runner.generate_state_packet(packet, **kwargs)
        except TypeError:
            return generation_runner.generate_state_packet(packet)

    if preview_response:
        assert request is not None
        packet = json.loads(request["request_messages"][0]["content"])
        answer = generate_state_packet(
            packet,
            on_delta=on_llm_answer_delta,
            on_reasoning_delta=on_llm_reasoning_delta,
            on_prompt_progress=on_llm_prompt_progress,
        )
        model_call = answer.get("_llm_call")
        if isinstance(model_call, dict):
            write_llm_call_record(str(events_path), **model_call)
        content = answer.get("content")
        if isinstance(content, str):
            print(content, end="")
        return

    def execute_call(call: dict) -> list[dict]:
        results = step_mod._execute_plan(
            [call], origin_role="assistant", command_cwd=runtime_ctx["command_cwd"],
            workspace_mode=runtime_ctx["workspace_mode"], workspace_roots=runtime_ctx["workspace_roots"],
            env_modifiers=step_mod.resolve_effective_env_modifiers([]),
            shell_allowed_commands=step_mod.resolve_effective_shell_allowed([], operator_config, events),
            assistant_timeout_s=operator_config.shell.assistant_timeout_s,
            assistant_timeout_source="default",
        )
        for result in results:
            payload = result.get("payload")
            if not isinstance(payload, dict):
                continue
            outcome = payload.get("outcome", payload.get("status"))
            if outcome in {"cancelled", "indeterminate"}:
                raise ToolOutcomeError(
                    str(outcome),
                    str(payload.get("summary", outcome)),
                    tool_name=payload.get("tool_name"),
                    traceback=payload.get("traceback"),
                )
            if payload.get("ok") is False:
                raise ToolOutcomeError(
                    "failed",
                    str(payload.get("summary", "tool call failed")),
                    tool_name=payload.get("tool_name"),
                    traceback=payload.get("traceback"),
                )
        return results


    from .graph import _next_message_id
    inferred_message_id = _next_message_id(read_log(str(events_path))) if events_path.exists() else "n1"

    try:
        result = step_state(
            events_path=events_path, state=current_state, observation=current_observation,
            instructions=parsed_turn.get("instructions"),
            protocol=parsed_turn.get("protocol"),
            session_text=normalized_transcript,
            pending_tool_calls=[] if cleaned_input_turns else parsed_turn.get("pending_tools"),
            continue_on_error=bool(parsed_turn.get("continue_on_error", False)),
            generate=generate_state_packet, execute_call=execute_call,
            message_id=inferred_message_id,
            state_message_id=current_state_message_id,
            infer_from=effective_infer_from,
            transcript_turns=cleaned_all_turns if effective_infer_from else None,
            on_delta=on_llm_answer_delta,
            on_reasoning_delta=on_llm_reasoning_delta,
            on_prompt_progress=on_llm_prompt_progress,
        )
    except ValueError as exc:
        diagnostic = f"[ERROR] {exc}"
        rendered_results = f"## TOAS:USER\n\n## RESULT\n\n{diagnostic}"
        transcript = normalized_transcript
        prefix = ""
        if transcript and not transcript.endswith(("\n", "\r")):
            prefix += "\n"
        if transcript and not (transcript + prefix).endswith("\n\n"):
            prefix += "\n"
        output_chunk = prefix + rendered_results + "\n"
        if on_projection_delta is not None:
            on_projection_delta(output_chunk)
        else:
            print(output_chunk, end="")
        raise
    if result["phase"] == "infer":
        prior_state_number = parsed_turn.get("state_number", 1)
        prior_handle = parsed_turn.get("handle") or str(prior_state_number)
        tool_calls = result.get("tool_calls") or None
        if prior_handle and not prior_handle.isdigit() and not prior_handle.upper().startswith("STATE/"):
            ref_handle = prior_handle
        else:
            ref_handle = f"STATE/{prior_state_number}"
        rendered = render_state_turn(
            result["state"], observation=None,
            format=parsed_turn.get("format", "yaml"),
            protocol={"ref": ref_handle},
            pending_tools=tool_calls,
            continue_on_error=result.get("continue_on_error"),
            state_number=prior_state_number + 1,
            outcome=result.get("outcome") if result.get("outcome") == "complete" else None,
            report=result.get("report"),
        )
        if not preview and not preview_response:
            inferred_parsed = parse_transcript(rendered)
            if inferred_parsed:
                inferred_turn = dict(inferred_parsed[0])
                inferred_turn["id"] = inferred_message_id
                inferred_parent_id = current_state_message_id
                if reconciliation.lcp > state_index + 1 and reconciliation.lineage:
                    candidate_id = reconciliation.lineage[reconciliation.lcp - 1].get("id")
                    if candidate_id:
                        inferred_parent_id = candidate_id
                materialize_state_turns(
                    events_path=events_path,
                    unmaterialized_turns=[inferred_turn],
                    parent_id=inferred_parent_id,
                )
        transcript = normalized_transcript
        prefix = ""
        if transcript and not transcript.endswith(("\n", "\r")):
            prefix += "\n"
        if transcript and not (transcript + prefix).endswith("\n\n"):
            prefix += "\n"
        output_chunk = prefix + rendered
        if on_projection_delta is not None:
            on_projection_delta(output_chunk)
        else:
            print(output_chunk, end="")
    elif result["phase"] == "execute_batch" or result.get("phase") == "terminal":
        if result.get("phase") == "terminal":
            msg = f"[{result.get('status', 'completed').upper()}] state goal completed"
            report_text = result.get("report")
            if report_text:
                msg += f"\n\n{report_text}"
            rendered_results = "## TOAS:USER\n\n## RESULT\n\n" + msg
        else:
            result_nodes = [
                node for outcome in result.get("outcomes", [])
                for node in (outcome.get("result") or [])
                if isinstance(node, dict) and node.get("role") == "result"
            ]
            outcome_failure_lines = []
            for outcome in result.get("outcomes", []):
                if outcome.get("status") != "completed":
                    idx = outcome.get("index", 0)
                    st = outcome.get("status", "failed")
                    tname = outcome.get("tool_name")
                    tool_label = f"tool {idx} ({tname})" if tname else f"tool {idx}"
                    err = outcome.get("error")
                    summary = err or f"status={st}"
                    outcome_failure_lines.append(f"[{st.upper()}] {tool_label}: {summary}")

            if result_nodes:
                from .runtime.rendering_edges import render_transcript_blocks
                rendered_results = render_transcript_blocks(result_nodes).strip()
                if outcome_failure_lines:
                    rendered_results += "\n\n" + "\n".join(outcome_failure_lines)
                if on_projection_nodes is not None:
                    on_projection_nodes(result_nodes)
            else:
                outcome_lines = []
                for outcome in result.get("outcomes", []):
                    idx = outcome.get("index", 0)
                    st = outcome.get("status", "failed")
                    tname = outcome.get("tool_name")
                    tool_label = f"tool {idx} ({tname})" if tname else f"tool {idx}"
                    err = outcome.get("error")
                    summary = err or f"status={st}"
                    outcome_lines.append(f"[{st.upper()}] {tool_label}: {summary}")
                if not outcome_lines:
                    outcome_lines = [f"[{result.get('status', 'completed').upper()}] batch execution completed"]
                rendered_results = "## TOAS:USER\n\n## RESULT\n\n" + "\n".join(outcome_lines)

        transcript = normalized_transcript
        prefix = ""
        if transcript and not transcript.endswith(("\n", "\r")):
            prefix += "\n"
        if transcript and not (transcript + prefix).endswith("\n\n"):
            prefix += "\n"
        output_chunk = prefix + rendered_results + "\n"
        if on_projection_delta is not None:
            on_projection_delta(output_chunk)
        else:
            print(output_chunk, end="")
