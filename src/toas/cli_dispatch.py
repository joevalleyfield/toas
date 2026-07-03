from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .cli_dispatch_ops import (
    parse_ancestry_options,
    parse_graph_options,
    parse_prompt_options,
    parse_step_async_options,
    parse_step_options,
    parse_surface_options,
    parse_watch_options,
)

HEADS_USAGE = (
    "usage: toas heads\n"
    "show the selected history graph leaf set as a compact branch-tip view\n"
    "zero-arg scope follows the shared implicit anchor: current logical history"
)

HISTORY_USAGE = (
    "usage: toas history [limit]\n"
    "show the current root-to-head lineage as a bounded readable window\n"
    "zero-arg scope follows the shared implicit anchor: the current default lineage"
)

GRAPH_USAGE = (
    "usage: toas graph [--projection temporal|consequence] [--sources <hot|segments|path> ...]\n"
    "show the selected history graph as a topology view across hot history by default\n"
    "use `--sources` to select explicit event-log sources"
)


@dataclass(frozen=True)
class DispatchDeps:
    run_help: Callable[[], None]
    run_step: Callable[..., None]
    run_step_async: Callable[[], None]
    run_watch: Callable[..., None]
    run_cancel: Callable[..., None]
    run_backend: Callable[..., None]
    run_heads: Callable[[], None]
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


def require_arg(cmd: list[str], index: int, usage_line: str) -> str:
    if len(cmd) <= index:
        raise SystemExit(f"usage: {usage_line}")
    return cmd[index]


def dispatch_main(
    cmd: list[str],
    *,
    deps: DispatchDeps,
) -> None:
    argv = cmd or ["step"]

    if argv[0] in {"help", "--help", "-h"}:
        deps.run_help()
    elif argv[0] == "step":
        if len(argv) > 1 and argv[1] == "--async":
            session_path, surface_id = parse_step_async_options(argv)
            if session_path is not None and surface_id is not None:
                raise SystemExit("step --async accepts only one of --session or --surface")
            if session_path is None:
                if surface_id is None:
                    deps.run_step_async()
                else:
                    deps.run_step_async(surface_id=surface_id)
            else:
                deps.run_step_async(session_path=session_path)
        else:
            stdin_mode, control, session_path, surface_id = parse_step_options(argv)
            if session_path is not None and surface_id is not None:
                raise SystemExit("step accepts only one of --session or --surface")
            if not stdin_mode and control is None and session_path is None:
                if surface_id is None:
                    deps.run_step()
                else:
                    deps.run_step(surface_id=surface_id)
            else:
                deps.run_step(stdin_mode=stdin_mode, control=control, session_path=session_path, surface_id=surface_id)
    elif argv[0] == "watch":
        run_id = require_arg(argv, 1, "toas watch <run_id> [--offset <n>] [--follow]")
        offset, follow = parse_watch_options(argv)
        deps.run_watch(run_id, offset=offset, follow=follow)
    elif argv[0] == "cancel":
        deps.run_cancel(require_arg(argv, 1, "toas cancel <run_id>"))
    elif argv[0] == "backend":
        action = argv[1] if len(argv) > 1 else "status"
        deps.run_backend(action)
    elif argv[0] == "heads":
        if len(argv) > 1 and argv[1] in {"--help", "-h"}:
            raise SystemExit(HEADS_USAGE)
        deps.run_heads()
    elif argv[0] == "intents":
        deps.run_intents()
    elif argv[0] == "graph":
        if len(argv) > 1 and argv[1] in {"--help", "-h"}:
            raise SystemExit(GRAPH_USAGE)
        projection, source_tokens = parse_graph_options(argv)
        deps.run_graph(projection, source_tokens=source_tokens)
    elif argv[0] == "transcript":
        deps.run_transcript(argv[1] if len(argv) > 1 else None)
    elif argv[0] == "llm-input":
        rest = argv[1:]
        envelope = "--envelope" in rest
        positionals = [arg for arg in rest if arg != "--envelope"]
        deps.run_llm_input(positionals[0] if positionals else None, envelope=envelope)
    elif argv[0] == "prompt":
        ref = require_arg(argv, 1, "toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]")
        mode, constraints = parse_prompt_options(argv)
        deps.run_prompt(ref, mode=mode, constraints=constraints)
    elif argv[0] == "prompts":
        deps.run_prompts(argv[1] if len(argv) > 1 else None)
    elif argv[0] == "history":
        if len(argv) > 1 and argv[1] in {"--help", "-h"}:
            raise SystemExit(HISTORY_USAGE)
        try:
            limit = int(argv[1]) if len(argv) > 1 else 10
        except ValueError as exc:
            raise SystemExit(HISTORY_USAGE) from exc
        deps.run_history(limit)
    elif argv[0] == "session-path":
        deps.run_session_path()
    elif argv[0] == "surface":
        sub, args, reason = parse_surface_options(argv)
        if sub in {"bind", "rebind"}:
            deps.run_surface(sub, *args, reason=reason)
        elif reason is None:
            deps.run_surface(sub, *args)
        else:
            deps.run_surface(sub, *args, reason=reason)
    elif argv[0] == "ancestry":
        msg_id = require_arg(argv, 1, "toas ancestry <message_id> [--depth <n>] [--full]")
        depth, full = parse_ancestry_options(argv)
        deps.run_ancestry(msg_id, depth=depth, full=full)
    elif argv[0] == "diff":
        head_a = require_arg(argv, 1, "toas diff <head_a> <head_b> [--full]")
        head_b = require_arg(argv, 2, "toas diff <head_a> <head_b> [--full]")
        full = "--full" in argv[3:]
        deps.run_diff(head_a, head_b, full=full)
    elif argv[0] == "index":
        sub = argv[1] if len(argv) > 1 else "rebuild"
        if sub == "rebuild":
            deps.run_index_rebuild()
        else:
            raise SystemExit(f"unknown index command: {sub}")
    elif argv[0] in {"daemon", "service"}:
        deps.run_daemon(argv[1] if len(argv) > 1 else "status")
    elif argv[0] in {"host", "transport"}:
        deps.run_host(argv[1:])
    elif argv[0] == "replay-script":
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
    elif argv[0] == "debug":
        sub = require_arg(argv, 1, "toas debug cancel-latency <jsonl_path>")
        if sub != "cancel-latency":
            raise SystemExit(f"unknown debug command: {sub}")
        path = require_arg(argv, 2, "toas debug cancel-latency <jsonl_path>")
        deps.run_debug_cancel_latency(path)
    else:
        raise SystemExit(f"unknown command: {argv[0]}")
