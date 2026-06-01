from __future__ import annotations

from pathlib import Path

from ..config import OperatorConfig
from ..graph import (
    extract_plan,
    extract_user_shell_plan,
    write_command_context_record,
    write_command_request_record,
    write_command_result_record,
    write_config_override_record,
    write_execution_queue_record,
    write_lens_artifact_record,
    write_intent_record,
    write_llm_call_record,
    write_message_events,
    write_tool_request_record,
    write_tool_result_record,
    write_workspace_scope_record,
    write_shell_scope_grant_record,
)


def split_append_nodes(
    append_set: list[dict],
    *,
    sanitize_secret_command_content,
    is_transient_projection_node,
) -> tuple[list[dict], list[dict], list[dict]]:
    message_nodes = [node for node in append_set if node["role"] != "result"]
    message_nodes = [
        {**node, "content": sanitize_secret_command_content(str(node.get("content", "")))}
        if node.get("role") == "user"
        else node
        for node in message_nodes
    ]
    persisted_message_nodes = [node for node in message_nodes if not is_transient_projection_node(node)]
    result_nodes = [node for node in append_set if node["role"] == "result"]
    return message_nodes, persisted_message_nodes, result_nodes


def persist_messages_and_llm_calls(events_path: Path, persisted_message_nodes: list[dict]) -> list[dict]:
    materialized = write_message_events(str(events_path), persisted_message_nodes)
    for orig_node, mat_node in zip(persisted_message_nodes, materialized, strict=False):
        llm_call_data = orig_node.get("_llm_call")
        if llm_call_data is not None:
            write_llm_call_record(str(events_path), message_id=mat_node["id"], **llm_call_data)
    return materialized


def stitch_frontier_records(
    *,
    events_path: Path,
    materialized: list[dict],
    operator_config: OperatorConfig,
    result_nodes: list[dict],
    head_id: str | None,
    lineage: list[dict],
    extract_operator_command_tail,
) -> list[dict]:
    synthetic_stdout_prefix: list[dict] = []
    if not materialized:
        return synthetic_stdout_prefix
    frontier = materialized[-1]
    plan = extract_plan(
        frontier["content"],
        yaml_position=operator_config.extraction.yaml_position,
    ) or extract_user_shell_plan(frontier["content"])
    operator = extract_operator_command_tail(frontier["content"])
    if plan is not None and result_nodes:
        write_tool_request_record(str(events_path), message_id=frontier["id"], plan=plan)
        for node in result_nodes:
            write_tool_result_record(
                str(events_path),
                message_id=frontier["id"],
                payload=node.get("payload", {"content": node["content"]}),
            )
        return synthetic_stdout_prefix
    if frontier["role"] != "user" or operator is None or not result_nodes:
        return synthetic_stdout_prefix
    command, args = operator
    request = write_command_request_record(
        str(events_path),
        command=command,
        args=args,
        related_to=frontier["id"],
        target_head_id=head_id,
    )
    request_id = request["payload"]["id"]
    for node in result_nodes:
        write_command_result_record(
            str(events_path),
            request_id=request_id,
            ok=not str(node["content"]).startswith("[ERROR]"),
            content=node["content"],
            context_update=node.get("context_update"),
            workspace_update=node.get("workspace_update"),
        )
    replay_like_nodes = [
        node
        for node in result_nodes
        if isinstance(node.get("extract_execution"), dict) or isinstance(node.get("replay_execution"), dict)
    ]
    if replay_like_nodes:
        tool_request_written: set[str] = set()
        for node in replay_like_nodes:
            execution = node.get("extract_execution") or node.get("replay_execution")
            if not isinstance(execution, dict):
                continue
            target_index = execution.get("target_message_index")
            request_plan = execution.get("request_plan")
            if not isinstance(target_index, int) or not isinstance(request_plan, list):
                continue
            if target_index < 1 or target_index > len(lineage):
                continue
            target_id = lineage[target_index - 1]["id"]
            if target_id not in tool_request_written:
                write_tool_request_record(str(events_path), message_id=target_id, plan=request_plan)
                tool_request_written.add(target_id)
            write_tool_result_record(
                str(events_path),
                message_id=target_id,
                payload=node.get("payload", {"content": node["content"]}),
            )
    return synthetic_stdout_prefix


def apply_result_side_effects(
    *,
    events_path: Path,
    result_nodes: list[dict],
    operator_config: OperatorConfig,
    session_path: Path,
    session_newline: str,
    runtime_secrets: dict[str, str],
    serialize_operator_config_toml,
    write_text_with_newline_style,
    apply_newline_style,
) -> None:
    _apply_queue_updates(events_path=events_path, result_nodes=result_nodes)
    _apply_lens_updates(events_path=events_path, result_nodes=result_nodes)
    _apply_intent_updates(events_path=events_path, result_nodes=result_nodes)
    _apply_context_updates(events_path=events_path, result_nodes=result_nodes)
    _apply_workspace_updates(events_path=events_path, result_nodes=result_nodes)
    _apply_secret_updates(result_nodes=result_nodes, runtime_secrets=runtime_secrets)
    _apply_config_updates(events_path=events_path, result_nodes=result_nodes)
    _apply_shell_scope_updates(events_path=events_path, result_nodes=result_nodes)
    _apply_config_saves(
        result_nodes=result_nodes,
        operator_config=operator_config,
        serialize_operator_config_toml=serialize_operator_config_toml,
    )
    _apply_session_updates(
        result_nodes=result_nodes,
        session_path=session_path,
        session_newline=session_newline,
        write_text_with_newline_style=write_text_with_newline_style,
        apply_newline_style=apply_newline_style,
    )


def _apply_queue_updates(*, events_path: Path, result_nodes: list[dict]) -> None:
    for node in result_nodes:
        queue_update = node.get("queue_update")
        if not isinstance(queue_update, dict):
            continue
        queue_id = queue_update.get("id")
        status = queue_update.get("status")
        if not isinstance(queue_id, str) or not queue_id:
            continue
        if not isinstance(status, str) or not status:
            continue
        write_execution_queue_record(
            str(events_path),
            queue_id=queue_id,
            status=status,
            payload=queue_update,
        )


def _apply_lens_updates(*, events_path: Path, result_nodes: list[dict]) -> None:
    for node in result_nodes:
        lens_update = node.get("lens_update")
        if not isinstance(lens_update, dict):
            continue
        action = lens_update.get("action")
        if action not in {"set", "remove", "reset"}:
            continue
        write_lens_artifact_record(
            str(events_path),
            action=action,
            title=lens_update.get("title") if isinstance(lens_update.get("title"), str) else None,
            distillation=lens_update.get("distillation") if isinstance(lens_update.get("distillation"), str) else None,
            source_pointers=(
                [item for item in lens_update.get("source_pointers", []) if isinstance(item, str)]
                if isinstance(lens_update.get("source_pointers"), list)
                else None
            ),
            use_when=lens_update.get("use_when") if isinstance(lens_update.get("use_when"), str) else None,
        )


def _apply_intent_updates(*, events_path: Path, result_nodes: list[dict]) -> None:
    for node in result_nodes:
        intent_update = node.get("intent_update")
        if not isinstance(intent_update, dict):
            continue
        intent_id = intent_update.get("intent_id")
        title = intent_update.get("title")
        status = intent_update.get("status")
        if not isinstance(intent_id, str) or not intent_id:
            continue
        if not isinstance(title, str) or not title:
            continue
        if not isinstance(status, str) or not status:
            continue
        write_intent_record(
            str(events_path),
            intent_id=intent_id,
            title=title,
            status=status,
            scope=intent_update.get("scope") if isinstance(intent_update.get("scope"), str) else None,
            tags=[tag for tag in intent_update.get("tags", []) if isinstance(tag, str)]
            if isinstance(intent_update.get("tags"), list)
            else None,
            source=intent_update.get("source") if isinstance(intent_update.get("source"), str) else None,
            notes=intent_update.get("notes") if isinstance(intent_update.get("notes"), str) else None,
        )


def _apply_context_updates(*, events_path: Path, result_nodes: list[dict]) -> None:
    for node in result_nodes:
        context_update = node.get("context_update")
        if not isinstance(context_update, dict):
            continue
        cwd = context_update.get("cwd")
        if not isinstance(cwd, str) or not cwd:
            continue
        previous = context_update.get("previous_cwd")
        previous_cwd = previous if isinstance(previous, str) and previous else None
        write_command_context_record(str(events_path), cwd=cwd, previous_cwd=previous_cwd)


def _apply_workspace_updates(*, events_path: Path, result_nodes: list[dict]) -> None:
    for node in result_nodes:
        workspace_update = node.get("workspace_update")
        if not isinstance(workspace_update, dict):
            continue
        mode = workspace_update.get("mode")
        roots = workspace_update.get("roots")
        if mode not in {"strict", "unbounded"} or not isinstance(roots, list):
            continue
        normalized: list[str] = []
        for root in roots:
            if not isinstance(root, str) or not root:
                continue
            candidate = str(Path(root).expanduser().resolve())
            if candidate not in normalized:
                normalized.append(candidate)
        if not normalized:
            continue
        write_workspace_scope_record(str(events_path), mode=mode, roots=normalized)


def _apply_secret_updates(*, result_nodes: list[dict], runtime_secrets: dict[str, str]) -> None:
    for node in result_nodes:
        secret_update = node.get("secret_update")
        if not isinstance(secret_update, dict):
            continue
        key = secret_update.get("key")
        action = secret_update.get("action")
        if key != "llm_api_key":
            continue
        if action == "set":
            value = secret_update.get("value")
            if isinstance(value, str):
                runtime_secrets["llm_api_key"] = value
        elif action == "unset":
            runtime_secrets.pop("llm_api_key", None)


def _apply_config_updates(*, events_path: Path, result_nodes: list[dict]) -> None:
    for node in result_nodes:
        config_update = node.get("config_update")
        if not isinstance(config_update, dict) or not config_update:
            continue
        write_config_override_record(str(events_path), config_update)


def _apply_shell_scope_updates(*, events_path: Path, result_nodes: list[dict]) -> None:
    for node in result_nodes:
        update = node.get("shell_scope_update")
        if not isinstance(update, dict):
            continue
        scope = update.get("scope")
        action = update.get("action")
        grant = update.get("grant")
        if not isinstance(scope, str) or not isinstance(action, str):
            continue
        if action in {"add", "remove", "unset"} and isinstance(grant, str) and grant:
            write_shell_scope_grant_record(str(events_path), scope=scope, action=action, grant=grant)
        elif action == "reset":
            write_shell_scope_grant_record(str(events_path), scope=scope, action=action)


def _apply_config_saves(*, result_nodes: list[dict], operator_config: OperatorConfig, serialize_operator_config_toml) -> None:
    for node in result_nodes:
        config_save = node.get("config_save")
        if not isinstance(config_save, dict):
            continue
        path = config_save.get("path", "toas.toml")
        if not isinstance(path, str) or not path:
            continue
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = (Path.cwd().resolve() / target).resolve()
        rendered = serialize_operator_config_toml(operator_config)
        target.write_text(rendered, encoding="utf-8")


def _apply_session_updates(
    *,
    result_nodes: list[dict],
    session_path: Path,
    session_newline: str,
    write_text_with_newline_style,
    apply_newline_style,
) -> None:
    for node in result_nodes:
        session_update = node.get("session_update")
        if not isinstance(session_update, dict):
            continue
        transcript_update = session_update.get("transcript")
        if not isinstance(transcript_update, str):
            continue
        write_text_with_newline_style(
            path=session_path,
            text=transcript_update,
            newline=session_newline,
            apply_newline_style_fn=apply_newline_style,
        )
