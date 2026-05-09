from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from ..shell_grants import shell_command_allowed, shell_script_segment_commands

SHELL_OPERATOR_TOKENS = {"|", "||", "&&", ";", ">", ">>", "<", "2>", "&>"}


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
) -> dict:
    effective_env = _normalize_windows_shell_env(env if env is not None else dict(os.environ))
    stream_stdout = str(effective_env.get("TOAS_STREAM_STDOUT", "")).strip().lower() in {"1", "true", "yes", "on"}
    if stream_stdout_override is not None:
        stream_stdout = stream_stdout_override
    try:
        if stream_stdout:
            proc = subprocess.Popen(
                argv,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                env=effective_env,
            )
            chunks: list[str] = []
            chunks_lock = threading.Lock()

            def _reader() -> None:
                stream = proc.stdout
                if stream is None:
                    return
                try:
                    for chunk in iter(stream.readline, ""):
                        with chunks_lock:
                            chunks.append(chunk)
                        print(chunk, end="", flush=True)
                finally:
                    stream.close()

            reader = threading.Thread(target=_reader, daemon=True)
            reader.start()
            try:
                returncode = proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired as exc:
                proc.kill()
                proc.wait()
                raise RuntimeError(f"tool shell timed out after {timeout_s}s") from exc
            reader.join(timeout=1.0)
            if reader.is_alive():
                # Best-effort drain for pathological streams without newlines.
                stream = proc.stdout
                if stream is not None:
                    remainder = stream.read()
                    if remainder:
                        with chunks_lock:
                            chunks.append(remainder)
                        print(remainder, end="", flush=True)
            stdout = "".join(chunks)
            stderr = ""
            completed = subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)
        else:
            completed = subprocess.run(
                argv,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
                env=effective_env,
            )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"tool shell timed out after {timeout_s}s") from exc

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


def needs_shell(command: str) -> bool:
    return any(token in command for token in ("|", "||", "&&", ";", ">", "<"))


def shell_launcher_argv(command: str) -> list[str]:
    if sys.platform.startswith("win"):
        if shutil.which("bash"):
            return ["bash", "-ic", command]
        if shutil.which("sh"):
            return ["sh", "-lc", command]
        return ["cmd.exe", "/d", "/s", "/c", command]
    return ["sh", "-lc", command]


def _normalize_windows_shell_env(env: dict[str, str]) -> dict[str, str]:
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

    if isinstance(command, str) and command.strip() and needs_shell(command):
        return run_subprocess(
            shell_launcher_argv(command),
            cwd=resolved_cwd,
            timeout_s=timeout_s,
            env=env,
            stream_stdout_override=True,
        )

    operator = next((part for part in argv if part in SHELL_OPERATOR_TOKENS), None)
    if operator is not None:
        command_line = command.strip() if isinstance(command, str) and command.strip() else shlex.join(argv)
        shell_hint = shlex.join(shell_launcher_argv(command_line))
        hint = f"needs shell for operator {operator!r}; try: {shell_hint}"
        return {
            "tool_name": "shell",
            "ok": False,
            "summary": "needs shell",
            "argv": argv,
            "cwd": str(resolved_cwd),
            "exit_code": None,
            "stdout": "",
            "stderr": hint,
            "content": f"needs shell\nstderr:\n{hint}",
        }

    return run_subprocess(
        argv,
        cwd=resolved_cwd,
        timeout_s=timeout_s,
        env=env,
        stream_stdout_override=True,
    )


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
        argv, cwd, timeout_s, env = validate_shell_args(
            args,
            workspace_path_fn=workspace_path_fn,
            effective_shell_allowed=effective_shell_allowed,
        )
        return run_subprocess(argv, cwd=cwd, timeout_s=timeout_s, env=env)

    if context != "user":
        raise RuntimeError(f"invalid shell context: {context}")

    argv = args.get("argv")
    command = args.get("command")
    if not (isinstance(argv, list) and argv and all(isinstance(part, str) for part in argv)):
        if isinstance(command, str) and command.strip():
            cleaned = command.strip("\n") if "\n" in command else command.strip()
            if "\n" in cleaned:
                argv = ["sh", "-lc", cleaned]
            else:
                try:
                    parsed = shlex.split(cleaned)
                except ValueError:
                    parsed = None
                argv = parsed if parsed else ["sh", "-lc", cleaned]
        else:
            raise RuntimeError("invalid arguments for user shell command: argv must be a non-empty list[str]")

    timeout_s = args.get("timeout_s")
    if timeout_s is not None and (not isinstance(timeout_s, int) or timeout_s <= 0):
        raise RuntimeError("invalid arguments for user shell command: timeout_s must be a positive int")

    cwd_arg = args.get("cwd")
    if cwd_arg is None:
        cwd_arg = base_cwd if isinstance(base_cwd, str) and base_cwd else "."
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for user shell command: cwd must be a string")

    if base_cwd is not None:
        base = Path(base_cwd).expanduser().resolve()
        candidate = Path(cwd_arg).expanduser()
        resolved_cwd = str(candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve())
    else:
        resolved_cwd = str(Path(cwd_arg).expanduser().resolve())

    if not isinstance(command, str) or not command.strip():
        command = shlex.join(argv)

    return run_user_shell(
        argv,
        cwd=resolved_cwd,
        timeout_s=timeout_s,
        command=command,
        env_overrides=env_overrides,
    )
