from __future__ import annotations

from .operator_command_context import OperatorCommandContext

_REPLAY_USAGE = "usage: /replay [--dry-run] [--index <n>] [--force]"


def _parse_extract_selection(args: list[str]) -> int | None:
    if len(args) > 1:
        raise ValueError("usage: /extract [index]")
    if not args:
        return None
    try:
        return int(args[0])
    except ValueError as exc:
        raise ValueError("usage: /extract [index]") from exc


def _latest_assistant_target(working: list[dict]) -> tuple[dict, int]:
    for i, message in enumerate(reversed(working[:-1]), start=1):
        if message["role"] == "assistant":
            return message, len(working) - 1 - i + 1
    raise ValueError("no prior assistant message available for /extract")


def _render_extract_candidates(candidates: list[dict], skipped: list[str]) -> list[dict]:
    lines = [
        "extract candidates from latest assistant message:",
        *[f"{i}. {candidate['kind']}\n{candidate['preview']}" for i, candidate in enumerate(candidates, start=1)],
    ]
    if skipped:
        lines.append("skipped callable-looking blocks:")
        lines.extend(skipped)
    content = f"{lines[0]}\n" + "\n".join(lines[1:])
    return [{"role": "result", "content": content}]


def _handle_extract(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    extract_selection = _parse_extract_selection(args)
    target_message, _target_message_index = _latest_assistant_target(context.working)

    candidates, skipped = step_mod._extract_frontier_assistant_candidates(target_message["content"])
    if not candidates:
        if skipped:
            detail = "\n".join(skipped)
            raise ValueError(
                "latest assistant message has no extractable callable intent\n"
                f"skipped callable-looking blocks:\n{detail}"
            )
        raise ValueError("latest assistant message has no extractable callable intent")

    if extract_selection is None:
        return _render_extract_candidates(candidates, skipped)

    if extract_selection < 1 or extract_selection > len(candidates):
        raise ValueError(f"index out of range: {extract_selection}")
    chosen_candidate = candidates[extract_selection - 1]
    chosen = chosen_candidate.get("adopt", chosen_candidate["preview"])
    return [{"role": "user", "content": chosen, "provenance": {"source": "adopted"}}]


def _parse_replay_args(args: list[str]) -> tuple[bool, bool, int | None]:
    dry_run = False
    force = False
    replay_selection: int | None = None
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
                raise ValueError(_REPLAY_USAGE)
            try:
                replay_selection = int(args[i + 1])
            except ValueError as exc:
                raise ValueError(_REPLAY_USAGE) from exc
            i += 2
            continue
        raise ValueError(_REPLAY_USAGE)
    return dry_run, force, replay_selection


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


def _render_replay_candidates(replay_candidates: list[dict], *, dry_run: bool, context: OperatorCommandContext) -> list[dict]:
    if len(replay_candidates) == 1 and not dry_run:
        only = replay_candidates[0]
        status = _candidate_execution_status(only["index"], context=context)
        return [
            {
                "role": "result",
                "content": (
                    f"replay candidate: 1 found ({status})\n"
                    f"1. {only['preview']}\n"
                    "confirm with: /replay --index 1"
                ),
            }
        ]

    lines = ["replay candidates:"]
    for n, replay_candidate in enumerate(replay_candidates, start=1):
        status = _candidate_execution_status(replay_candidate["index"], context=context)
        lines.append(f"{n}. {replay_candidate['preview']} [{status}]")
    lines.append("execute with: /replay --index <n>")
    return [{"role": "result", "content": "\n".join(lines)}]


def _execute_replay_choice(chosen: dict, *, dry_run: bool, step_mod, context: OperatorCommandContext) -> list[dict]:
    if dry_run:
        return [
            {
                "role": "result",
                "content": (
                    f"replay dry-run: would execute candidate {chosen['choice_index']}\n"
                    f"{chosen['preview']}\n"
                    f"target message index: {chosen['index']}\n"
                    "execution context: current command cwd/workspace (not historical)"
                ),
            }
        ]

    executed_nodes = step_mod._as_nodes(context.execute(context.working, chosen["plan"]))
    for node in executed_nodes:
        node["replay_execution"] = {
            "target_message_index": chosen["index"],
            "request_plan": chosen["plan"],
        }
    return executed_nodes


def _handle_replay(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    dry_run, force, replay_selection = _parse_replay_args(args)
    replay_candidates = _collect_replay_candidates(step_mod=step_mod, context=context)
    if not replay_candidates:
        raise ValueError("no replayable callable messages found in history")

    if replay_selection is None:
        return _render_replay_candidates(replay_candidates, dry_run=dry_run, context=context)

    if replay_selection < 1 or replay_selection > len(replay_candidates):
        raise ValueError(f"index out of range: {replay_selection}")
    chosen = dict(replay_candidates[replay_selection - 1])
    chosen["choice_index"] = replay_selection
    if context.already_executed_indices and chosen["index"] in context.already_executed_indices and not force:
        raise ValueError("target already has tool_request records; rerun with --force")
    return _execute_replay_choice(chosen, dry_run=dry_run, step_mod=step_mod, context=context)


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
    return None
