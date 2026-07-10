from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any

from .file_write_edges import write_text_with_tool_newline_policy


def run_write_file(args: dict, *, workspace_path_fn, newline_style_policy: str = "auto") -> dict:
    path_arg = args["path"]
    content = args["content"]

    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool write_file: path must be a non-empty string")
    if not isinstance(content, str):
        raise RuntimeError("invalid arguments for tool write_file: content must be a string")

    path = workspace_path_fn(path_arg)
    path.parent.mkdir(parents=True, exist_ok=True)
    newline = write_text_with_tool_newline_policy(
        path=path,
        text=content,
        newline_style_policy=newline_style_policy,
    )
    return {
        "tool_name": "write_file",
        "ok": True,
        "summary": f"wrote {len(content.encode('utf-8'))} bytes",
        "path": path_arg,
        "bytes_written": len(content.encode("utf-8")),
        "newline_style": "crlf" if newline == "\r\n" else "lf",
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

    number_lines = args.get("number_lines", False)
    if not isinstance(number_lines, bool):
        raise RuntimeError("invalid arguments for tool read_file: number_lines must be a bool")

    start_line = args.get("start_line")
    end_line = args.get("end_line")
    if start_line is not None and not isinstance(start_line, int):
        raise RuntimeError("invalid arguments for tool read_file: start_line must be a positive int")
    if end_line is not None and not isinstance(end_line, int):
        raise RuntimeError("invalid arguments for tool read_file: end_line must be a positive int")
    if start_line is not None and start_line < 1:
        raise RuntimeError("invalid arguments for tool read_file: start_line must be a positive int")
    if end_line is not None and end_line < 1:
        raise RuntimeError("invalid arguments for tool read_file: end_line must be a positive int")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise RuntimeError("invalid arguments for tool read_file: end_line must be >= start_line")

    path = workspace_path_fn(path_arg)
    if not path.is_file():
        raise RuntimeError(f"tool read_file requires a file: {path_arg}")

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if start_line is None and end_line is None:
        content = "".join(lines)
        summary = path_arg
    else:
        effective_start = 1 if start_line is None else start_line
        effective_end = len(lines) if end_line is None else end_line
        if effective_start > len(lines):
            raise RuntimeError(f"start_line {effective_start} is beyond file length {len(lines)}")
        if effective_end > len(lines):
            raise RuntimeError(f"end_line {effective_end} is beyond file length {len(lines)}")
        content = "".join(lines[effective_start - 1 : effective_end])
        summary = f"{path_arg}:{effective_start}-{effective_end}"

    display_content = content
    if number_lines:
        display_start = 1 if start_line is None else start_line
        display_content = "".join(
            f"{line_no:>4}: {line}"
            for line_no, line in enumerate(content.splitlines(keepends=True), start=display_start)
        )

    return {
        "tool_name": "read_file",
        "ok": True,
        "summary": summary,
        "path": path_arg,
        "content": content,
        "display_content": display_content,
        "number_lines": number_lines,
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
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError:
        matches = _fallback_search_matches(path=path, query=query, regex=regex, limit=limit)
        output = "\n".join(matches)
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


def _fallback_search_matches(*, path: Path, query: str, regex: bool, limit: int) -> list[str]:
    pattern: re.Pattern[str] | None = None
    if regex:
        try:
            pattern = re.compile(query)
        except re.error as exc:
            raise RuntimeError(
                f"tool search failed: {exc}\n"
                "hint: query was treated as regex; set regex=false for literal matching"
            ) from exc

    candidates: list[Path]
    if path.is_file():
        candidates = [path]
    elif path.is_dir():
        candidates = [candidate for candidate in path.rglob("*") if candidate.is_file()]
    else:
        return []

    results: list[str] = []
    for candidate in sorted(candidates):
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            matched = bool(pattern.search(line)) if pattern is not None else query in line
            if matched:
                results.append(f"{candidate}:{line_no}:{line}")
                if len(results) >= limit:
                    return results
    return results


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
