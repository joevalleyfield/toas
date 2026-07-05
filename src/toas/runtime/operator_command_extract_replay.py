from __future__ import annotations

from .operator_command_context import OperatorCommandContext
from .replay_queue_edges import TERMINAL_QUEUE_STATUSES as _TERMINAL_QUEUE_STATUSES
from .replay_queue_edges import entry_for_call as _entry_for_call
from .replay_queue_edges import is_shell_authorization_block as _is_shell_authorization_block
from .replay_queue_edges import iter_queue_payloads as _iter_queue_payloads  # noqa: F401
from .replay_queue_edges import latest_queue_state as _latest_queue_state
from .replay_queue_edges import latest_queue_states_by_id as _latest_queue_states_by_id
from .replay_queue_edges import next_queue_id as _next_queue_id
from .replay_queue_edges import queue_summary as _queue_summary
from .result_nodes import make_result_node

_EXTRACT_USAGE = "usage: /extract [--verbose] [--shape <auto|yaml|shell>] [index]"
_REPLAY_USAGE = "usage: /replay [--dry-run] [--index <n>] [--force]"
_REPLAY_QUEUE_USAGE = (
    "usage: /replay [--dry-run] [--index <n|rN>] [--force] "
    "[--resume <queue_id> | --approve <queue_id> | --skip <queue_id> | --cancel <queue_id>]"
)
_QUEUE_USAGE = "usage: /queue [<queue_id>] [resume|approve|skip|cancel]"


def _result_node(content: str, *, step_mod, context: OperatorCommandContext, **fields) -> dict:
    if "\n" in content:
        lower_content = content.lower()
        if "extract" in lower_content:
            source = "command.extract"
        elif "queue" in lower_content:
            source = "command.queue"
        else:
            source = "command.replay"
        from ..tools_cluster.rendering import render_fenced_output
        content = render_fenced_output(
            content=content,
            kind="view",
            source=source,
            potency="inert",
        )
    return make_result_node(
        content,
        origin_role=context.frontier_role,
        origin_kind="slash_command",
        **fields,
    )


def _format_intent_id(index: int) -> str:
    return f"d{index}"


def _parse_extract_index_token(token: str) -> int:
    raw = token.strip()
    if raw.startswith("#"):
        raw = raw[1:]
    if raw.startswith("d"):
        raw = raw[1:]
    if not raw:
        raise ValueError(_EXTRACT_USAGE)
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(_EXTRACT_USAGE) from exc


def _format_replay_intent_id(index: int) -> str:
    return f"r{index}"


def _parse_replay_index_token(token: str) -> int:
    raw = token.strip()
    if raw.startswith("#"):
        raw = raw[1:]
    if raw.startswith("r"):
        raw = raw[1:]
    if not raw:
        raise ValueError(_REPLAY_QUEUE_USAGE)
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(_REPLAY_QUEUE_USAGE) from exc


def _parse_extract_selection(args: list[str]) -> tuple[int | None, bool, str | None]:
    extract_selection: int | None = None
    verbose = False
    projection_shape: str | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--verbose":
            verbose = True
            i += 1
            continue
        if arg == "--shape":
            if i + 1 >= len(args):
                raise ValueError(_EXTRACT_USAGE)
            shape = args[i + 1].strip().lower()
            if shape not in {"auto", "yaml", "shell"}:
                raise ValueError(_EXTRACT_USAGE)
            projection_shape = shape
            i += 2
            continue
        if extract_selection is not None:
            raise ValueError(_EXTRACT_USAGE)
        extract_selection = _parse_extract_index_token(arg)
        i += 1
    return extract_selection, verbose, projection_shape


def _latest_assistant_target(working: list[dict]) -> tuple[dict, int]:
    for i, message in enumerate(reversed(working[:-1]), start=1):
        if message["role"] == "assistant":
            return message, len(working) - 1 - i + 1
    raise ValueError("no prior assistant message available for /extract")


def _render_extract_candidates(candidates: list[dict], skipped: list[str], *, verbose: bool, step_mod, context: OperatorCommandContext) -> list[dict]:
    lines = [
        "extract candidates from latest assistant message:",
        *[
            f"{i}. {candidate['kind']} [#{_format_intent_id(i)}]\n"
            f"{candidate.get('preview_verbose', candidate['preview']) if verbose else candidate['preview']}"
            for i, candidate in enumerate(candidates, start=1)
        ],
    ]
    if skipped:
        lines.append("skipped callable-looking blocks:")
        lines.extend(skipped)
    content = f"{lines[0]}\n" + "\n".join(lines[1:])
    return [_result_node(content, step_mod=step_mod, context=context)]


def _handle_extract(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    extract_selection, verbose, projection_shape_override = _parse_extract_selection(args)
    target_message, _target_message_index = _latest_assistant_target(context.working)
    projection_shape = projection_shape_override or getattr(context.config.extraction, "projection_shape", "auto")

    candidates, skipped = step_mod._extract_frontier_assistant_candidates(
        target_message["content"],
        projection_shape=projection_shape,
    )
    if not candidates:
        if skipped:
            detail = "\n".join(skipped)
            raise ValueError(
                "latest assistant message has no extractable callable intent\n"
                f"skipped callable-looking blocks:\n{detail}"
            )
        raise ValueError("latest assistant message has no extractable callable intent")

    if extract_selection is None:
        return _render_extract_candidates(candidates, skipped, verbose=verbose, step_mod=step_mod, context=context)

    if extract_selection < 1 or extract_selection > len(candidates):
        raise ValueError(f"index out of range: {extract_selection}")
    chosen_candidate = candidates[extract_selection - 1]
    if verbose:
        chosen = chosen_candidate.get("adopt_verbose", chosen_candidate.get("adopt", chosen_candidate["preview"]))
    else:
        chosen = chosen_candidate.get("adopt", chosen_candidate["preview"])
    return [{"role": "user", "content": chosen, "provenance": {"source": "adopted"}}]


def _parse_replay_args(args: list[str]) -> tuple[bool, bool, int | None, tuple[str, str] | None]:
    dry_run = False
    force = False
    replay_selection: int | None = None
    queue_action: tuple[str, str] | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--dry-run":
            dry_run = True
            i += 1
            continue
        if arg == "--force":
            force = True
            i += 1
            continue
        if arg == "--index":
            if i + 1 >= len(args):
                raise ValueError(_REPLAY_QUEUE_USAGE)
            replay_selection = _parse_replay_index_token(args[i + 1])
            i += 2
            continue
        if arg in {"--resume", "--approve", "--skip", "--cancel"}:
            if i + 1 >= len(args):
                raise ValueError(_REPLAY_QUEUE_USAGE)
            if queue_action is not None:
                raise ValueError(_REPLAY_QUEUE_USAGE)
            queue_id = args[i + 1].strip()
            if not queue_id:
                raise ValueError(_REPLAY_QUEUE_USAGE)
            queue_action = (arg[2:], queue_id)
            i += 2
            continue
        raise ValueError(_REPLAY_QUEUE_USAGE)

    if queue_action is not None and replay_selection is not None:
        raise ValueError(_REPLAY_QUEUE_USAGE)
    if queue_action is not None and dry_run:
        raise ValueError(_REPLAY_QUEUE_USAGE)
    return dry_run, force, replay_selection, queue_action




def _execute_call_for_queue(
    call: dict,
    *,
    as_approved_user_call: bool,
    step_mod,
    context: OperatorCommandContext,
) -> list[dict]:
    if as_approved_user_call:
        return step_mod._execute_plan_user_context(
            [call],
            origin_role=context.frontier_role,
            command_cwd=context.command_cwd,
            workspace_mode=context.workspace_mode,
            workspace_roots=context.workspace_roots,
            env_modifiers=step_mod.resolve_effective_env_modifiers(context.working),
        )
    return step_mod._execute_plan(
        [call],
        origin_role=context.frontier_role,
        command_cwd=context.command_cwd,
        workspace_mode=context.workspace_mode,
        workspace_roots=context.workspace_roots,
        env_modifiers=step_mod.resolve_effective_env_modifiers(context.working),
        shell_allowed_commands=step_mod.resolve_effective_shell_allowed(context.working, context.config),
    )


def _validate_queue_plan_state(queue: dict) -> tuple[list, int]:
    plan = queue.get("plan")
    if not isinstance(plan, list):
        raise ValueError(f"queue {queue.get('id')} is missing plan payload")
    next_index = queue.get("next_index", 0)
    if not isinstance(next_index, int) or next_index < 0 or next_index > len(plan):
        raise ValueError(f"queue {queue.get('id')} has invalid next_index")
    return plan, next_index


def _normalized_queue_entries(queue: dict) -> list[dict]:
    entries = queue.get("entries")
    if not isinstance(entries, list):
        entries = []
    return [dict(entry) for entry in entries if isinstance(entry, dict)]


def _cancel_queue_remaining(queue: dict, *, plan: list, entries: list[dict], next_index: int) -> dict:
    for i in range(next_index, len(plan)):
        entries.append(_entry_for_call(i, plan[i], status="cancelled"))
    queue["entries"] = entries
    queue["status"] = "cancelled"
    queue["next_index"] = len(plan)
    return queue


def _apply_queue_skip(queue: dict, *, plan: list, entries: list[dict], next_index: int) -> int:
    if next_index >= len(plan):
        raise ValueError(f"queue {queue.get('id')} has no pending operation to skip")
    entries.append(_entry_for_call(next_index, plan[next_index], status="skipped"))
    next_index += 1
    queue["entries"] = entries
    queue["next_index"] = next_index
    return next_index


def _queue_step_outcome(nodes: list[dict]) -> str:
    blocked = any(_is_shell_authorization_block(node) for node in nodes if isinstance(node, dict))
    if blocked:
        return "blocked"
    failed = any(
        isinstance(node, dict)
        and isinstance(node.get("payload"), dict)
        and not bool(node["payload"].get("ok", True))
        and not _is_shell_authorization_block(node)
        for node in nodes
    )
    return "failed" if failed else "ran"


def _render_queue_boundary_message(*, queue: dict, plan: list, call: dict, next_index: int) -> str:
    return (
        f"replay queue blocked at operation {next_index + 1}/{len(plan)} ({call.get('tool_name')})\n"
        f"queue id: {queue.get('id')}\n"
        "queue controls:\n"
        "  /queue [resume|approve*|skip|cancel]"
    )


def _run_queue_until_boundary(
    queue: dict,
    *,
    step_mod,
    context: OperatorCommandContext,
    action: str,
) -> tuple[list[dict], dict]:
    plan, next_index = _validate_queue_plan_state(queue)
    entries = _normalized_queue_entries(queue)
    out_nodes: list[dict] = []

    if action == "cancel":
        queue = _cancel_queue_remaining(queue, plan=plan, entries=entries, next_index=next_index)
        out_nodes.append(_result_node(f"replay queue cancelled: {_queue_summary(queue)}", step_mod=step_mod, context=context, queue_update=queue))
        return out_nodes, queue

    if action == "skip":
        next_index = _apply_queue_skip(queue, plan=plan, entries=entries, next_index=next_index)

    approve_index = next_index if action == "approve" else None
    while next_index < len(plan):
        call = plan[next_index]
        nodes = step_mod._as_nodes(
            _execute_call_for_queue(
                call,
                as_approved_user_call=(approve_index is not None and next_index == approve_index),
                step_mod=step_mod,
                context=context,
            )
        )
        out_nodes.extend(nodes)
        outcome = _queue_step_outcome(nodes)
        if outcome == "blocked":
            entries.append(_entry_for_call(next_index, call, status="blocked"))
            queue["entries"] = entries
            queue["status"] = "blocked"
            queue["next_index"] = next_index
            out_nodes.append(
                _result_node(
                    _render_queue_boundary_message(queue=queue, plan=plan, call=call, next_index=next_index),
                    step_mod=step_mod,
                    context=context,
                    queue_update=queue,
                )
            )
            return out_nodes, queue
        if outcome == "failed":
            entries.append(_entry_for_call(next_index, call, status="failed"))
            queue["entries"] = entries
            queue["status"] = "failed"
            queue["next_index"] = next_index + 1
            out_nodes.append(_result_node(f"replay queue failed: {_queue_summary(queue)}", step_mod=step_mod, context=context, queue_update=queue))
            return out_nodes, queue

        ran_status = "approved" if approve_index is not None and next_index == approve_index else "ran"
        entries.append(_entry_for_call(next_index, call, status=ran_status))
        next_index += 1
        queue["entries"] = entries
        queue["next_index"] = next_index

    queue["status"] = "completed"
    out_nodes.append(_result_node(f"replay queue completed: {_queue_summary(queue)}", step_mod=step_mod, context=context, queue_update=queue))
    return out_nodes, queue


def _collect_replay_candidates(*, step_mod, context: OperatorCommandContext) -> list[dict]:
    replay_candidates: list[dict] = []
    for idx, message in enumerate(context.working[:-1], start=1):
        plan, ambiguous = step_mod.extract_plan_with_status(message["content"], yaml_position="any")
        if ambiguous:
            continue
        if plan is not None:
            replay_candidates.append(
                {
                    "index": idx,
                    "kind": "tool_plan",
                    "preview": f"message #{idx} {message['role']}: tool plan",
                    "plan": plan,
                }
            )
            continue
        if message["role"] == "assistant":
            loose_command, _ = step_mod._extract_loose_command(message["content"])
            if loose_command is not None:
                try:
                    argv = step_mod.shlex.split(loose_command)
                except ValueError:
                    continue
                if argv:
                    replay_candidates.append(
                        {
                            "index": idx,
                            "kind": "assistant_loose_command",
                            "preview": f"message #{idx} assistant loose command: $ {loose_command}",
                            "plan": [{"tool_name": "shell", "args": {"argv": argv}}],
                        }
                    )
    return replay_candidates


def _candidate_execution_status(index: int, *, context: OperatorCommandContext) -> str:
    if context.already_executed_indices and index in context.already_executed_indices:
        return "already executed"
    return "not executed"


def _render_replay_candidates(replay_candidates: list[dict], *, dry_run: bool, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(replay_candidates) == 1 and not dry_run:
        only = replay_candidates[0]
        status = _candidate_execution_status(only["index"], context=context)
        return [
            _result_node(
                (
                    f"replay candidate: 1 found ({status})\n"
                    f"1. {only['preview']} [#{_format_replay_intent_id(1)}]\n"
                    "confirm with: /replay --index #r1"
                ),
                step_mod=step_mod,
                context=context,
            )
        ]

    lines = ["replay candidates:"]
    for n, replay_candidate in enumerate(replay_candidates, start=1):
        status = _candidate_execution_status(replay_candidate["index"], context=context)
        lines.append(f"{n}. {replay_candidate['preview']} [#{_format_replay_intent_id(n)}] [{status}]")
    lines.append("execute with: /replay --index <n|rN>")
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context)]


def _execute_replay_choice(chosen: dict, *, dry_run: bool, step_mod, context: OperatorCommandContext) -> list[dict]:
    if dry_run:
        return [
            _result_node(
                (
                    f"replay dry-run: would execute candidate {chosen['choice_index']}\n"
                    f"{chosen['preview']}\n"
                    f"target message index: {chosen['index']}\n"
                    "execution context: current command cwd/workspace (not historical)"
                ),
                step_mod=step_mod,
                context=context,
            )
        ]

    if len(chosen["plan"]) > 1:
        queue = {
            "id": _next_queue_id(context=context),
            "status": "running",
            "next_index": 0,
            "target_message_index": chosen["index"],
            "plan": chosen["plan"],
            "entries": [],
        }
        executed_nodes, _ = _run_queue_until_boundary(queue, step_mod=step_mod, context=context, action="resume")
    else:
        executed_nodes = step_mod._as_nodes(context.execute(context.working, chosen["plan"]))
    for node in executed_nodes:
        node["replay_execution"] = {
            "target_message_index": chosen["index"],
            "request_plan": chosen["plan"],
        }
    return executed_nodes


def _handle_replay_queue_action(queue_action: tuple[str, str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    action, queue_id = queue_action
    queue = _latest_queue_state(queue_id, context=context)
    if queue is None:
        raise ValueError(f"unknown replay queue id: {queue_id}")
    if queue.get("status") in _TERMINAL_QUEUE_STATUSES:
        return [_result_node(f"replay queue already terminal: {_queue_summary(queue)}", step_mod=step_mod, context=context)]
    if action not in {"resume", "approve", "skip", "cancel"}:
        raise ValueError(_REPLAY_QUEUE_USAGE)

    out_nodes, _ = _run_queue_until_boundary(queue, step_mod=step_mod, context=context, action=action)
    for node in out_nodes:
        if isinstance(node, dict):
            node["replay_queue"] = {"id": queue_id, "action": action}
    return out_nodes


def _resolve_default_queue_id(*, context: OperatorCommandContext) -> str:
    active_ids = sorted(
        queue_id
        for queue_id, payload in _latest_queue_states_by_id(context=context).items()
        if payload.get("status") not in _TERMINAL_QUEUE_STATUSES
    )
    if not active_ids:
        raise ValueError("no active replay queue found; run /replay --index <n> first")
    if len(active_ids) > 1:
        raise ValueError("multiple active replay queues; specify queue id (for example: /queue q2 approve)")
    return active_ids[0]


def _parse_queue_args(args: list[str], *, context: OperatorCommandContext) -> tuple[str, str]:
    allowed_actions = {"resume", "approve", "skip", "cancel"}
    action = "approve"
    queue_id: str | None = None
    tokens = [arg.strip() for arg in args if arg.strip()]
    if len(tokens) > 2:
        raise ValueError(_QUEUE_USAGE)
    if len(tokens) == 1:
        token = tokens[0]
        if token in allowed_actions:
            action = token
        elif token.startswith("q"):
            queue_id = token
        else:
            raise ValueError(_QUEUE_USAGE)
    elif len(tokens) == 2:
        first, second = tokens
        if first in allowed_actions and second.startswith("q"):
            action = first
            queue_id = second
        elif first.startswith("q") and second in allowed_actions:
            queue_id = first
            action = second
        else:
            raise ValueError(_QUEUE_USAGE)
    if queue_id is None:
        queue_id = _resolve_default_queue_id(context=context)
    return action, queue_id


def _handle_queue(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    action, queue_id = _parse_queue_args(args, context=context)
    return _handle_replay_queue_action((action, queue_id), step_mod=step_mod, context=context)


def _handle_replay(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    dry_run, force, replay_selection, queue_action = _parse_replay_args(args)
    if queue_action is not None:
        return _handle_replay_queue_action(queue_action, step_mod=step_mod, context=context)

    replay_candidates = _collect_replay_candidates(step_mod=step_mod, context=context)
    if not replay_candidates:
        raise ValueError("no replayable callable messages found in history")

    if replay_selection is None:
        return _render_replay_candidates(replay_candidates, dry_run=dry_run, step_mod=step_mod, context=context)

    if replay_selection < 1 or replay_selection > len(replay_candidates):
        raise ValueError(f"index out of range: {replay_selection}")
    chosen = dict(replay_candidates[replay_selection - 1])
    chosen["choice_index"] = replay_selection
    if context.already_executed_indices and chosen["index"] in context.already_executed_indices and not force:
        raise ValueError("target already has tool_request records; rerun with --force")
    return _execute_replay_choice(chosen, dry_run=dry_run, step_mod=step_mod, context=context)


_HEAL_USAGE = "usage: /heal search_indent=N | /heal POSITION:search_indent=N [...]"


def _parse_heal_args(args: list[str]) -> list[tuple[int | None, int]]:
    if not args:
        raise ValueError(_HEAL_USAGE)
    parsed = []
    for arg in args:
        position = None
        patch = arg
        if ":" in arg:
            position_text, patch = arg.split(":", 1)
            try:
                position = int(position_text)
            except ValueError as exc:
                raise ValueError(_HEAL_USAGE) from exc
            if position < 1:
                raise ValueError(_HEAL_USAGE)
        if not patch.startswith("search_indent="):
            raise ValueError(_HEAL_USAGE)
        try:
            search_indent = int(patch.split("=", 1)[1])
        except ValueError as exc:
            raise ValueError(_HEAL_USAGE) from exc
        if search_indent < 0:
            raise ValueError(_HEAL_USAGE)
        parsed.append((position, search_indent))
    if len(parsed) > 1 and any(position is None for position, _indent in parsed):
        raise ValueError(_HEAL_USAGE)
    positions = [position for position, _indent in parsed if position is not None]
    if len(positions) != len(set(positions)):
        raise ValueError(_HEAL_USAGE)
    return parsed


def _handle_heal(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    repairs = _parse_heal_args(args)

    candidates = _collect_replay_candidates(step_mod=step_mod, context=context)
    if not candidates:
        raise ValueError("no prior callable frontier available to heal")
    plan = candidates[-1]["plan"]
    if repairs[0][0] is None:
        if len(plan) != 1:
            raise ValueError("latest callable frontier has multiple operations; indexed heal required")
        repairs = [(1, repairs[0][1])]
    healed_calls = []
    for position, search_indent in repairs:
        if position is None or position > len(plan):
            raise ValueError("heal operation position is outside the latest callable frontier")
        call = dict(plan[position - 1])
        if call.get("tool_name") != "replace_block":
            raise ValueError(f"operation {position} is not replace_block")
        call_args = call.get("args")
        if not isinstance(call_args, dict):
            raise ValueError(f"replace_block operation {position} has invalid arguments")
        call["args"] = {**call_args, "search_indent": search_indent}
        healed_calls.append(call)
    return step_mod._execute_plan_user_context(
        healed_calls,
        origin_role=context.frontier_role,
        command_cwd=context.command_cwd,
        workspace_mode=context.workspace_mode,
        workspace_roots=context.workspace_roots,
        env_modifiers=step_mod.resolve_effective_env_modifiers(context.working),
    )


def handle_extract_replay_commands(
    command: str,
    args: list[str],
    *,
    step_mod,
    context: OperatorCommandContext,
) -> list[dict] | None:
    if command == "extract":
        return _handle_extract(args, step_mod=step_mod, context=context)
    if command == "replay":
        return _handle_replay(args, step_mod=step_mod, context=context)
    if command == "queue":
        return _handle_queue(args, step_mod=step_mod, context=context)
    if command == "heal":
        return _handle_heal(args, step_mod=step_mod, context=context)
    return None
