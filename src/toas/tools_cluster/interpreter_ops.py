"""Explicit-runtime execution for unregistered language fences."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .shell_ops import run_subprocess


def run_interpreter_script(args: dict, *, workspace_path_fn) -> dict:
    language = args.get("language")
    script = args.get("script")
    runtime = args.get("runtime")
    if not isinstance(language, str) or not language.strip():
        raise RuntimeError("invalid arguments for tool interpreter_script: language must be a non-empty string")
    if not isinstance(script, str) or not script.strip():
        raise RuntimeError("invalid arguments for tool interpreter_script: script must be a non-empty string")
    if not isinstance(runtime, list) or not runtime or not all(isinstance(part, str) and part for part in runtime):
        raise RuntimeError("invalid arguments for tool interpreter_script: runtime must be a non-empty list[str]")
    cwd_arg = args.get("cwd", ".")
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for tool interpreter_script: cwd must be a string")
    try:
        cwd = workspace_path_fn(cwd_arg)
    except RuntimeError as exc:
        raise RuntimeError("tool interpreter_script disallows cwd outside workspace") from exc
    if not cwd.is_dir():
        raise RuntimeError("tool interpreter_script requires cwd to be a directory")
    timeout_s = args.get("timeout_s", 5)
    if timeout_s is not None and (not isinstance(timeout_s, int) or timeout_s <= 0):
        raise RuntimeError("invalid arguments for tool interpreter_script: timeout_s must be a positive int")
    persist = args.get("persist", False)
    if not isinstance(persist, bool):
        raise RuntimeError("invalid arguments for tool interpreter_script: persist must be a bool")
    path_arg = args.get("path", f"./script###{language}")
    if not isinstance(path_arg, str) or not path_arg.strip():
        raise RuntimeError("invalid arguments for tool interpreter_script: path must be a non-empty string")
    overwrite = args.get("overwrite", False)
    if not isinstance(overwrite, bool):
        raise RuntimeError("invalid arguments for tool interpreter_script: overwrite must be a bool")
    if overwrite and not persist:
        raise RuntimeError("invalid arguments for tool interpreter_script: overwrite requires persist=true")
    path = Path(path_arg).expanduser()
    target = path.resolve() if path.is_absolute() else (cwd / path).resolve()
    try:
        target = workspace_path_fn(str(target))
    except RuntimeError as exc:
        raise RuntimeError("tool interpreter_script disallows path outside workspace") from exc
    if not target.parent.is_dir():
        raise RuntimeError("tool interpreter_script requires the parent of path to be a directory")
    artifact: Path | None = None
    try:
        if "###" in target.name:
            prefix, suffix = target.name.split("###", 1)
            fd, generated = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=target.parent)
            artifact = Path(generated)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(script)
        else:
            mode = "w" if overwrite else "x"
            with target.open(mode, encoding="utf-8") as handle:
                handle.write(script)
            artifact = target
        try:
            result = run_subprocess(
                [*runtime, str(artifact)],
                cwd=cwd,
                timeout_s=timeout_s,
                env=dict(os.environ),
                tool_name="interpreter_script",
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"tool interpreter_script runtime not found: {runtime[0]}") from exc
        result.update(
            tool_name="interpreter_script",
            language=language,
            runtime=runtime,
            cwd=str(cwd),
            script_path=str(artifact),
            persist=persist,
        )
        return result
    finally:
        if artifact is not None and not persist:
            try:
                artifact.unlink()
            except FileNotFoundError:
                pass
