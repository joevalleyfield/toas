import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ..perf import PerfRecorder, phase


def run_op_capture_stdout(op: str, payload: dict, *, cli_module: Any, capture_stdout: Any) -> str:
    if op == "step":
        return capture_stdout(cli_module.run_step_local)
    if op == "jump":
        return capture_stdout(cli_module.run_jump_local, int(payload["index"]))
    if op == "head":
        return capture_stdout(cli_module.run_head_local, str(payload["head_id"]))
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
    debug_log: Any,
) -> dict:
    perf = PerfRecorder(name=f"daemon.default_op.{op}")
    with phase(perf, "request_workdir"):
        with request_workdir(payload, process_state_lock=process_state_lock):
            with phase(perf, "run_op_capture_stdout"):
                stdout = run_op_capture_stdout_fn(op, payload)
    debug_log(f"out op={op} stdout_len={len(stdout)}")
    perf.emit_stderr()
    return {"stdout": stdout}
