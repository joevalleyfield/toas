"""Python source execution through the shared subprocess runner."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from .shell_ops import run_subprocess


def validate_python_script_args(args: dict, *, workspace_path_fn) -> tuple[str, Path, int]:
    script = args.get("script")
    if not isinstance(script, str) or not script.strip():
        raise RuntimeError("invalid arguments for tool python_script: script must be a non-empty string")
    cwd_arg = args.get("cwd", ".")
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for tool python_script: cwd must be a string")
    try:
        cwd = workspace_path_fn(cwd_arg)
    except RuntimeError as exc:
        raise RuntimeError("tool python_script disallows cwd outside workspace") from exc
    if not cwd.is_dir():
        raise RuntimeError("tool python_script requires cwd to be a directory")
    timeout_s = args.get("timeout_s", 5)
    if not isinstance(timeout_s, int) or timeout_s <= 0:
        raise RuntimeError("invalid arguments for tool python_script: timeout_s must be a positive int")
    return script, cwd, timeout_s


def run_python_script(args: dict, *, workspace_path_fn, stream_stdout_override: bool | None = None) -> dict:
    script, cwd, timeout_s = validate_python_script_args(args, workspace_path_fn=workspace_path_fn)
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".py",
            prefix="toas-script-",
            dir=cwd,
            delete=False,
        ) as handle:
            handle.write(script)
            path = Path(handle.name)
        result = run_subprocess(
            [sys.executable, str(path)],
            cwd=cwd,
            timeout_s=timeout_s,
            env=dict(os.environ),
            stream_stdout_override=stream_stdout_override,
            tool_name="python_script",
        )
        result["tool_name"] = "python_script"
        result["cwd"] = str(cwd)
        return result
    finally:
        if path is not None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
