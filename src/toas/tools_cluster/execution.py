import traceback
from pathlib import Path

from ..runtime.environment_policy import active_environment_overrides


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
) -> list[dict]:
    if default_process_env is None:
        default_process_env = default_shell_env
    with active_environment_overrides(default_process_env):
        results = []
        for raw_call in plan:
            call = adapt_call_for_execution(
                raw_call,
                default_shell_cwd=default_shell_cwd,
                default_process_env=default_process_env,
                default_shell_timeout_s=default_shell_timeout_s,
                default_timeout_s=default_timeout_s,
            )
            try:
                output = execute_call(call)
            except TimeoutError as exc:
                results.append(
                    _apply_intention(
                        _raised_failure_result(
                            call=call,
                            exc=exc,
                            failure_kind="timeout",
                            outcome="indeterminate",
                        ),
                        raw_call,
                    )
                )
                break
            except ConnectionError as exc:
                results.append(
                    _apply_intention(
                        _raised_failure_result(
                            call=call,
                            exc=exc,
                            failure_kind="transport",
                            outcome="indeterminate",
                        ),
                        raw_call,
                    )
                )
                break
            except ChildProcessError as exc:
                results.append(
                    _apply_intention(
                        _raised_failure_result(
                            call=call,
                            exc=exc,
                            failure_kind="process",
                            outcome="indeterminate",
                        ),
                        raw_call,
                    )
                )
                break
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
                results.append(_apply_intention(error_result, raw_call))
                break
            except Exception as exc:
                failure_kind, outcome = _classify_runtime_failure(str(exc))
                error_result = _raised_failure_result(
                    call=call,
                    exc=exc,
                    failure_kind=failure_kind,
                    outcome=outcome,
                    include_traceback=True,
                )
                results.append(_apply_intention(error_result, raw_call))
                break
            projected = _apply_intention(_annotate_returned_failure(output), raw_call)
            results.append(projected)
            if projected.get("ok") is False:
                break
        return results


