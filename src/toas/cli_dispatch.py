from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .cli_dispatch_ops import parse_ancestry_options, parse_prompt_options, parse_watch_options


@dataclass(frozen=True)
class DispatchDeps:
    run_help: Callable[[], None]
    run_step: Callable[..., None]
    run_step_async: Callable[[], None]
    run_watch: Callable[..., None]
    run_cancel: Callable[..., None]
    run_backend: Callable[..., None]
    run_jump: Callable[..., None]
    run_head: Callable[..., None]
    run_heads: Callable[[], None]
    run_intents: Callable[[], None]
    run_transcript: Callable[..., None]
    run_llm_input: Callable[..., None]
    run_prompt: Callable[..., None]
    run_prompts: Callable[..., None]
    run_history: Callable[..., None]
    run_rebuild: Callable[..., None]
    run_session_path: Callable[[], None]
    run_surface: Callable[..., None]
    run_ancestry: Callable[..., None]
    run_diff: Callable[..., None]
    run_index_rebuild: Callable[[], None]
    run_daemon: Callable[..., None]
    run_host: Callable[..., None]
    run_replay_script: Callable[..., None]


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
            session_path: str | None = None
            surface_id: str | None = None
            i = 2
            while i < len(argv):
                arg = argv[i]
                if arg == "--session":
                    if i + 1 >= len(argv):
                        raise SystemExit("usage: toas step --async [--session <transcript_path>]")
                    session_path = argv[i + 1]
                    i += 2
                    continue
                if arg == "--surface":
                    if i + 1 >= len(argv):
                        raise SystemExit("usage: toas step --async [--session <transcript_path>] [--surface <surface_id>]")
                    surface_id = argv[i + 1]
                    i += 2
                    continue
                raise SystemExit(f"unknown option: {arg}")
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
            stdin_mode = False
            control: str | None = None
            session_path: str | None = None
            surface_id: str | None = None
            i = 1
            while i < len(argv):
                arg = argv[i]
                if arg == "--stdin":
                    stdin_mode = True
                    i += 1
                    continue
                if arg == "--control":
                    if i + 1 >= len(argv):
                        raise SystemExit("usage: toas step [--stdin] [--control <slash_command>] [--session <transcript_path>]")
                    control = argv[i + 1]
                    i += 2
                    continue
                if arg == "--session":
                    if i + 1 >= len(argv):
                        raise SystemExit("usage: toas step [--stdin] [--control <slash_command>] [--session <transcript_path>]")
                    session_path = argv[i + 1]
                    i += 2
                    continue
                if arg == "--surface":
                    if i + 1 >= len(argv):
                        raise SystemExit("usage: toas step [--stdin] [--control <slash_command>] [--session <transcript_path>] [--surface <surface_id>]")
                    surface_id = argv[i + 1]
                    i += 2
                    continue
                raise SystemExit(f"unknown option: {arg}")
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
    elif argv[0] == "jump":
        deps.run_jump(int(require_arg(argv, 1, "toas jump <index>")))
    elif argv[0] == "head":
        deps.run_head(require_arg(argv, 1, "toas head <node_id>"))
    elif argv[0] == "heads":
        deps.run_heads()
    elif argv[0] == "intents":
        deps.run_intents()
    elif argv[0] == "transcript":
        deps.run_transcript(argv[1] if len(argv) > 1 else None)
    elif argv[0] == "llm-input":
        deps.run_llm_input(argv[1] if len(argv) > 1 else None)
    elif argv[0] == "prompt":
        ref = require_arg(argv, 1, "toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]")
        mode, constraints = parse_prompt_options(argv)
        deps.run_prompt(ref, mode=mode, constraints=constraints)
    elif argv[0] == "prompts":
        deps.run_prompts(argv[1] if len(argv) > 1 else None)
    elif argv[0] == "history":
        limit = int(argv[1]) if len(argv) > 1 else 10
        deps.run_history(limit)
    elif argv[0] == "rebuild":
        deps.run_rebuild(argv[1] if len(argv) > 1 else None)
    elif argv[0] == "session-path":
        deps.run_session_path()
    elif argv[0] == "surface":
        if len(argv) < 2:
            raise SystemExit("usage: toas surface [list|bind|select] ...")
        sub = argv[1]
        if sub == "list":
            deps.run_surface("list")
        elif sub == "bind":
            surface_id = require_arg(argv, 2, "toas surface bind <surface_id> <transcript_path> [--reason <text>]")
            transcript_path = require_arg(argv, 3, "toas surface bind <surface_id> <transcript_path> [--reason <text>]")
            reason = None
            if len(argv) > 4:
                if len(argv) != 6 or argv[4] != "--reason":
                    raise SystemExit("usage: toas surface bind <surface_id> <transcript_path> [--reason <text>]")
                reason = argv[5]
            deps.run_surface("bind", surface_id, transcript_path, reason=reason)
        elif sub == "select":
            surface_id = require_arg(argv, 2, "toas surface select <surface_id>")
            deps.run_surface("select", surface_id)
        elif sub == "rebind":
            surface_id = require_arg(argv, 2, "toas surface rebind <surface_id> --from-head <head_id> --to-head <head_id> --reason <text>")
            from_head_id = None
            to_head_id = None
            reason = None
            i = 3
            while i < len(argv):
                arg = argv[i]
                if arg == "--from-head" and i + 1 < len(argv):
                    from_head_id = argv[i + 1]
                    i += 2
                    continue
                if arg == "--to-head" and i + 1 < len(argv):
                    to_head_id = argv[i + 1]
                    i += 2
                    continue
                if arg == "--reason" and i + 1 < len(argv):
                    reason = argv[i + 1]
                    i += 2
                    continue
                raise SystemExit("usage: toas surface rebind <surface_id> --from-head <head_id> --to-head <head_id> --reason <text>")
            if not from_head_id or not to_head_id or not reason:
                raise SystemExit("usage: toas surface rebind <surface_id> --from-head <head_id> --to-head <head_id> --reason <text>")
            deps.run_surface("rebind", surface_id, from_head_id, to_head_id, reason=reason)
        else:
            raise SystemExit(f"unknown surface command: {sub}")
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
    elif argv[0] == "daemon":
        deps.run_daemon(argv[1] if len(argv) > 1 else "status")
    elif argv[0] == "host":
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
    else:
        raise SystemExit(f"unknown command: {argv[0]}")
