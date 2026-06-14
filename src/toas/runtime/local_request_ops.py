import io
import logging
import os
import re
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Any

from ..config import apply_overrides, config_from_discovered_paths
from ..graph import active_config_overrides, active_surface_id, surface_bindings


def capture_stdout(fn, *args, **kwargs) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        fn(*args, **kwargs)
    return buffer.getvalue()


def _ensure_file(path: Path) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


def resolve_events_path() -> Path:
    preferred = Path(".toas/events.jsonl")
    legacy = Path("events.jsonl")
    if preferred.exists():
        return preferred
    if legacy.exists():
        return legacy
    return preferred


def resolve_session_path(events: list[dict] | None = None) -> Path:
    file_config = config_from_discovered_paths(workdir=Path.cwd())
    operator_config = file_config
    if events is not None:
        session_overrides = active_config_overrides(events)
        operator_config = apply_overrides(file_config, session_overrides)
        selected_surface_id = active_surface_id(events)
        if isinstance(selected_surface_id, str) and selected_surface_id:
            bound_path = surface_bindings(events).get(selected_surface_id)
            if isinstance(bound_path, str) and bound_path.strip():
                return Path(bound_path.strip())
    transcript_path = operator_config.session.transcript_path.strip() or ".toas/session.md"
    return Path(transcript_path)


logger = logging.getLogger(__name__)


def run_op_capture_stdout(op: str, payload: dict, *, cli_module: Any, capture_stdout: Any) -> str:
    if op == "step":
        return capture_stdout(cli_module.run_step_local)
    if op == "heads":
        return capture_stdout(cli_module.run_heads_local)
    if op == "intents":
        return capture_stdout(cli_module.run_intents_local)
    if op == "prompt":
        return capture_stdout(
            cli_module.run_prompt_local,
            str(payload["ref"]),
            str(payload.get("mode", "direct")),
            payload.get("constraints"),
        )
    if op == "prompts":
        return capture_stdout(cli_module.run_prompts_local, payload.get("prefix"))
    if op == "history":
        limit = int(payload.get("limit", 10))
        return capture_stdout(cli_module.run_history_local, limit)
    if op == "transcript":
        return capture_stdout(cli_module.run_transcript_local, payload.get("head_id"))
    if op == "llm_input":
        return capture_stdout(cli_module.run_llm_input_local, payload.get("head_id"))
    if op == "rebuild":
        return capture_stdout(cli_module.run_rebuild_local, payload.get("head_id"))
    raise KeyError(op)


@contextmanager
def request_workdir(payload: dict, *, process_state_lock: Any):
    workdir = payload.get("workdir")
    if not isinstance(workdir, str) or not workdir:
        yield
        return
    original = Path.cwd().resolve()
    normalized_workdir = workdir
    if os.name == "nt":
        # Accept MSYS/Git-Bash style paths from Vim like /c/Users/...
        msys_match = re.match(r"^/([a-zA-Z])/(.*)$", workdir)
        if msys_match:
            drive = msys_match.group(1).upper()
            rest = msys_match.group(2).replace("/", "\\")
            normalized_workdir = f"{drive}:\\{rest}"
    target = Path(normalized_workdir).expanduser().resolve()
    if not target.is_dir():
        raise RuntimeError(f"invalid workdir: {workdir}")
    with process_state_lock:
        os.chdir(target)
        try:
            yield
        finally:
            os.chdir(original)


def handle_default_op(
    payload: dict,
    *,
    op: str,
    process_state_lock: Any,
    run_op_capture_stdout_fn: Any,
) -> dict:
    with request_workdir(payload, process_state_lock=process_state_lock):
        stdout = run_op_capture_stdout_fn(op, payload)
    logger.debug("out op=%s stdout_len=%d", op, len(stdout))
    return {"stdout": stdout}
