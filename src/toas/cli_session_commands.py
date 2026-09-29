from __future__ import annotations

import inspect
import json
import sys  # noqa: F401
from collections.abc import Callable
from pathlib import Path

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
    from .runtime.state_step import (
        is_state_turn_marker,
        parse_state_turn,
    )

    transcript_markers = [
        line.strip()
        for line in normalized_transcript.splitlines()
        if line.startswith("## TOAS:")
    ]
    if any(is_state_turn_marker(marker) for marker in transcript_markers):
        _run_state_step(
            deps=deps,
            events_path=events_path,
            session_path=resolved_session_path,
            normalized_transcript=normalized_transcript,
            session_newline=session_newline,
            events=events,
            parsed_turn=parse_state_turn(normalized_transcript),
            preview=preview,
            preview_response=preview_response,
            on_projection_nodes=on_projection_nodes,
            on_projection_delta=on_projection_delta,
        )
        return
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


def run_state_seed(*, format: str = "yaml", session_path: str | None = None) -> None:
    """Output a fresh editable state turn with instructions and blank goal to stdout."""
    from .runtime.state_step import seed_state_turn

    rendered = seed_state_turn(format=format)
    print(rendered, end="")


def _state_free_transcript(transcript: str) -> str:
    """Project ordinary transcript turns while omitting typed state blocks."""
    from .runtime.state_step import is_state_turn_marker

    output: list[str] = []
    keep = True
    for line in transcript.splitlines(keepends=True):
        if line.startswith("## TOAS:"):
            keep = not is_state_turn_marker(line.strip())
        if keep:
            output.append(line)
    return "".join(output)


def _resolve_state_input_turns(
    *, deps, events_path: Path, session_path: Path, session_newline: str,
    normalized_transcript: str, parsed_turn: dict,
    on_projection_nodes: Callable[[list[dict]], None] | None = None,
    on_projection_delta: Callable[[str], None] | None = None,
) -> tuple[str, dict, list[dict], bool]:
    """Resolve appended USER/CONTROL turns through the ordinary step runtime."""
    from . import step as step_mod
    from .graph import read_log as read_current_log
    from .runtime.rendering_edges import render_transcript_blocks
    from .runtime.step_runtime import _frontier_has_callable_intent

    from .runtime.state_step import parse_state_turn

    input_turns = [dict(turn) for turn in parsed_turn.get("_input_turns", [])]
    if not input_turns:
        return normalized_transcript, parsed_turn, read_current_log(str(events_path)), False

    suffix = parsed_turn.get("_transcript_suffix", "")
    transcript_body = normalized_transcript[:-len(suffix)] if suffix else normalized_transcript
    prior_messages = parse_transcript(
        _state_free_transcript(parsed_turn.get("_transcript_prefix", ""))
    )
    intent_resolved = False

    index = 0
    while index < len(input_turns):
        turn = input_turns[index]
        content_stripped = turn.get("content", "").lstrip()
        if content_stripped.startswith("## RESULT"):
            index += 1
            continue
        if index + 1 < len(input_turns) and input_turns[index + 1].get("content", "").lstrip().startswith("## RESULT"):
            index += 1
            continue

        ordinary_transcript = render_transcript(
            [*prior_messages, *input_turns[: index + 1]], spaced=True
        )
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
            working=[*prior_messages, *input_turns[: index + 1]],
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

        if result_nodes:
            rendered_results = render_transcript_blocks(result_nodes)
            result_turns = parse_transcript(rendered_results)
            input_turns = (
                input_turns[: index + 1]
                + [dict(item) for item in result_turns]
                + input_turns[index + 1 :]
            )
            transcript_suffix = render_transcript(input_turns, spaced=True)
            normalized_transcript = transcript_body + transcript_suffix
            parsed_turn = parse_state_turn(normalized_transcript)
            input_turns = [dict(item) for item in parsed_turn.get("_input_turns", [])]
            suffix = parsed_turn.get("_transcript_suffix", "")
            transcript_body = normalized_transcript[:-len(suffix)] if suffix else normalized_transcript
            index += len(result_turns) + 1
        else:
            index += 1

    return normalized_transcript, parsed_turn, read_current_log(str(events_path)), intent_resolved


def _run_state_step(*, deps, events_path: Path, session_path: Path, normalized_transcript: str,
                    session_newline: str, events: list[dict], parsed_turn: dict,
                    preview: bool = False, preview_response: bool = False,
                    on_projection_nodes: Callable[[list[dict]], None] | None = None,
                    on_projection_delta: Callable[[str], None] | None = None) -> None:
    """Adapt a typed state transcript to the independent state-step runtime."""
    from . import step as step_mod
    from .config import apply_overrides, config_from_discovered_paths
    from .graph import active_config_overrides, state_step_records
    from .runtime.state_step import (
        ToolOutcomeError,
        _merge_patch,
        preview_state_request,
        parse_state_turn,
        render_state_turn,
        step_state,
        transcript_observation_with_tool_outcomes,
        observation_with_user_turns,
    )

    snapshots = [record for record in state_step_records(str(events_path)) if record.get("kind") == "state_snapshot"]
    if parsed_turn["turn_type"] == "state":
        current_state = parsed_turn["state"]
    else:
        if not snapshots:
            raise ValueError("state-diff turn has no earlier accepted state snapshot")
        current_state = _merge_patch(snapshots[-1]["state"], parsed_turn["state_patch"])
    input_turns = parsed_turn.get("_input_turns", [])
    current_observation = observation_with_user_turns(
        parsed_turn.get("observation"), input_turns
    ) if input_turns else parsed_turn.get("observation")
    request = None
    if preview or preview_response:
        if input_turns:
            from .runtime.step_runtime import _frontier_has_callable_intent

            preview_config = apply_overrides(
                config_from_discovered_paths(workdir=Path.cwd()),
                active_config_overrides(events),
            )
            prefix_messages = parse_transcript(
                _state_free_transcript(parsed_turn.get("_transcript_prefix", ""))
            )
            has_unresolved = False
            for index, turn in enumerate(input_turns):
                content_stripped = turn.get("content", "").lstrip()
                if content_stripped.startswith("## RESULT"):
                    continue
                if index + 1 < len(input_turns) and input_turns[index + 1].get("content", "").lstrip().startswith("## RESULT"):
                    continue
                if _frontier_has_callable_intent(
                    step_mod=step_mod,
                    frontier=turn,
                    working=[*prefix_messages, *input_turns[: index + 1]],
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
            session_text=normalized_transcript,
        )
        if request.get("phase") != "infer":
            print(json.dumps(request, ensure_ascii=False, indent=2))
            return
        if preview:
            print(json.dumps(request, ensure_ascii=False, indent=2))
        if not preview_response:
            return
    if input_turns and not preview and not preview_response:
        normalized_transcript, parsed_turn, events, intent_resolved = _resolve_state_input_turns(
            deps=deps,
            events_path=events_path,
            session_path=session_path,
            session_newline=session_newline,
            normalized_transcript=normalized_transcript,
            parsed_turn=parsed_turn,
            on_projection_nodes=on_projection_nodes,
            on_projection_delta=on_projection_delta,
        )
        if intent_resolved:
            return
        input_turns = parsed_turn.get("_input_turns", [])
        current_observation = observation_with_user_turns(
            parsed_turn.get("observation"), input_turns
        ) if input_turns else parsed_turn.get("observation")
    runtime_ctx = _build_runtime_context(
        events=events, normalized_transcript=normalized_transcript,
        session_path=session_path, workdir=Path.cwd(),
    )
    operator_config = apply_overrides(
        config_from_discovered_paths(workdir=Path.cwd()), active_config_overrides(events)
    )
    generation_runner = None

    def generate_state_packet(packet: dict) -> dict:
        nonlocal generation_runner
        if generation_runner is None:
            _, _, generation_runner, _ = _resolve_runtime_generation_context(
                deps=deps, events_path=events_path, events=events
            )
        return generation_runner.generate_state_packet(packet)

    if preview_response:
        assert request is not None
        packet = json.loads(request["request_messages"][0]["content"])
        answer = generate_state_packet(packet)
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
                raise ToolOutcomeError(str(outcome), str(payload.get("summary", outcome)))
            if payload.get("ok") is False:
                raise ToolOutcomeError("failed", str(payload.get("summary", "tool call failed")))
        return results

    result = step_state(
        events_path=events_path, state=current_state, observation=current_observation,
        instructions=parsed_turn.get("instructions"),
        session_text=normalized_transcript,
        pending_tool_calls=parsed_turn.get("pending_tools"),
        generate=generate_state_packet, execute_call=execute_call,
    )
    if result["phase"] == "infer":
        prior_state_number = parsed_turn.get("state_number", 1)
        tool_calls = result.get("tool_calls") or None
        rendered = render_state_turn(
            result["state"], observation=None,
            format=parsed_turn.get("format", "yaml"),
            instructions=parsed_turn.get("instructions"),
            pending_tools=tool_calls,
            state_number=prior_state_number + 1,
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
    elif result["phase"] == "execute_batch":
        result_nodes = [
            node for outcome in result.get("outcomes", [])
            for node in (outcome.get("result") or [])
            if isinstance(node, dict) and node.get("role") == "result"
        ]
        if result_nodes:
            from .runtime.rendering_edges import render_transcript_blocks
            rendered_results = render_transcript_blocks(result_nodes).strip()
            if on_projection_nodes is not None:
                on_projection_nodes(result_nodes)
        else:
            outcome_lines = []
            for outcome in result.get("outcomes", []):
                idx = outcome.get("index", 0)
                st = outcome.get("status", "failed")
                err = outcome.get("error")
                summary = err or f"status={st}"
                outcome_lines.append(f"[{st.upper()}] tool {idx}: {summary}")
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
