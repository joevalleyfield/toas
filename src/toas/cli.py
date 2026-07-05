import json
import sys
from pathlib import Path

from . import cli_commands
from .cli_async_commands import (
    build_deps as _build_async_deps,
)
from .cli_async_commands import (
    run_backend as _run_backend_async_command,
)
from .cli_async_commands import (
    run_cancel as _run_cancel_async_command,
)
from .cli_async_commands import (
    run_step_async as _run_step_async_command,
)
from .cli_async_commands import (
    run_watch as _run_watch_async_command,
)
from .cli_dispatch import DispatchDeps
from .cli_dispatch import dispatch_main as dispatch_cli_main
from .cli_dispatch_ops import SURFACE_BIND_USAGE, SURFACE_REBIND_USAGE, SURFACE_SELECT_USAGE
from .cli_host_commands import run_host as run_host_command
from .cli_replay_script import ReplayScriptDeps
from .cli_replay_script import run_replay_script as run_cli_replay_script
from .cli_runtime_commands import run_daemon as run_runtime_daemon
from .cli_session_views import run_graph as _run_graph_impl
from .cli_streaming import ClosedSetMarkerStreamEscaper, StreamPresenter
from .config import config_from_discovered_paths, config_from_file  # noqa: F401
from .daemon import server_lifecycle as daemon_server_lifecycle
from .graph import (
    read_log,
    surface_bindings,
)
from .operator_api import bind_surface as operator_bind_surface
from .operator_api import graph_text as operator_graph_text
from .operator_api import select_surface as operator_select_surface
from .operator_api import step_once as run_operator_step_once
from .operator_api import surface_lines as operator_surface_lines
from .prompts import load_prompt_ref
from .replay_runner import (
    append_text_block,
    load_replay_steps,
    render_procedure_append,
    render_prompt_append,
    write_replay_artifact,
)
from .rpc_client import RpcClientError, rpc_request
from .rpc_transport import default_endpoint, endpoint_exists
from .runtime.cancel_latency_summary import summarize_cancel_latency_file
from .runtime.presentation_edges import (
    extract_response_stdout as extract_runtime_response_stdout,
)
from .runtime.request_ops import _ensure_file, resolve_events_path, resolve_session_path
from .runtime.rpc_payload_edges import (
    drop_none_fields as drop_runtime_none_fields,
)
from .runtime.rpc_payload_edges import (
    with_workdir as with_runtime_workdir,
)
from .runtime.session_file_edges import (
    read_text_preserve_newlines as read_runtime_text_preserve_newlines,
)
from .step import render_session_help_full

SESSION_PATH = Path("session.md")
EVENTS_PATH = Path(".toas/events.jsonl")

_StreamPresenter = StreamPresenter
_ClosedSetMarkerStreamEscaper = ClosedSetMarkerStreamEscaper


USAGE = """Usage:
  toas [step]
  toas step --async [--session <transcript_path>]
  toas watch <run_id> [--offset <n>] [--follow]
  toas cancel <run_id>
  toas backend [start|stop|restart|status]
  toas heads [--sources ...]
  toas intents
  toas graph [anchor] [-N] [+N] [--projection temporal|consequence] [--sources ...] [--stitch-diagnostics]
  toas transcript [anchor] [--sources ...]
  toas llm-input [anchor] [--sources ...] [--envelope]
  toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]
  toas prompts [prefix]
  toas history [limit] [anchor] [--sources ...]
  toas ancestry <message_id> [--depth <n>] [--full]
  toas diff <head_a> <head_b> [--full]
  toas index [rebuild]
  toas daemon [start|stop|status]
  toas service [start|stop|status]   (alias: daemon)
  toas host serve [--owner-pid <pid>]
  toas transport [serve|stop]        (alias: host)
  toas surface [list|bind|select|rebind] ...
  toas replay-script <script_path> [--output <path>] [--dry-run]
  toas debug cancel-latency <jsonl_path>
  toas help

Environment:
  TOAS_RPC_MODE=auto|on|off

History surfaces:
  heads                    show the selected history graph leaf set as compact branch tips
  history [limit]          show the current root-to-head lineage as a bounded window
  graph [--projection ...] show the selected history graph as a topology view
  transcript [head_id]     show transcript projection for a selected lineage
  llm-input [head_id]      show the core message-body projection for a selected lineage
  llm-input --envelope     also show the packet/system shaping live generation adds
                           above that core projection (transport re-rendering such as
                           single_user_blob is not reflected)
"""


def _should_prefer_rpc() -> bool:
    return endpoint_exists(default_endpoint())


def _rpc_mode() -> str:
    import os
    mode = os.environ.get("TOAS_RPC_MODE", "auto").strip().lower()
    if mode not in {"auto", "on", "off"}:
        return "auto"
    return mode


def _rpc_enabled_for_call() -> bool:
    mode = _rpc_mode()
    if mode == "off":
        return False
    if mode == "on":
        return True
    return _should_prefer_rpc()


def _rpc_stdout(op: str, payload: dict | None = None) -> bool:
    if not _rpc_enabled_for_call():
        return False
    payload = with_runtime_workdir(payload, workdir=Path.cwd())
    try:
        response = rpc_request(op, payload)
    except RpcClientError:
        return False
    stdout = extract_runtime_response_stdout(response)
    if stdout:
        print(stdout, end="")
    return True


def _session_path_for_surface_id(surface_id: str) -> str:
    events = read_log(str(resolve_events_path()))
    bound_path = surface_bindings(events).get(surface_id)
    if not isinstance(bound_path, str) or not bound_path.strip():
        raise SystemExit(f"unknown surface_id: {surface_id}")
    return bound_path.strip()


def _load_operator_config_for_cwd():
    from .runtime.policy_edges import load_operator_config_for_workdir
    return load_operator_config_for_workdir(Path.cwd())


def _make_async_deps():
    return _build_async_deps(
        load_operator_config_for_cwd=_load_operator_config_for_cwd,
        rpc_enabled_for_call=_rpc_enabled_for_call,
        rpc_request=rpc_request,
        print_fn=print,
    )


# --- step ---

def _run_step(
    *,
    stdin_mode: bool = False,
    control: str | None = None,
    session_path: str | None = None,
    surface_id: str | None = None,
    on_llm_answer_delta=None,
    on_llm_reasoning_delta=None,
    on_llm_prompt_progress=None,
    on_projection_delta=None,
):
    if session_path is not None and surface_id is not None:
        raise SystemExit("step accepts only one of session_path or surface_id")
    if surface_id is not None:
        session_path = _session_path_for_surface_id(surface_id)
    run_operator_step_once(
        stdin_mode=stdin_mode,
        control=control,
        session_path=session_path,
        on_llm_answer_delta=on_llm_answer_delta,
        on_llm_reasoning_delta=on_llm_reasoning_delta,
        on_llm_prompt_progress=on_llm_prompt_progress,
        on_projection_delta=on_projection_delta,
    )


def run_step(
    *,
    stdin_mode: bool = False,
    control: str | None = None,
    session_path: str | None = None,
    surface_id: str | None = None,
):
    if stdin_mode or control is not None or session_path is not None or surface_id is not None:
        kwargs = {"stdin_mode": stdin_mode, "control": control, "session_path": session_path}
        if surface_id is not None:
            kwargs["surface_id"] = surface_id
        _run_step(**kwargs)
        return
    if _rpc_stdout("step"):
        return
    _run_step()


def run_step_async(*, session_path: str | None = None, surface_id: str | None = None):
    if session_path is not None and surface_id is not None:
        raise SystemExit("step --async accepts only one of session_path or surface_id")
    if surface_id is not None:
        session_path = _session_path_for_surface_id(surface_id)
    _run_step_async_command(_make_async_deps(), session_path=session_path)


def run_watch(run_id: str, *, offset: int = 0, follow: bool = False):
    _run_watch_async_command(run_id, offset=offset, follow=follow, deps=_make_async_deps())


def run_cancel(run_id: str):
    _run_cancel_async_command(run_id, _make_async_deps())


def run_backend(action: str):
    _run_backend_async_command(action, _make_async_deps())


# --- read-only command wrappers (RPC-or-local) ---

def _run_graph(
    projection: str = "temporal",
    source_tokens: list[str] | None = None,
    stitch_diagnostics: bool = False,
    anchor_id: str | None = None,
    before: int | None = None,
    after: int | None = None,
):
    _run_graph_impl(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_graph_text=operator_graph_text,
        projection=projection,
        source_tokens=source_tokens,
        stitch_diagnostics=stitch_diagnostics,
        anchor_id=anchor_id,
        before=before,
        after=after,
    )


def run_intents():
    if _rpc_stdout("intents"):
        return
    cli_commands.run_intents()


def run_heads(source_tokens: list[str] | None = None):
    payload = {}
    if source_tokens is not None:
        payload["source_tokens"] = source_tokens
    if _rpc_stdout("heads", payload or None):
        return
    cli_commands.run_heads(source_tokens=source_tokens)


def run_graph(
    projection: str = "temporal",
    source_tokens: list[str] | None = None,
    stitch_diagnostics: bool = False,
    anchor_id: str | None = None,
    before: int | None = None,
    after: int | None = None,
):
    payload: dict[str, object] = {"projection": projection}
    if source_tokens is not None:
        payload["source_tokens"] = source_tokens
    if stitch_diagnostics:
        payload["stitch_diagnostics"] = stitch_diagnostics
    if anchor_id is not None:
        payload["anchor_id"] = anchor_id
    if before is not None:
        payload["before"] = before
    if after is not None:
        payload["after"] = after
    if _rpc_stdout("graph", payload):
        return
    _run_graph(
        projection,
        source_tokens=source_tokens,
        stitch_diagnostics=stitch_diagnostics,
        anchor_id=anchor_id,
        before=before,
        after=after,
    )


def run_history(
    limit: int = 10,
    source_tokens: list[str] | None = None,
    anchor_id: str | None = None,
):
    payload: dict[str, object] = {"limit": limit}
    if source_tokens is not None:
        payload["source_tokens"] = source_tokens
    if anchor_id is not None:
        payload["anchor_id"] = anchor_id
    if _rpc_stdout("history", payload):
        return
    cli_commands.run_history(limit, source_tokens=source_tokens, anchor_id=anchor_id)


def run_transcript(head_id: str | None = None, source_tokens: list[str] | None = None):
    if _rpc_stdout("transcript", drop_runtime_none_fields({"head_id": head_id, "source_tokens": source_tokens})):
        return
    cli_commands.run_transcript(head_id, source_tokens=source_tokens)


def run_session_path():
    cli_commands.run_session_path()


def run_llm_input(
    head_id: str | None = None,
    source_tokens: list[str] | None = None,
    envelope: bool = False,
):
    payload = drop_runtime_none_fields({"head_id": head_id, "source_tokens": source_tokens, "envelope": envelope})
    if _rpc_stdout("llm_input", payload):
        return
    cli_commands.run_llm_input(head_id, source_tokens=source_tokens, envelope=envelope)


def run_prompt(ref: str, mode: str = "direct", constraints: list[str] | None = None):
    payload = {"ref": ref, "mode": mode}
    if constraints:
        payload["constraints"] = constraints
    if _rpc_stdout("prompt", payload):
        return
    cli_commands.run_prompt(ref, mode=mode, constraints=constraints)


def run_prompts(prefix: str | None = None):
    if _rpc_stdout("prompts", drop_runtime_none_fields({"prefix": prefix})):
        return
    cli_commands.run_prompts(prefix)


def run_diff(head_a: str, head_b: str, *, full: bool = False):
    if _rpc_stdout("diff", {"head_a": head_a, "head_b": head_b, "full": full}):
        return
    cli_commands.run_diff(head_a, head_b, full=full)


def run_ancestry(message_id: str, *, depth: int | None = None, full: bool = False):
    if _rpc_stdout("ancestry", drop_runtime_none_fields({"message_id": message_id, "depth": depth, "full": full})):
        return
    cli_commands.run_ancestry(message_id, depth=depth, full=full)


def run_index_rebuild():
    if _rpc_stdout("index_rebuild"):
        return
    cli_commands.run_index_rebuild()


def run_daemon(action: str):
    run_runtime_daemon(action, daemon_module=daemon_server_lifecycle)


def run_host(argv: list[str]):
    run_host_command(argv)


# --- surface ---

def run_surface(action: str, *args, reason: str | None = None):
    events_path = resolve_events_path()
    _ensure_file(events_path)
    if action == "list":
        for line in operator_surface_lines(events_path=events_path).lines:
            print(line)
        return
    if action == "bind":
        if len(args) != 2:
            raise SystemExit(SURFACE_BIND_USAGE)
        out = operator_bind_surface(
            events_path=events_path,
            surface_id=str(args[0]),
            transcript_path=str(args[1]),
            reason=reason,
        )
        print(out.message)
        return
    if action == "select":
        if len(args) != 1:
            raise SystemExit(SURFACE_SELECT_USAGE)
        out = operator_select_surface(events_path=events_path, surface_id=str(args[0]))
        print(out.message)
        return
    if action == "rebind":
        if len(args) != 3 or not isinstance(reason, str) or not reason:
            raise SystemExit(SURFACE_REBIND_USAGE)
        from .operator_api import rebind_surface as operator_rebind_surface
        out = operator_rebind_surface(
            events_path=events_path,
            surface_id=str(args[0]),
            from_head_id=str(args[1]),
            to_head_id=str(args[2]),
            reason=reason,
        )
        print(out.message)
        return
    raise SystemExit(f"unknown surface command: {action}")


# --- other commands ---

def run_help() -> None:
    print(USAGE, end="")
    print(render_session_help_full())


def run_replay_script(script_path: str, *, output_path: str | None = None, dry_run: bool = False):
    session_path = resolve_session_path()
    run_cli_replay_script(
        script_path,
        output_path=output_path,
        dry_run=dry_run,
        deps=ReplayScriptDeps(
            ensure_file=_ensure_file,
            session_path=session_path,
            events_path=resolve_events_path(),
            load_replay_steps=load_replay_steps,
            render_prompt_append=render_prompt_append,
            render_procedure_append=render_procedure_append,
            append_text_block=append_text_block,
            read_log=read_log,
            run_step=_run_step,
            read_text_preserve_newlines=read_runtime_text_preserve_newlines,
            load_prompt_ref=load_prompt_ref,
            write_replay_artifact=write_replay_artifact,
            print_fn=print,
        ),
    )


def run_debug_cancel_latency(path: str) -> None:
    out = summarize_cancel_latency_file(Path(path))
    print(json.dumps(out, indent=2, sort_keys=True))


# --- entry point ---

def _build_dispatch_deps() -> DispatchDeps:
    return DispatchDeps(
        run_help=run_help,
        run_step=run_step,
        run_step_async=run_step_async,
        run_watch=run_watch,
        run_cancel=run_cancel,
        run_backend=run_backend,
        run_heads=run_heads,
        run_intents=run_intents,
        run_graph=run_graph,
        run_transcript=run_transcript,
        run_llm_input=run_llm_input,
        run_prompt=run_prompt,
        run_prompts=run_prompts,
        run_history=run_history,
        run_session_path=run_session_path,
        run_surface=run_surface,
        run_ancestry=run_ancestry,
        run_diff=run_diff,
        run_index_rebuild=run_index_rebuild,
        run_daemon=run_daemon,
        run_host=run_host,
        run_replay_script=run_replay_script,
        run_debug_cancel_latency=run_debug_cancel_latency,
    )


def main():
    from .runtime.logging_bootstrap import configure_logging
    configure_logging(config_from_discovered_paths(workdir=Path.cwd()).diagnostics)
    dispatch_cli_main(sys.argv[1:], deps=_build_dispatch_deps())


if __name__ == "__main__":
    raise SystemExit(
        "Do not invoke 'python -m toas.cli'. "
        "Use 'python -m toas' (or 'toas') instead."
    )
