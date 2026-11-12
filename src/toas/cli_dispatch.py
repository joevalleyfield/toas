from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .cli_dispatch_ops import (
    parse_ancestry_options,
    parse_edit_options,
    parse_graph_options,
    parse_heads_options,
    parse_history_options,
    parse_llm_input_options,
    parse_new_options,
    parse_prompt_options,
    parse_session_continue_options,
    parse_step_async_options,
    parse_step_options,
    parse_surface_options,
    parse_transcript_options,
    parse_watch_options,
)
from .cli_usage import get_subcommand_help


@dataclass(frozen=True)
class DispatchDeps:
    run_help: Callable[[], None]
    run_step: Callable[..., None]
    run_step_async: Callable[..., None]
    run_watch: Callable[..., None]
    run_cancel: Callable[..., None]
    run_backend: Callable[..., None]
    run_heads: Callable[..., None]
    run_intents: Callable[[], None]
    run_graph: Callable[..., None]
    run_transcript: Callable[..., None]
    run_llm_input: Callable[..., None]
    run_prompt: Callable[..., None]
    run_prompts: Callable[..., None]
    run_history: Callable[..., None]
    run_session_path: Callable[[], None]
    run_surface: Callable[..., None]
    run_ancestry: Callable[..., None]
    run_diff: Callable[..., None]
    run_index_rebuild: Callable[[], None]
    run_daemon: Callable[..., None]
    run_host: Callable[..., None]
    run_replay_script: Callable[..., None]
    run_debug_cancel_latency: Callable[..., None]
    run_session_continue: Callable[..., None] | None = None
    run_policy: Callable[..., None] | None = None
    run_skill: Callable[..., None] | None = None
    run_skill_specialize: Callable[..., None] | None = None
    run_skills: Callable[..., None] | None = None
    run_new: Callable[..., None] | None = None
    run_edit: Callable[..., None] | None = None


def require_arg(cmd: list[str], index: int, usage_line: str) -> str:
    if len(cmd) <= index:
        raise SystemExit(f"usage: {usage_line}")
    return cmd[index]


def _handle_step(argv: list[str], deps: DispatchDeps) -> None:
    if "--async" in argv[1:]:
        session_path, surface_id, max_turns = parse_step_async_options(argv)
        if session_path is not None and surface_id is not None:
            raise SystemExit("step --async accepts only one of --session or --surface")
        step_async_kwargs: dict[str, object] = {}
        if session_path is not None:
            step_async_kwargs["session_path"] = session_path
        if surface_id is not None:
            step_async_kwargs["surface_id"] = surface_id
        if max_turns is not None:
            step_async_kwargs["max_turns"] = max_turns
        deps.run_step_async(**step_async_kwargs)
    else:
        stdin_mode, preview_request, preview_request_pretty, preview_response, control, session_path, surface_id, infer_from, max_turns = parse_step_options(argv)
        if session_path is not None and surface_id is not None:
            raise SystemExit("step accepts only one of --session or --surface")
        if not stdin_mode and not preview_request and not preview_response and control is None and session_path is None and infer_from is None and max_turns is None:
            if surface_id is None:
                deps.run_step()
            else:
                deps.run_step(surface_id=surface_id)
        else:
            step_kwargs: dict[str, object] = {
                "stdin_mode": stdin_mode,
                "control": control,
                "session_path": session_path,
                "surface_id": surface_id,
            }
            if max_turns is not None:
                step_kwargs["max_turns"] = max_turns
            if infer_from is not None:
                step_kwargs["infer_from"] = infer_from
            if preview_request:
                step_kwargs["preview_request"] = True
            if preview_request_pretty:
                step_kwargs["preview_request_pretty"] = True
            if preview_response:
                step_kwargs["preview_response"] = True
            deps.run_step(**step_kwargs)


def _handle_watch(argv: list[str], deps: DispatchDeps) -> None:
    run_id = require_arg(argv, 1, "toas watch <run_id> [--offset <n>] [--follow]")
    offset, follow = parse_watch_options(argv)
    deps.run_watch(run_id, offset=offset, follow=follow)


def _handle_cancel(argv: list[str], deps: DispatchDeps) -> None:
    deps.run_cancel(require_arg(argv, 1, "toas cancel <run_id>"))


def _handle_backend(argv: list[str], deps: DispatchDeps) -> None:
    action = argv[1] if len(argv) > 1 else "status"
    deps.run_backend(action)


def _handle_heads(argv: list[str], deps: DispatchDeps) -> None:
    source_tokens = parse_heads_options(argv)
    if source_tokens is None:
        deps.run_heads()
    else:
        deps.run_heads(source_tokens=source_tokens)


def _handle_intents(argv: list[str], deps: DispatchDeps) -> None:
    deps.run_intents()


def _handle_graph(argv: list[str], deps: DispatchDeps) -> None:
    projection, source_tokens, stitch_diagnostics, anchor_id, before, after = parse_graph_options(argv)
    graph_kwargs: dict[str, object] = {}
    if source_tokens is not None:
        graph_kwargs["source_tokens"] = source_tokens
    if stitch_diagnostics:
        graph_kwargs["stitch_diagnostics"] = stitch_diagnostics
    if anchor_id is not None:
        graph_kwargs["anchor_id"] = anchor_id
    if before is not None:
        graph_kwargs["before"] = before
    if after is not None:
        graph_kwargs["after"] = after
    deps.run_graph(projection, **graph_kwargs)


def _handle_transcript(argv: list[str], deps: DispatchDeps) -> None:
    anchor_id, source_tokens, snapshots, diffs, projection_alias, record = parse_transcript_options(argv)
    transcript_kwargs: dict[str, object] = {}
    if source_tokens is not None:
        transcript_kwargs["source_tokens"] = source_tokens
    if snapshots is not None:
        transcript_kwargs["snapshots"] = snapshots
    if diffs is not None:
        transcript_kwargs["diffs"] = diffs
    if projection_alias is not None:
        transcript_kwargs["projection"] = projection_alias
    if record:
        transcript_kwargs["record"] = True
    deps.run_transcript(anchor_id, **transcript_kwargs)


def _handle_llm_input(argv: list[str], deps: DispatchDeps) -> None:
    anchor_id, source_tokens, envelope = parse_llm_input_options(argv)
    llm_input_kwargs: dict[str, object] = {"envelope": envelope}
    if source_tokens is not None:
        llm_input_kwargs["source_tokens"] = source_tokens
    deps.run_llm_input(anchor_id, **llm_input_kwargs)


def _handle_prompt(argv: list[str], deps: DispatchDeps) -> None:
    ref = require_arg(argv, 1, "toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]")
    mode, constraints = parse_prompt_options(argv)
    deps.run_prompt(ref, mode=mode, constraints=constraints)


def _handle_prompts(argv: list[str], deps: DispatchDeps) -> None:
    deps.run_prompts(argv[1] if len(argv) > 1 else None)


def _handle_skill(argv: list[str], deps: DispatchDeps) -> None:
    if len(argv) > 1 and argv[1] == "specialize":
        target = require_arg(argv, 2, "toas skill specialize <name>")
        if deps.run_skill_specialize is not None:
            deps.run_skill_specialize(target)
    else:
        name = require_arg(argv, 1, "toas skill <name>")
        if deps.run_skill is not None:
            deps.run_skill(name)


def _handle_skills(argv: list[str], deps: DispatchDeps) -> None:
    if deps.run_skills is not None:
        deps.run_skills(argv[1] if len(argv) > 1 else None)


def _handle_history(argv: list[str], deps: DispatchDeps) -> None:
    limit, source_tokens, anchor_id = parse_history_options(argv)
    history_kwargs: dict[str, object] = {}
    if source_tokens is None:
        if anchor_id is not None:
            history_kwargs["anchor_id"] = anchor_id
    else:
        history_kwargs["source_tokens"] = source_tokens
        if anchor_id is not None:
            history_kwargs["anchor_id"] = anchor_id
    deps.run_history(limit, **history_kwargs)


def _handle_session_path(argv: list[str], deps: DispatchDeps) -> None:
    deps.run_session_path()


def _handle_session(argv: list[str], deps: DispatchDeps) -> None:
    if deps.run_session_continue is None:
        raise SystemExit("session continuation is unavailable")
    predecessor_path, accepted_name, ignore_preceding_graph, exclude_tail = parse_session_continue_options(argv)
    continue_kwargs: dict[str, object] = {"predecessor_path": predecessor_path, "accepted_name": accepted_name}
    if ignore_preceding_graph:
        continue_kwargs["ignore_preceding_graph"] = True
    if exclude_tail:
        continue_kwargs["exclude_tail"] = True
    deps.run_session_continue(**continue_kwargs)


def _handle_new(argv: list[str], deps: DispatchDeps) -> None:
    slug, edit = parse_new_options(argv)
    if deps.run_new is None:
        raise SystemExit("new command is not configured")
    deps.run_new(slug, edit=edit)


def _handle_edit(argv: list[str], deps: DispatchDeps) -> None:
    if deps.run_edit is None:
        raise SystemExit("edit command is not configured")
    deps.run_edit(parse_edit_options(argv))


def _handle_surface(argv: list[str], deps: DispatchDeps) -> None:
    sub, args, reason = parse_surface_options(argv)
    if sub in {"bind", "rebind"}:
        deps.run_surface(sub, *args, reason=reason)
    elif reason is None:
        deps.run_surface(sub, *args)
    else:
        deps.run_surface(sub, *args, reason=reason)


def _handle_ancestry(argv: list[str], deps: DispatchDeps) -> None:
    msg_id = require_arg(argv, 1, "toas ancestry <message_id> [--depth <n>] [--full]")
    depth, full = parse_ancestry_options(argv)
    deps.run_ancestry(msg_id, depth=depth, full=full)


def _handle_diff(argv: list[str], deps: DispatchDeps) -> None:
    head_a = require_arg(argv, 1, "toas diff <head_a> <head_b> [--full]")
    head_b = require_arg(argv, 2, "toas diff <head_a> <head_b> [--full]")
    full = "--full" in argv[3:]
    deps.run_diff(head_a, head_b, full=full)


def _handle_index(argv: list[str], deps: DispatchDeps) -> None:
    sub = argv[1] if len(argv) > 1 else "rebuild"
    if sub == "rebuild":
        deps.run_index_rebuild()
    else:
        raise SystemExit(f"unknown index command: {sub}")


def _handle_daemon(argv: list[str], deps: DispatchDeps) -> None:
    deps.run_daemon(argv[1] if len(argv) > 1 else "status")


def _handle_host(argv: list[str], deps: DispatchDeps) -> None:
    deps.run_host(argv[1:])


def _handle_replay_script(argv: list[str], deps: DispatchDeps) -> None:
    script_path = require_arg(argv, 1, "toas replay-script <script_path> [--output <path>] [--dry-run]")
    output_path = None
    dry_run = False
    i = 2
    while i < len(argv):
        arg = argv[i]
        if arg == "--dry-run":
            dry_run = True
            i += 1
            continue
        if arg == "--output":
            if i + 1 >= len(argv):
                raise SystemExit("usage: toas replay-script <script_path> [--output <path>] [--dry-run]")
            output_path = argv[i + 1]
            i += 2
            continue
        raise SystemExit(f"unknown option: {arg}")
    deps.run_replay_script(script_path, output_path=output_path, dry_run=dry_run)


def _handle_debug(argv: list[str], deps: DispatchDeps) -> None:
    sub = require_arg(argv, 1, "toas debug cancel-latency <jsonl_path>")
    if sub != "cancel-latency":
        raise SystemExit(f"unknown debug command: {sub}")
    path = require_arg(argv, 2, "toas debug cancel-latency <jsonl_path>")
    deps.run_debug_cancel_latency(path)


def _handle_policy(argv: list[str], deps: DispatchDeps) -> None:
    if deps.run_policy is None:
        raise SystemExit("policy command is not configured")
    deps.run_policy(argv[1:])


_COMMANDS: dict[str, Callable[[list[str], DispatchDeps], None]] = {
    "step": _handle_step,
    "watch": _handle_watch,
    "cancel": _handle_cancel,
    "backend": _handle_backend,
    "heads": _handle_heads,
    "intents": _handle_intents,
    "graph": _handle_graph,
    "transcript": _handle_transcript,
    "llm-input": _handle_llm_input,
    "prompt": _handle_prompt,
    "prompts": _handle_prompts,
    "skill": _handle_skill,
    "skills": _handle_skills,
    "history": _handle_history,
    "session-path": _handle_session_path,
    "session": _handle_session,
    "new": _handle_new,
    "edit": _handle_edit,
    "surface": _handle_surface,
    "ancestry": _handle_ancestry,
    "diff": _handle_diff,
    "index": _handle_index,
    "daemon": _handle_daemon,
    "service": _handle_daemon,
    "host": _handle_host,
    "transport": _handle_host,
    "replay-script": _handle_replay_script,
    "debug": _handle_debug,
    "policy": _handle_policy,
}


def dispatch_main(
    cmd: list[str],
    *,
    deps: DispatchDeps,
) -> None:
    argv = cmd or ["step"]

    if argv[0] in {"help", "--help", "-h"}:
        if len(argv) > 1:
            subcommand_help = get_subcommand_help(argv[1])
            if subcommand_help is not None:
                raise SystemExit(subcommand_help)
        deps.run_help()
        return

    if len(argv) > 1 and argv[1] in {"--help", "-h"}:
        subcommand_help = get_subcommand_help(argv[0])
        if subcommand_help is not None:
            raise SystemExit(subcommand_help)

    handler = _COMMANDS.get(argv[0])
    if handler is None:
        raise SystemExit(f"unknown command: {argv[0]}")
    handler(argv, deps)
