from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Any


def run_write_file(args: dict, *, workspace_path_fn) -> dict:
    path_arg = args["path"]
    content = args["content"]

    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool write_file: path must be a non-empty string")
    if not isinstance(content, str):
        raise RuntimeError("invalid arguments for tool write_file: content must be a string")

    path = workspace_path_fn(path_arg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {
        "tool_name": "write_file",
        "ok": True,
        "summary": f"wrote {len(content.encode('utf-8'))} bytes",
        "path": path_arg,
        "bytes_written": len(content.encode("utf-8")),
    }


def run_echo_block(args: dict) -> dict:
    block = args["block"]
    if not isinstance(block, str):
        raise RuntimeError("invalid arguments for tool echo_block: block must be a string")
    lines = block.splitlines()
    leading_ws = [len(line) - len(line.lstrip(" ")) for line in lines if line]
    return {
        "tool_name": "echo_block",
        "ok": True,
        "summary": f"block echo: {len(lines)} lines",
        "line_count": len(lines),
        "leading_spaces": leading_ws,
        "content": block,
    }


def run_read_file(args: dict, *, workspace_path_fn) -> dict:
    path_arg = args["path"]
    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool read_file: path must be a non-empty string")

    path = workspace_path_fn(path_arg)
    if not path.is_file():
        raise RuntimeError(f"tool read_file requires a file: {path_arg}")

    content = path.read_text(encoding="utf-8")
    return {
        "tool_name": "read_file",
        "ok": True,
        "summary": path_arg,
        "path": path_arg,
        "content": content,
    }


def run_search(args: dict, *, workspace_path_fn) -> dict:
    query = args["query"]
    if not isinstance(query, str) or not query:
        raise RuntimeError("invalid arguments for tool search: query must be a non-empty string")

    path_arg = args.get("path", ".")
    if not isinstance(path_arg, str):
        raise RuntimeError("invalid arguments for tool search: path must be a string")

    limit = args.get("limit", 20)
    if not isinstance(limit, int) or limit <= 0 or limit > 200:
        raise RuntimeError("invalid arguments for tool search: limit must be an int between 1 and 200")
    regex = args.get("regex", False)
    if not isinstance(regex, bool):
        raise RuntimeError("invalid arguments for tool search: regex must be a bool")

    path = workspace_path_fn(path_arg)
    command = ["rg", "-n", "--color=never", "--max-count", str(limit)]
    if not regex:
        command.append("-F")
    command.extend([query, str(path)])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if completed.returncode not in (0, 1):
        stderr = completed.stderr.strip() or "rg failed"
        if regex:
            raise RuntimeError(
                f"tool search failed: {stderr}\n"
                "hint: query was treated as regex; set regex=false for literal matching"
            )
        raise RuntimeError(f"tool search failed: {stderr}")

    output = completed.stdout.strip()
    matches = [line for line in output.splitlines() if line]
    return {
        "tool_name": "search",
        "ok": True,
        "summary": f"{len(matches)} matches",
        "query": query,
        "regex": regex,
        "path": path_arg,
        "matches": matches,
        "content": output,
    }


def collect_python_structure(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    entries: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "def"
            start = int(getattr(node, "lineno", 1))
            end = int(getattr(node, "end_lineno", start))
            entries.append(
                {
                    "kind": kind,
                    "name": node.name,
                    "start_line": start,
                    "end_line": end,
                    "path": str(path),
                }
            )
    entries.sort(key=lambda item: (item["path"], item["start_line"], item["name"]))
    return entries


def run_get_structure(args: dict, *, workspace_path_fn) -> dict:
    path_arg = args["path"]
    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool get_structure: path must be a non-empty string")

    path = workspace_path_fn(path_arg)
    if path.is_file():
        if path.suffix != ".py":
            raise RuntimeError(f"tool get_structure currently only supports .py files: {path_arg}")
        structure = collect_python_structure(path)
        return {
            "tool_name": "get_structure",
            "ok": True,
            "summary": f"found {len(structure)} symbols",
            "path": path_arg,
            "structure": structure,
        }

    if not path.is_dir():
        raise RuntimeError(f"tool get_structure requires a file or directory: {path_arg}")

    all_structure: list[dict[str, Any]] = []
    for candidate in sorted(path.rglob("*.py")):
        if candidate.is_file():
            all_structure.extend(collect_python_structure(candidate))
    all_structure.sort(key=lambda item: (item["path"], item["start_line"], item["name"]))
    return {
        "tool_name": "get_structure",
        "ok": True,
        "summary": f"found {len(all_structure)} symbols across {path_arg}",
        "path": path_arg,
        "structure": all_structure,
    }
