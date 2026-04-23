from __future__ import annotations

from .operator_command_context import OperatorCommandContext


def handle_extract_replay_commands(command: str, args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict] | None:
    if command == "extract":
        extract_selection = None
        if len(args) > 1:
            raise ValueError("usage: /extract [index]")
        if args:
            try:
                extract_selection = int(args[0])
            except ValueError as exc:
                raise ValueError("usage: /extract [index]") from exc

        target_message = None
        target_message_index = None
        for i, message in enumerate(reversed(context.working[:-1]), start=1):
            if message["role"] == "assistant":
                target_message = message
                target_message_index = len(context.working) - 1 - i + 1
                break
        if target_message is None or target_message_index is None:
            raise ValueError("no prior assistant message available for /extract")

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
            lines = [
                "extract candidates from latest assistant message:",
                *[f"{i}. {candidate['kind']}\n{candidate['preview']}" for i, candidate in enumerate(candidates, start=1)],
            ]
            if skipped:
                lines.append("skipped callable-looking blocks:")
                lines.extend(skipped)
            content = f"{lines[0]}\n" + "\n".join(lines[1:])
            return [{"role": "result", "content": content}]

        if extract_selection < 1 or extract_selection > len(candidates):
            raise ValueError(f"index out of range: {extract_selection}")
        chosen_candidate = candidates[extract_selection - 1]
        chosen = chosen_candidate.get("adopt", chosen_candidate["preview"])
        return [{"role": "user", "content": chosen, "provenance": {"source": "adopted"}}]

    if command == "replay":
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
                    raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]")
                try:
                    replay_selection = int(args[i + 1])
                except ValueError as exc:
                    raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]") from exc
                i += 2
                continue
            raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]")

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

        if not replay_candidates:
            raise ValueError("no replayable callable messages found in history")

        if replay_selection is None:
            if len(replay_candidates) == 1 and not dry_run:
                only = replay_candidates[0]
                status = "already executed" if context.already_executed_indices and only["index"] in context.already_executed_indices else "not executed"
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
                status = (
                    "already executed"
                    if context.already_executed_indices and replay_candidate["index"] in context.already_executed_indices
                    else "not executed"
                )
                lines.append(f"{n}. {replay_candidate['preview']} [{status}]")
            lines.append("execute with: /replay --index <n>")
            return [{"role": "result", "content": "\n".join(lines)}]

        if replay_selection < 1 or replay_selection > len(replay_candidates):
            raise ValueError(f"index out of range: {replay_selection}")
        chosen = replay_candidates[replay_selection - 1]
        if context.already_executed_indices and chosen["index"] in context.already_executed_indices and not force:
            raise ValueError("target already has tool_request records; rerun with --force")

        if dry_run:
            return [
                {
                    "role": "result",
                    "content": (
                        f"replay dry-run: would execute candidate {replay_selection}\n"
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

    return None
