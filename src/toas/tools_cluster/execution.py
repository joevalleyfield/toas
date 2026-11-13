import traceback
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import monotonic

from ..runtime.environment_policy import active_environment_overrides, active_stream_stdout
from ..runtime.tool_stream_context import (
    emit_tool_done,
    emit_tool_start,
    is_tool_done_emitted,
)


def apply_io_redirection(
    output: dict,
    call: dict,
    workspace_root: Path | None = None,
) -> dict:
    out_target = call.get("out") or (call.get("args", {}).get("out") if isinstance(call.get("args"), dict) else None)
    err_target = call.get("err") or (call.get("args", {}).get("err") if isinstance(call.get("args"), dict) else None)
    if not out_target and not err_target:
        return output

    base_dir = workspace_root or Path.cwd()
    stdout_text = output.get("stdout") or output.get("content") or output.get("text") or ""
    stderr_text = output.get("stderr") or ""

    if out_target and not output.get("out_redirected"):
        append_out = bool(
            call.get("append_out")
            or (call.get("args", {}).get("append_out") if isinstance(call.get("args"), dict) else False)
        )
        if out_target == "scratch":
            block_id = f"ib_{sha256(stdout_text.encode('utf-8')).hexdigest()[:16]}"
            target_path = base_dir / ".toas" / "scratch" / f"{block_id}.txt"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append_out else "w"
            with target_path.open(mode, encoding="utf-8") as f:
                f.write(stdout_text)
            output["out_target"] = f".toas/scratch/{block_id}.txt"
            output["out_block_id"] = block_id
            output["out_redirected"] = True
        else:
            target_path = (base_dir / out_target) if not Path(out_target).is_absolute() else Path(out_target)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append_out else "w"
            with target_path.open(mode, encoding="utf-8") as f:
                f.write(stdout_text)
            block_id = f"ib_{sha256(stdout_text.encode('utf-8')).hexdigest()[:16]}"
            output["out_target"] = out_target
            output["out_block_id"] = block_id
            output["out_redirected"] = True

    if err_target and not output.get("err_redirected"):
        append_err = bool(
            call.get("append_err")
            or (call.get("args", {}).get("append_err") if isinstance(call.get("args"), dict) else False)
        )
        if err_target == "scratch":
            block_id = f"ib_{sha256(stderr_text.encode('utf-8')).hexdigest()[:16]}"
            target_path = base_dir / ".toas" / "scratch" / f"{block_id}.txt"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append_err else "w"
            with target_path.open(mode, encoding="utf-8") as f:
                f.write(stderr_text)
            output["err_target"] = f".toas/scratch/{block_id}.txt"
            output["err_block_id"] = block_id
            output["err_redirected"] = True
        else:
            target_path = (base_dir / err_target) if not Path(err_target).is_absolute() else Path(err_target)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append_err else "w"
            with target_path.open(mode, encoding="utf-8") as f:
                f.write(stderr_text)
            block_id = f"ib_{sha256(stderr_text.encode('utf-8')).hexdigest()[:16]}"
            output["err_target"] = err_target
            output["err_block_id"] = block_id
            output["err_redirected"] = True

    parts = [f"exit={output.get('exit_code', 0)}"]
    if output.get("out_redirected"):
        parts.append(f"stdout redirected to {output['out_target']}")
    elif output.get("stdout"):
        parts.append(f"stdout:\n{output['stdout']}")

    if output.get("err_redirected"):
        parts.append(f"stderr redirected to {output['err_target']}")
    elif output.get("stderr"):
        parts.append(f"stderr:\n{output['stderr']}")

    output["content"] = "\n".join(parts)
    return output


def adapt_call_for_execution(
    raw_call: dict,
    *,
    default_shell_cwd: str | None,
    default_process_env: dict[str, str | None] | None = None,
    default_shell_env: dict[str, str | None] | None = None,
    default_shell_timeout_s: int | None = None,
    default_timeout_s: int | None = None,
) -> dict:
    call = raw_call
    process_env = default_process_env if default_process_env is not None else default_shell_env
    if isinstance(raw_call.get("args"), dict):
        args = dict(raw_call["args"])
        base = Path(default_shell_cwd).expanduser().resolve() if default_shell_cwd is not None else None

        if "timeout_s" not in args:
            if raw_call.get("tool_name") in {"shell", "shell_script"}:
                if default_shell_timeout_s is not None:
                    args["timeout_s"] = default_shell_timeout_s
            elif default_timeout_s is None and raw_call.get("tool_name") in {
                "python_script",
                "powershell_script",
                "interpreter_script",
                "search",
            }:
                args["timeout_s"] = default_timeout_s

        if raw_call.get("tool_name") == "shell" and base is not None:
            cwd_arg = args.get("cwd")
            if not isinstance(cwd_arg, str):
                args["cwd"] = str(base)
            else:
                candidate = Path(cwd_arg).expanduser()
                resolved = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
                args["cwd"] = str(resolved)
            if process_env:
                args["env"] = {key: value for key, value in process_env.items() if value is not None}

        if base is not None and raw_call.get("tool_name") in {
            "read_file",
            "search",
            "write_file",
            "get_structure",
            "code_survey",
            "replace_range",
            "replace_block",
        } and isinstance(args.get("path"), str):
            path_arg = args["path"]
            candidate = Path(path_arg).expanduser()
            resolved = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
            args["path"] = str(resolved)

        if args != raw_call["args"]:
            call = {**raw_call, "args": args}
    return call


def _apply_intention(result: dict, raw_call: dict) -> dict:
    raw_intent = raw_call.get("intent")
    if not isinstance(raw_intent, str) or not raw_intent.strip():
        raw_intent = raw_call.get("intention")
    if isinstance(raw_intent, str) and raw_intent.strip():
        result["intention"] = raw_intent.strip()
    return result


def _classify_runtime_failure(message: str) -> tuple[str, str]:
    if message.startswith("invalid arguments for tool ") or message.startswith("unknown tool:"):
        return "validation", "failed"
    if "disallows command" in message or "override needed" in message:
        return "authorization", "blocked"
    if "timed out" in message:
        return "timeout", "indeterminate"
    return "execution", "failed"


def _annotate_returned_failure(result: dict) -> dict:
    if result.get("ok") is not False:
        return result
    annotated = dict(result)
    annotated.setdefault("failure_kind", "execution")
    annotated.setdefault("outcome", "failed")
    return annotated


def _raised_failure_result(
    *, call: dict, exc: BaseException, failure_kind: str, outcome: str, include_traceback: bool = False
) -> dict:
    result = {
        "tool_name": call.get("tool_name"),
        "ok": False,
        "summary": str(exc),
        "error": str(exc),
        "failure_kind": failure_kind,
        "outcome": outcome,
    }
    if include_traceback:
        tb = traceback.format_exc().strip()
        if tb and tb != "NoneType: None":
            result["traceback"] = tb
    return result


def execute_plan_calls(
    plan: list[dict],
    *,
    execute_call,
    default_shell_cwd: str | None = None,
    default_process_env: dict[str, str | None] | None = None,
    default_shell_env: dict[str, str | None] | None = None,
    default_shell_timeout_s: int | None = None,
    default_timeout_s: int | None = None,
    continue_on_error: bool = False,
    stream_stdout_enabled: bool | None = None,
) -> list[dict]:
    if default_process_env is None:
        default_process_env = default_shell_env
    with (
        active_environment_overrides(default_process_env),
        active_stream_stdout(stream_stdout_enabled is True),
    ):
        results = []
        total = len(plan)
        for idx, raw_call in enumerate(plan, start=1):
            started = monotonic()
            def timed(result: dict, started_at: float = started) -> dict:
                result["duration_ms"] = round((monotonic() - started_at) * 1000)
                result["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                return result
            call_continue_on_error = bool(
                raw_call.get("continue_on_error")
                if "continue_on_error" in raw_call
                else continue_on_error
            )
            call = adapt_call_for_execution(
                raw_call,
                default_shell_cwd=default_shell_cwd,
                default_process_env=default_process_env,
                default_shell_timeout_s=default_shell_timeout_s,
                default_timeout_s=default_timeout_s,
            )
            tool_name = str(call.get("tool_name") or call.get("operation") or "unknown")
            emit_tool_start(operation=tool_name, index=idx, total=total)
            try:
                output = execute_call(call)
            except TimeoutError as exc:
                results.append(
                    timed(_apply_intention(
                        _raised_failure_result(
                            call=call,
                            exc=exc,
                            failure_kind="timeout",
                            outcome="indeterminate",
                        ),
                        raw_call,
                    ))
                )
                if not is_tool_done_emitted():
                    emit_tool_done(operation=tool_name, ok=False, status="indeterminate", index=idx, total=total)
                if not call_continue_on_error:
                    break
                continue
            except ConnectionError as exc:
                results.append(
                    timed(_apply_intention(
                        _raised_failure_result(
                            call=call,
                            exc=exc,
                            failure_kind="transport",
                            outcome="indeterminate",
                        ),
                        raw_call,
                    ))
                )
                if not is_tool_done_emitted():
                    emit_tool_done(operation=tool_name, ok=False, status="indeterminate", index=idx, total=total)
                if not call_continue_on_error:
                    break
                continue
            except ChildProcessError as exc:
                results.append(
                    timed(_apply_intention(
                        _raised_failure_result(
                            call=call,
                            exc=exc,
                            failure_kind="process",
                            outcome="indeterminate",
                        ),
                        raw_call,
                    ))
                )
                if not is_tool_done_emitted():
                    emit_tool_done(operation=tool_name, ok=False, status="indeterminate", index=idx, total=total)
                if not call_continue_on_error:
                    break
                continue
            except RuntimeError as exc:
                failure_kind, outcome = _classify_runtime_failure(str(exc))
                error_result = _raised_failure_result(
                    call=call,
                    exc=exc,
                    failure_kind=failure_kind,
                    outcome=outcome,
                )
                repair_suggestion = getattr(exc, "repair_suggestion", None)
                if isinstance(repair_suggestion, dict) and repair_suggestion:
                    error_result["repair_suggestion"] = repair_suggestion
                unapplied_patch = getattr(exc, "unapplied_patch", None)
                if isinstance(unapplied_patch, str) and unapplied_patch:
                    error_result["unapplied_patch"] = unapplied_patch
                for attr in ("applied_hunks", "failed_hunk", "skipped_hunks", "files_touched"):
                    val = getattr(exc, attr, None)
                    if val is not None:
                        error_result[attr] = val
                results.append(timed(_apply_intention(error_result, raw_call)))
                if not is_tool_done_emitted():
                    emit_tool_done(operation=tool_name, ok=False, status=outcome, index=idx, total=total)
                if not call_continue_on_error:
                    break
                continue
            except Exception as exc:
                failure_kind, outcome = _classify_runtime_failure(str(exc))
                error_result = _raised_failure_result(
                    call=call,
                    exc=exc,
                    failure_kind=failure_kind,
                    outcome=outcome,
                    include_traceback=True,
                )
                unapplied_patch = getattr(exc, "unapplied_patch", None)
                if isinstance(unapplied_patch, str) and unapplied_patch:
                    error_result["unapplied_patch"] = unapplied_patch
                for attr in ("applied_hunks", "failed_hunk", "skipped_hunks", "files_touched"):
                    val = getattr(exc, attr, None)
                    if val is not None:
                        error_result[attr] = val
                results.append(timed(_apply_intention(error_result, raw_call)))
                if not is_tool_done_emitted():
                    emit_tool_done(operation=tool_name, ok=False, status=outcome, index=idx, total=total)
                if not call_continue_on_error:
                    break
                continue
            if isinstance(output, dict):
                output = apply_io_redirection(
                    output,
                    call,
                    workspace_root=Path(default_shell_cwd).expanduser().resolve() if default_shell_cwd is not None else None,
                )
            projected = timed(_apply_intention(_annotate_returned_failure(output), raw_call))
            results.append(projected)
            if not is_tool_done_emitted():
                ok = projected.get("ok") is not False
                status = None if ok else str(projected.get("outcome") or "error")
                emit_tool_done(operation=tool_name, ok=ok, status=status, index=idx, total=total)
            if projected.get("ok") is False and not call_continue_on_error:
                break
        return results


