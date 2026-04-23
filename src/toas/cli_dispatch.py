from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .cli_dispatch_ops import parse_ancestry_options, parse_prompt_options, parse_watch_options


@dataclass(frozen=True)
class DispatchDeps:
    run_help: Callable[[], None]
    run_step: Callable[[], None]
    run_step_async: Callable[[], None]
    run_watch: Callable[..., None]
    run_cancel: Callable[..., None]
    run_backend: Callable[..., None]
    run_jump: Callable[..., None]
    run_head: Callable[..., None]
    run_heads: Callable[[], None]
    run_transcript: Callable[..., None]
    run_llm_input: Callable[..., None]
    run_prompt: Callable[..., None]
    run_prompts: Callable[..., None]
    run_history: Callable[..., None]
    run_rebuild: Callable[..., None]
    run_ancestry: Callable[..., None]
    run_diff: Callable[..., None]
    run_index_rebuild: Callable[[], None]
    run_daemon: Callable[..., None]


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
            deps.run_step_async()
        elif len(argv) > 1:
            raise SystemExit(f"unknown option: {argv[1]}")
        else:
            deps.run_step()
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
    else:
        raise SystemExit(f"unknown command: {argv[0]}")
