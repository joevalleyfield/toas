"""Lane-specific parsers for explicitly activated executable and materialization fences."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any

from ..graph import normalize_tool_plan
from .fence_activation import FenceActivation, classify_fence_activation
from .markdown_fence import MarkdownFence, scan_markdown_fences


def _resolve_fence_script_ref(ref_str: str) -> str | None:
    ref_path = Path(ref_str)
    if not ref_path.is_file():
        scratch_path = Path(".toas/scratch") / f"{ref_str}.txt"
        if scratch_path.is_file():
            ref_path = scratch_path
    if ref_path.is_file():
        try:
            return ref_path.read_text(encoding="utf-8")
        except OSError:
            return None
    return None


def _resolve_fence_stdin(
    stdin_str: str,
    *,
    content: str | None = None,
    workspace_root: Path | None = None,
) -> str | None:
    stdin_val = stdin_str.strip()
    if not stdin_val:
        return None

    match = re.match(r"^(?:\.toas/)?scratch/(ib_[a-zA-Z0-9_-]+)(?:\.txt)?$", stdin_val)
    block_id = match.group(1) if match else (stdin_val if stdin_val.startswith("ib_") else None)

    if block_id:
        scratch_file = (
            (workspace_root / ".toas" / "scratch" / f"{block_id}.txt")
            if workspace_root
            else Path(".toas/scratch") / f"{block_id}.txt"
        )
        if scratch_file.is_file():
            try:
                return scratch_file.read_text(encoding="utf-8")
            except OSError:
                return None
        if content:
            pattern = re.compile(r'(?ms)^(`{3,})[^\n]*block_id="?([a-zA-Z0-9_-]+)"?[^\n]*\n(.*?)\n\1$')
            for m in pattern.finditer(content):
                if m.group(2) == block_id:
                    return m.group(3)
        return None

    target = (workspace_root / stdin_val) if workspace_root else Path(stdin_val)
    if target.is_file():
        try:
            return target.read_text(encoding="utf-8")
        except OSError:
            return None

    scratch_file = (
        (workspace_root / ".toas" / "scratch" / f"{stdin_val}.txt")
        if workspace_root
        else Path(".toas/scratch") / f"{stdin_val}.txt"
    )
    if scratch_file.is_file():
        try:
            return scratch_file.read_text(encoding="utf-8")
        except OSError:
            return None

    return None


def _apply_activation_io_channels(call: dict[str, Any], activation: FenceActivation) -> None:
    if activation.stdin:
        call["stdin"] = activation.stdin
    if activation.out:
        call["out"] = activation.out
    if activation.err:
        call["err"] = activation.err
    if activation.append_out:
        call["append_out"] = True
    if activation.append_err:
        call["append_err"] = True


def parse_bash_exec_fence(
    fence: MarkdownFence,
    content: str | None = None,
) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if (
        activation.status != "active"
        or activation.language != "bash"
        or not activation.has_exec
        or activation.has_write
    ):
        return None
    lines = fence.body.splitlines()
    nonempty = [line for line in lines if line.strip()]
    if nonempty and all(line.lstrip().startswith("$ ") for line in nonempty):
        script = "\n".join(line.lstrip()[2:] for line in lines if line.strip())
    else:
        script = fence.body.rstrip("\r\n")
    if not script.strip():
        if activation.ref:
            resolved = _resolve_fence_script_ref(activation.ref)
            if resolved is not None and resolved.strip():
                script = resolved.rstrip("\r\n")
            else:
                return None
        else:
            return None
    args: dict[str, Any] = {"script": script}
    for token in fence.info_tokens[1:]:
        if "=" in token:
            key, value = token.split("=", 1)
            if key == "runtime":
                try:
                    args[key] = shlex.split(value)
                except ValueError:
                    return None
            elif key == "timeout_s":
                if not value.isdigit() or int(value) <= 0:
                    return None
                args[key] = int(value)
    if activation.stdin:
        resolved_stdin = _resolve_fence_stdin(activation.stdin, content=content)
        if resolved_stdin is None:
            return None
        args["input"] = resolved_stdin
    call = {"tool_name": "shell_script", "args": args}
    _apply_activation_io_channels(call, activation)
    return [call]


def extract_bash_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_bash_exec_fence(fence, content=content)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_exec_fence(fence: MarkdownFence) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if (
        activation.status != "active"
        or activation.language != "json"
        or not activation.has_exec
        or activation.has_write
    ):
        return None
    try:
        parsed = json.loads(fence.body, object_pairs_hook=_reject_duplicate_json_keys)
    except (TypeError, ValueError):
        return None
    plan, _ = normalize_tool_plan(parsed)
    return plan


def json_exec_fence_toolset(fence: MarkdownFence) -> str | None:
    activation = classify_fence_activation(fence)
    if activation.status == "active" and activation.language == "json":
        return activation.toolset
    return None


def extract_json_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_json_exec_fence(fence)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans


def parse_python_exec_fence(
    fence: MarkdownFence,
    content: str | None = None,
) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if (
        activation.status != "active"
        or activation.language != "python"
        or not activation.has_exec
        or activation.has_write
    ):
        return None
    script = fence.body.rstrip("\r\n")
    if not script.strip():
        if activation.ref:
            resolved = _resolve_fence_script_ref(activation.ref)
            if resolved is not None and resolved.strip():
                script = resolved.rstrip("\r\n")
            else:
                return None
        else:
            return None
    args: dict[str, Any] = {"script": script}
    for token in fence.info_tokens[1:]:
        if "=" in token:
            key, value = token.split("=", 1)
            if key == "runtime":
                args[key] = value.split()
            elif key in {"cwd", "path"}:
                args[key] = value
            elif key == "timeout_s":
                if not value.isdigit() or int(value) <= 0:
                    return None
                args[key] = int(value)
            elif key in {"persist", "overwrite"}:
                if value.casefold() not in {"true", "false"}:
                    return None
                args[key] = value.casefold() == "true"
    if activation.stdin:
        resolved_stdin = _resolve_fence_stdin(activation.stdin, content=content)
        if resolved_stdin is None:
            return None
        args["input"] = resolved_stdin
    call = {"tool_name": "python_script", "args": args}
    _apply_activation_io_channels(call, activation)
    return [call]


def extract_python_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_python_exec_fence(fence, content=content)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans


def parse_powershell_exec_fence(
    fence: MarkdownFence,
    content: str | None = None,
) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if (
        activation.status != "active"
        or activation.language != "powershell"
        or not activation.has_exec
        or activation.has_write
    ):
        return None
    script = fence.body.rstrip("\r\n")
    if not script.strip():
        if activation.ref:
            resolved = _resolve_fence_script_ref(activation.ref)
            if resolved is not None and resolved.strip():
                script = resolved.rstrip("\r\n")
            else:
                return None
        else:
            return None
    args: dict[str, Any] = {"script": script}
    for token in fence.info_tokens[1:]:
        if "=" in token:
            key, value = token.split("=", 1)
            if key == "runtime":
                args[key] = value.split()
            elif key in {"cwd", "path"}:
                args[key] = value
            elif key == "timeout_s":
                if not value.isdigit() or int(value) <= 0:
                    return None
                args[key] = int(value)
            elif key in {"persist", "overwrite"}:
                if value.casefold() not in {"true", "false"}:
                    return None
                args[key] = value.casefold() == "true"
    if activation.stdin:
        resolved_stdin = _resolve_fence_stdin(activation.stdin, content=content)
        if resolved_stdin is None:
            return None
        args["input"] = resolved_stdin
    call = {"tool_name": "powershell_script", "args": args}
    _apply_activation_io_channels(call, activation)
    return [call]


def extract_powershell_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_powershell_exec_fence(fence, content=content)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans


def parse_interpreter_exec_fence(
    fence: MarkdownFence,
    content: str | None = None,
) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if (
        activation.status != "active"
        or activation.language in {"bash", "json", "powershell", "python", "yaml"}
        or not activation.has_exec
        or activation.has_write
    ):
        return None
    script = fence.body.rstrip("\r\n")
    if not script.strip():
        if activation.ref:
            resolved = _resolve_fence_script_ref(activation.ref)
            if resolved is not None and resolved.strip():
                script = resolved.rstrip("\r\n")
            else:
                return None
        else:
            return None
    runtime = next(
        (
            token.split("=", 1)[1].split()
            for token in fence.info_tokens[1:]
            if token.startswith("runtime=")
        ),
        None,
    )
    args: dict[str, Any] = {"language": activation.language, "script": script, "runtime": runtime}
    for token in fence.info_tokens[1:]:
        if "=" in token:
            key, value = token.split("=", 1)
            if key in {"cwd", "path"}:
                args[key] = value
            elif key == "timeout_s":
                if not value.isdigit() or int(value) <= 0:
                    return None
                args[key] = int(value)
            elif key in {"persist", "overwrite"}:
                if value.casefold() not in {"true", "false"}:
                    return None
                args[key] = value.casefold() == "true"
    if activation.stdin:
        resolved_stdin = _resolve_fence_stdin(activation.stdin, content=content)
        if resolved_stdin is None:
            return None
        args["input"] = resolved_stdin
    call = {"tool_name": "interpreter_script", "args": args}
    _apply_activation_io_channels(call, activation)
    return [call]


def extract_interpreter_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_interpreter_exec_fence(fence, content=content)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans


def parse_write_fence(
    fence: MarkdownFence,
    content: str | None = None,
) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if activation.status != "active" or not activation.has_write or not activation.path:
        return None
    fence_content = fence.body
    if not fence_content.strip() and activation.ref:
        resolved = _resolve_fence_script_ref(activation.ref)
        if resolved is not None:
            fence_content = resolved
        else:
            return None
    write_args: dict[str, Any] = {
        "path": activation.path,
        "content": fence_content,
    }
    for token in fence.info_tokens[1:]:
        if "=" in token:
            key, value = token.split("=", 1)
            if key in {"overwrite", "force"}:
                if value.casefold() in {"true", "false"}:
                    write_args["force"] = value.casefold() == "true"
            elif key in {"append", "mode"}:
                if value.casefold() in {"true", "append"}:
                    write_args["append"] = True
    plan: list[dict[str, Any]] = [{"tool_name": "write_file", "args": write_args}]
    if activation.has_exec:
        script = fence_content.rstrip("\r\n")
        exec_call: dict[str, Any] | None = None
        if activation.language == "python":
            py_args: dict[str, Any] = {
                "script": script,
                "path": activation.path,
                "persist": True,
            }
            for token in fence.info_tokens[1:]:
                if "=" in token:
                    key, value = token.split("=", 1)
                    if key == "runtime":
                        py_args[key] = value.split()
                    elif key == "cwd":
                        py_args[key] = value
                    elif key == "timeout_s" and value.isdigit() and int(value) > 0:
                        py_args[key] = int(value)
                    elif key in {"overwrite", "force"} and value.casefold() in {"true", "false"}:
                        py_args["overwrite"] = value.casefold() == "true"
            exec_call = {"tool_name": "python_script", "args": py_args}
        elif activation.language == "bash":
            sh_args: dict[str, Any] = {"script": script}
            for token in fence.info_tokens[1:]:
                if "=" in token:
                    key, value = token.split("=", 1)
                    if key == "runtime":
                        try:
                            sh_args[key] = shlex.split(value)
                        except ValueError:
                            return None
                    elif key == "timeout_s" and value.isdigit() and int(value) > 0:
                        sh_args[key] = int(value)
            exec_call = {"tool_name": "shell_script", "args": sh_args}
        elif activation.language == "powershell":
            ps_args: dict[str, Any] = {"script": script, "path": activation.path, "persist": True}
            for token in fence.info_tokens[1:]:
                if "=" in token:
                    key, value = token.split("=", 1)
                    if key == "runtime":
                        ps_args[key] = value.split()
                    elif key == "cwd":
                        ps_args[key] = value
                    elif key == "timeout_s" and value.isdigit() and int(value) > 0:
                        ps_args[key] = int(value)
            exec_call = {"tool_name": "powershell_script", "args": ps_args}
        elif activation.predicate == "explicit-runtime":
            runtime = next(
                (
                    token.split("=", 1)[1].split()
                    for token in fence.info_tokens[1:]
                    if token.startswith("runtime=")
                ),
                None,
            )
            exec_call = {
                "tool_name": "interpreter_script",
                "args": {
                    "language": activation.language,
                    "script": script,
                    "runtime": runtime,
                    "path": activation.path,
                    "persist": True,
                },
            }
        if exec_call is not None:
            if activation.stdin:
                resolved_stdin = _resolve_fence_stdin(activation.stdin, content=content)
                if resolved_stdin is None:
                    return None
                exec_call["args"]["input"] = resolved_stdin
            _apply_activation_io_channels(exec_call, activation)
            plan.append(exec_call)
    return plan


def extract_write_fence_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_write_fence(fence, content=content)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans
