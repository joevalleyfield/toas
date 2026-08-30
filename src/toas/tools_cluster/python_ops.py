"""Python source execution through the shared subprocess runner."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from .shell_ops import run_subprocess


def validate_python_script_args(args: dict, *, workspace_path_fn) -> tuple[str, Path, int, list[str], bool, Path, bool]:
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
    runtime = args.get("runtime", [sys.executable])
    if not isinstance(runtime, list) or not runtime or not all(isinstance(part, str) and part for part in runtime):
        raise RuntimeError("invalid arguments for tool python_script: runtime must be a non-empty list[str]")
    persist = args.get("persist", False)
    if not isinstance(persist, bool):
        raise RuntimeError("invalid arguments for tool python_script: persist must be a bool")
    path_arg = args.get("path", "./script###.py")
    if not isinstance(path_arg, str) or not path_arg.strip():
        raise RuntimeError("invalid arguments for tool python_script: path must be a non-empty string")
    overwrite = args.get("overwrite", False)
    if not isinstance(overwrite, bool):
        raise RuntimeError("invalid arguments for tool python_script: overwrite must be a bool")
    if overwrite and not persist:
        raise RuntimeError("invalid arguments for tool python_script: overwrite requires persist=true")
    path = Path(path_arg).expanduser()
    target = path.resolve() if path.is_absolute() else (cwd / path).resolve()
    try:
        target = workspace_path_fn(str(target))
    except RuntimeError as exc:
        raise RuntimeError("tool python_script disallows path outside workspace") from exc
    if not target.parent.is_dir():
        raise RuntimeError("tool python_script requires the parent of path to be a directory")
    return script, cwd, timeout_s, runtime, persist, target, overwrite


def run_python_script(args: dict, *, workspace_path_fn, stream_stdout_override: bool | None = None) -> dict:
    script, cwd, timeout_s, runtime, persist, target, overwrite = validate_python_script_args(
        args, workspace_path_fn=workspace_path_fn
    )
    path: Path | None = None
    try:
        if "###" in str(target.name):
            prefix, suffix = target.name.split("###", 1)
            fd, generated = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=target.parent)
            path = Path(generated)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(script)
        else:
            mode = "w" if overwrite else "x"
            with target.open(mode, encoding="utf-8") as handle:
                handle.write(script)
            path = target
        result = run_subprocess(
            [*runtime, str(path)],
            cwd=cwd,
            timeout_s=timeout_s,
            env=dict(os.environ),
            stream_stdout_override=stream_stdout_override,
            tool_name="python_script",
        )
        result["tool_name"] = "python_script"
        result["cwd"] = str(cwd)
        result["script_path"] = str(path)
        result["persist"] = persist
        return result
    finally:
        if path is not None and not persist:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
