from pathlib import Path


def adapt_call_for_execution(
    raw_call: dict,
    *,
    default_shell_cwd: str | None,
    default_shell_env: dict[str, str | None] | None,
) -> dict:
    call = raw_call
    if default_shell_cwd is not None and isinstance(raw_call.get("args"), dict):
        args = dict(raw_call["args"])
        base = Path(default_shell_cwd).expanduser().resolve()

        if raw_call.get("tool_name") == "shell":
            cwd_arg = args.get("cwd")
            if not isinstance(cwd_arg, str):
                args["cwd"] = str(base)
            else:
                candidate = Path(cwd_arg).expanduser()
                resolved = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
                args["cwd"] = str(resolved)
            if default_shell_env:
                args["env"] = {
                    key: value
                    for key, value in default_shell_env.items()
                    if value is not None
                }

        if raw_call.get("tool_name") in {
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

        call = {**raw_call, "args": args}
    return call


def _apply_intention(result: dict, raw_call: dict) -> dict:
    raw_intent = raw_call.get("intent")
    if not isinstance(raw_intent, str) or not raw_intent.strip():
        raw_intent = raw_call.get("intention")
    if isinstance(raw_intent, str) and raw_intent.strip():
        result["intention"] = raw_intent.strip()
    return result


def execute_plan_calls(
    plan: list[dict],
    *,
    execute_call,
    default_shell_cwd: str | None = None,
    default_shell_env: dict[str, str | None] | None = None,
) -> list[dict]:
    results = []
    for raw_call in plan:
        call = adapt_call_for_execution(
            raw_call,
            default_shell_cwd=default_shell_cwd,
            default_shell_env=default_shell_env,
        )
        try:
            output = execute_call(call)
        except RuntimeError as exc:
            error_result = {
                "tool_name": call.get("tool_name"),
                "ok": False,
                "summary": str(exc),
                "error": str(exc),
            }
            repair_suggestion = getattr(exc, "repair_suggestion", None)
            if isinstance(repair_suggestion, dict) and repair_suggestion:
                error_result["repair_suggestion"] = repair_suggestion
            results.append(_apply_intention(error_result, raw_call))
            continue
        results.append(_apply_intention(output, raw_call))
    return results
