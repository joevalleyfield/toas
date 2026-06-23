from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

from ..runtime.tool_stream_context import emit_tool_done
from ..shell_grants import shell_command_allowed, shell_script_segment_commands
import glob

from .shell_streaming import run_streaming_subprocess

SHELL_OPERATOR_TOKENS = {"|", "||", "&&", ";", ">", ">>", "<", "2>", "&>"}

GLOB_CHARS = {"*", "?", "["}


def _append_shell_diag(entry: dict) -> None:
    try:
        diag_path = Path(".toas/.toas/error.log")
        diag_path.parent.mkdir(parents=True, exist_ok=True)
        with diag_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.time():.6f} {entry}\n")
    except Exception:
        pass


def validate_shell_args(
    args: dict,
    *,
    workspace_path_fn,
    effective_shell_allowed,
) -> tuple[list[str], Path, int, dict[str, str] | None]:
    argv = args.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
        raise RuntimeError("invalid arguments for tool shell: argv must be a non-empty list[str]")

    if not shell_command_allowed(argv[0], effective_shell_allowed):
        raise RuntimeError(
            f"tool shell disallows command: {argv[0]} "
            "(override needed; stage in user context to run unbounded)"
        )

    timeout_s = args.get("timeout_s", 5)
    if not isinstance(timeout_s, int) or timeout_s <= 0 or timeout_s > 30:
        raise RuntimeError("invalid arguments for tool shell: timeout_s must be an int between 1 and 30")

    cwd_arg = args.get("cwd", ".")
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for tool shell: cwd must be a string")

    try:
        cwd = workspace_path_fn(cwd_arg)
    except RuntimeError as exc:
        raise RuntimeError("tool shell disallows cwd outside workspace") from exc
    if not cwd.is_dir():
        raise RuntimeError("tool shell requires cwd to be a directory")
    if cwd == Path("/"):
        raise RuntimeError("tool shell disallows cwd outside workspace")

    env_raw = args.get("env")
    env: dict[str, str] | None = None
    if env_raw is not None:
        if not isinstance(env_raw, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env_raw.items()):
            raise RuntimeError("invalid arguments for tool shell: env must be a mapping of string keys and values")
        env = dict(os.environ)
        env.update(env_raw)

    return argv, cwd, timeout_s, env


def validate_shell_script_args(
    args: dict,
    *,
    workspace_path_fn,
    effective_shell_allowed,
) -> tuple[str, Path, int, dict[str, str] | None]:
    script = args.get("script")
    if not isinstance(script, str) or not script.strip():
        raise RuntimeError("invalid arguments for tool shell_script: script must be a non-empty string")

    segment_commands = shell_script_segment_commands(script)
    if not segment_commands:
        raise RuntimeError("invalid arguments for tool shell_script: could not parse command segments from script")
    blocked = next((cmd for cmd in segment_commands if not shell_command_allowed(cmd, effective_shell_allowed)), None)
    if blocked is not None:
        raise RuntimeError(
            f"tool shell_script disallows command: {blocked} "
            "(override needed; stage in user context to run unbounded)"
        )

    timeout_s = args.get("timeout_s", 5)
    if not isinstance(timeout_s, int) or timeout_s <= 0 or timeout_s > 30:
        raise RuntimeError("invalid arguments for tool shell_script: timeout_s must be an int between 1 and 30")

    cwd_arg = args.get("cwd", ".")
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for tool shell_script: cwd must be a string")
    try:
        cwd = workspace_path_fn(cwd_arg)
    except RuntimeError as exc:
        raise RuntimeError("tool shell_script disallows cwd outside workspace") from exc
    if not cwd.is_dir():
        raise RuntimeError("tool shell_script requires cwd to be a directory")
    if cwd == Path("/"):
        raise RuntimeError("tool shell_script disallows cwd outside workspace")

    env_raw = args.get("env")
    env: dict[str, str] | None = None
    if env_raw is not None:
        if not isinstance(env_raw, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env_raw.items()):
            raise RuntimeError("invalid arguments for tool shell_script: env must be a mapping of string keys and values")
        env = dict(os.environ)
        env.update(env_raw)

    return script, cwd, timeout_s, env


def run_subprocess(
    argv: list[str],
    *,
    cwd: Path,
    timeout_s: int | None,
    env: dict[str, str] | None = None,
    stream_stdout_override: bool | None = None,
    tool_name: str = "shell",
) -> dict:
    effective_env = _normalize_windows_shell_env(
        env if env is not None else dict(os.environ),
        argv=argv,
    )
    stream_stdout = str(effective_env.get("TOAS_STREAM_STDOUT", "")).strip().lower() in {"1", "true", "yes", "on"}
    if stream_stdout_override is not None:
        stream_stdout = stream_stdout_override
    try:
        if stream_stdout:
            completed = run_streaming_subprocess(
                argv=argv,
                cwd=cwd,
                timeout_s=timeout_s,
                env=effective_env,
            )
        else:
            completed = _run_subprocess_with_timeout_diagnostics(
                argv=argv,
                cwd=cwd,
                timeout_s=timeout_s,
                env=effective_env,
            )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"tool shell timed out after {timeout_s}s") from exc

    result = _shape_subprocess_result(argv=argv, cwd=cwd, completed=completed)
    emit_tool_done(
        operation=tool_name,
        ok=bool(result.get("ok")),
        status=None if bool(result.get("ok")) else "error",
    )
    return result


def _shape_subprocess_result(*, argv: list[str], cwd: Path, completed: subprocess.CompletedProcess) -> dict:
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parts = [f"exit={completed.returncode}"]
    if stdout:
        parts.append(f"stdout:\n{stdout}")
    if stderr:
        parts.append(f"stderr:\n{stderr}")
    return {
        "tool_name": "shell",
        "ok": completed.returncode == 0,
        "summary": f"exit={completed.returncode}",
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "content": "\n".join(parts),
    }


def _run_subprocess_with_timeout_diagnostics(
    *,
    argv: list[str],
    cwd: Path,
    timeout_s: int | None,
    env: dict[str, str],
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _append_shell_diag(
            {
                "kind": "assistant_shell_timeout_probe",
                "argv": argv,
                "cwd": str(cwd),
                "timeout_s": timeout_s,
                "pid": None,
                "exe": shutil.which(argv[0]),
                "ps": "timeout from subprocess.run",
            }
        )
        raise


def _probe_process_snapshot(pid: int) -> str:
    try:
        completed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "pid,ppid,state,etime,command"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return (completed.stdout or completed.stderr or "").strip()
    except Exception as exc:
        return f"ps probe failed: {exc!r}"


def needs_shell(command: str) -> bool:
    return any(
        token in command
        for token in ("|", "||", "&&", ";", ">", "<", "*", "?", "[", "]")
    )

def _expand_globs_in_argv(argv: list[str]) -> list[str]:
    expanded = []
    for part in argv:
        if any(c in part for c in GLOB_CHARS):
            try:
                matches = glob.glob(part)
                if matches:
                    expanded.extend(matches)
                else:
                    expanded.append(part)
            except Exception:
                expanded.append(part)
        else:
            expanded.append(part)
    return expanded


def shell_launcher_argv(command: str) -> list[str]:
    if sys.platform.startswith("win"):
        if shutil.which("bash"):
            return ["bash", "-lc", command]
        if shutil.which("sh"):
            return ["sh", "-lc", command]
        return ["cmd.exe", "/d", "/s", "/c", command]
    return ["sh", "-lc", command]


def _windows_shell_path_entries(shell_executable: str | None) -> list[str]:
    if not shell_executable:
        return []
    shell_path = Path(shell_executable)
    parent = shell_path.parent
    grandparent = parent.parent
    candidates = []
    if grandparent != parent:
        candidates.append(grandparent / "usr" / "bin")
        candidates.append(grandparent / "bin")
    candidates.append(parent)
    ordered: list[str] = []
    for candidate in candidates:
        text = str(candidate)
        if text not in ordered:
            ordered.append(text)
    return ordered


def _normalize_windows_shell_env(env: dict[str, str], *, argv: list[str] | None = None) -> dict[str, str]:
    if not sys.platform.startswith("win"):
        return env
    aliases = {
        "OneDrive": ["ONEDRIVE"],
        "UserProfile": ["USERPROFILE"],
        "ProgramFiles": ["PROGRAMFILES"],
        "AppData": ["APPDATA"],
    }
    for canonical, variants in aliases.items():
        if canonical in env:
            continue
        for variant in variants:
            if variant in env:
                env[canonical] = env[variant]
                break
    shell_executable = None
    if isinstance(argv, list) and argv and isinstance(argv[0], str):
        shell_executable = argv[0]
        if not any(sep in shell_executable for sep in ("/", "\\")):
            shell_executable = shutil.which(shell_executable) or shell_executable
    path_entries = _windows_shell_path_entries(shell_executable)
    if path_entries:
        pathsep = ";" if sys.platform.startswith("win") else os.pathsep
        current_parts = [part for part in env.get("PATH", "").split(pathsep) if part]
        normalized_parts = {part.casefold(): idx for idx, part in enumerate(current_parts)}
        for entry in reversed(path_entries):
            existing_idx = normalized_parts.pop(entry.casefold(), None)
            if existing_idx is not None:
                current_parts.pop(existing_idx)
                normalized_parts = {part.casefold(): idx for idx, part in enumerate(current_parts)}
            current_parts.insert(0, entry)
            normalized_parts = {part.casefold(): idx for idx, part in enumerate(current_parts)}
        env["PATH"] = pathsep.join(current_parts)
    return env


def build_env_with_overrides(env_overrides: dict[str, str | None] | None) -> dict[str, str] | None:
    if not env_overrides:
        return None
    env = dict(os.environ)
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def run_user_shell(
    argv: list[str],
    *,
    cwd: str = ".",
    timeout_s: int | None = None,
    command: str | None = None,
    env_overrides: dict[str, str | None] | None = None,
) -> dict:
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
        raise RuntimeError("invalid user shell command: argv must be a non-empty list[str]")
    if not isinstance(cwd, str):
        raise RuntimeError("invalid user shell command: cwd must be a string")
    if timeout_s is not None and (not isinstance(timeout_s, int) or timeout_s <= 0):
        raise RuntimeError("invalid user shell command: timeout_s must be a positive int")

    resolved_cwd = Path(cwd).expanduser().resolve()
    if not resolved_cwd.is_dir():
        raise RuntimeError("user shell command requires cwd to be a directory")

    env = build_env_with_overrides(env_overrides)
    shell_argv, shell_hint = _resolve_user_shell_execution(argv=argv, command=command)
    if shell_hint is not None:
        return _needs_shell_result(argv=argv, cwd=resolved_cwd, hint=shell_hint)
    assert shell_argv is not None
    return run_subprocess(
        shell_argv,
        cwd=resolved_cwd,
        timeout_s=timeout_s,
        env=env,
        stream_stdout_override=True,
    )


def _resolve_user_shell_execution(*, argv: list[str], command: str | None) -> tuple[list[str] | None, str | None]:
    if isinstance(command, str) and command.strip() and needs_shell(command):
        return shell_launcher_argv(command), None
    operator = next((part for part in argv if part in SHELL_OPERATOR_TOKENS), None)
    if operator is None:
        return argv, None
    command_line = command.strip() if isinstance(command, str) and command.strip() else shlex.join(argv)
    shell_hint = shlex.join(shell_launcher_argv(command_line))
    return None, f"needs shell for operator {operator!r}; try: {shell_hint}"


def _needs_shell_result(*, argv: list[str], cwd: Path, hint: str) -> dict:
    return {
        "tool_name": "shell",
        "ok": False,
        "summary": "needs shell",
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": None,
        "stdout": "",
        "stderr": hint,
        "content": f"needs shell\nstderr:\n{hint}",
    }


def execute_shell_call(
    args: dict,
    *,
    context: str,
    workspace_path_fn,
    effective_shell_allowed,
    base_cwd: str | None = None,
    env_overrides: dict[str, str | None] | None = None,
) -> dict:
    if context == "assistant":
        started = time.time()
        _append_shell_diag(
            {
                "kind": "assistant_shell_start",
                "context": context,
                "args": args,
            }
        )
        argv, cwd, timeout_s, env = validate_shell_args(
            args,
            workspace_path_fn=workspace_path_fn,
            effective_shell_allowed=effective_shell_allowed,
        )
        argv = _expand_globs_in_argv(argv)
        try:
            result = run_subprocess(argv, cwd=cwd, timeout_s=timeout_s, env=env)
            _append_shell_diag(
                {
                    "kind": "assistant_shell_ok",
                    "context": context,
                    "argv": argv,
                    "cwd": str(cwd),
                    "timeout_s": timeout_s,
                    "elapsed_s": round(time.time() - started, 6),
                    "exit_code": result.get("exit_code"),
                    "ok": result.get("ok"),
                    "stdout_len": len(result.get("stdout", "") or ""),
                    "stderr_len": len(result.get("stderr", "") or ""),
                }
            )
            return result
        except Exception as exc:
            _append_shell_diag(
                {
                    "kind": "assistant_shell_error",
                    "context": context,
                    "argv": argv,
                    "cwd": str(cwd),
                    "timeout_s": timeout_s,
                    "elapsed_s": round(time.time() - started, 6),
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    if context != "user":
        raise RuntimeError(f"invalid shell context: {context}")

    command = args.get("command")
    argv = _resolve_user_argv(args=args, command=command)

    timeout_s = args.get("timeout_s")
    if timeout_s is not None and (not isinstance(timeout_s, int) or timeout_s <= 0):
        raise RuntimeError("invalid arguments for user shell command: timeout_s must be a positive int")

    resolved_cwd = _resolve_user_cwd(args=args, base_cwd=base_cwd)

    if not isinstance(command, str) or not command.strip():
        command = shlex.join(argv)

    return run_user_shell(
        argv,
        cwd=resolved_cwd,
        timeout_s=timeout_s,
        command=command,
        env_overrides=env_overrides,
    )


def _resolve_user_argv(*, args: dict, command: str | None) -> list[str]:
    argv = args.get("argv")
    if isinstance(argv, list) and argv and all(isinstance(part, str) for part in argv):
        return argv
    if not (isinstance(command, str) and command.strip()):
        raise RuntimeError("invalid arguments for user shell command: argv must be a non-empty list[str]")
    cleaned = command.strip("\n") if "\n" in command else command.strip()
    if "\n" in cleaned:
        return ["sh", "-lc", cleaned]
    try:
        parsed = shlex.split(cleaned)
    except ValueError:
        parsed = None
    return parsed if parsed else ["sh", "-lc", cleaned]


def _resolve_user_cwd(*, args: dict, base_cwd: str | None) -> str:
    cwd_arg = args.get("cwd")
    if cwd_arg is None:
        cwd_arg = base_cwd if isinstance(base_cwd, str) and base_cwd else "."
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for user shell command: cwd must be a string")
    if base_cwd is not None:
        base = Path(base_cwd).expanduser().resolve()
        candidate = Path(cwd_arg).expanduser()
        return str(candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve())
    return str(Path(cwd_arg).expanduser().resolve())
