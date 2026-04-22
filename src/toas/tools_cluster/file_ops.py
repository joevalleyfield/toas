from __future__ import annotations

import importlib
import re
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any


def _normalize_indent(
    value: Any,
    *,
    tool_name: str,
    arg_name: str,
    default: str = "",
) -> str:
    if value is None:
        return default
    if isinstance(value, int):
        if value < 0:
            raise RuntimeError(
                f"invalid arguments for tool {tool_name}: {arg_name} must be a non-negative int or a string"
            )
        return " " * value
    if isinstance(value, str):
        return value
    raise RuntimeError(
        f"invalid arguments for tool {tool_name}: {arg_name} must be an int or a string"
    )


def _apply_indent(text: str, indent: str) -> str:
    if not text:
        return text
    if not indent:
        return text
    lines = text.splitlines(keepends=True)
    return "".join(indent + line if line.strip() else line for line in lines)


def _whitespace_lax_block_pattern(block: str) -> re.Pattern[str]:
    parts: list[str] = []
    in_whitespace = False
    for ch in block:
        if ch.isspace():
            if not in_whitespace:
                parts.append(r"\s+")
                in_whitespace = True
            continue
        parts.append(re.escape(ch))
        in_whitespace = False
    return re.compile("".join(parts), re.DOTALL)


def _blankline_tolerant_pattern(block: str) -> re.Pattern[str]:
    parts: list[str] = []
    for line in block.splitlines(keepends=True):
        line_wo_nl = line.rstrip("\r\n")
        has_nl = line.endswith("\n") or line.endswith("\r")
        if not line_wo_nl.strip():
            parts.append(r"[ \t]*")
            if has_nl:
                parts.append(r"(?:\r?\n)")
            continue
        parts.append(re.escape(line_wo_nl))
        if has_nl:
            parts.append(re.escape("\n"))
    return re.compile("".join(parts), re.DOTALL)


def _replace_block_pattern(search_block: str, match_mode: str) -> re.Pattern[str]:
    if match_mode == "strict":
        return re.compile(re.escape(search_block), re.DOTALL)
    if match_mode == "default":
        return _blankline_tolerant_pattern(search_block)
    if match_mode == "lax":
        return _whitespace_lax_block_pattern(search_block)
    raise RuntimeError(
        "invalid arguments for tool replace_block: match_mode must be one of strict, default, lax"
    )


def _best_equal_length_region(content: str, search_block: str) -> dict[str, Any] | None:
    target_len = len(search_block)
    if target_len <= 0 or not content:
        return None
    if len(content) <= target_len:
        return {"start": 0, "end": len(content), "text": content}

    total_windows = len(content) - target_len + 1
    max_windows = 3000
    stride = 1 if total_windows <= max_windows else max(1, total_windows // max_windows)

    best_start = 0
    best_ratio = -1.0
    for start in range(0, total_windows, stride):
        window = content[start : start + target_len]
        ratio = SequenceMatcher(a=search_block, b=window, autojunk=False).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = start

    end_start = total_windows - 1
    if end_start != best_start:
        end_window = content[end_start : end_start + target_len]
        end_ratio = SequenceMatcher(a=search_block, b=end_window, autojunk=False).ratio()
        if end_ratio > best_ratio:
            best_start = end_start

    return {
        "start": best_start,
        "end": best_start + target_len,
        "text": content[best_start : best_start + target_len],
    }


def _replace_block_mismatch_diagnostics(content: str, search_block: str) -> str:
    lines: list[str] = []
    lines.append(f"search chars={len(search_block)}, file chars={len(content)}")

    file_has_crlf = "\r\n" in content
    search_has_crlf = "\r\n" in search_block
    if file_has_crlf != search_has_crlf:
        lines.append(
            f"newline style mismatch: search uses {'CRLF' if search_has_crlf else 'LF'}, "
            f"file uses {'CRLF' if file_has_crlf else 'LF'}"
        )

    first_line = search_block.splitlines()[0] if search_block.splitlines() else search_block
    if first_line:
        occurrences = content.count(first_line)
        lines.append(f"first search line occurrences in file: {occurrences}")

    matcher = SequenceMatcher(a=search_block, b=content, autojunk=False)
    longest = matcher.find_longest_match(0, len(search_block), 0, len(content))
    if longest.size <= 0:
        lines.append("closest overlap: none")
        return "\n".join(lines)

    search_end = longest.a + longest.size
    file_end = longest.b + longest.size
    lines.append(
        f"closest overlap: search[{longest.a}:{search_end}] <-> file[{longest.b}:{file_end}] "
        f"(chars={longest.size})"
    )

    expected_next = search_block[search_end : search_end + 80]
    actual_next = content[file_end : file_end + 80]
    if expected_next:
        lines.append(f"expected next: {expected_next!r}")
    if actual_next:
        lines.append(f"actual next:   {actual_next!r}")

    context_start = max(0, longest.b - 40)
    context_end = min(len(content), file_end + 40)
    lines.append(f"file context near overlap: {content[context_start:context_end]!r}")

    candidate = _best_equal_length_region(content, search_block)
    if candidate is not None:
        ratio = SequenceMatcher(a=search_block, b=candidate["text"], autojunk=False).ratio()
        lines.append(
            "best equal-length region: "
            f"file[{candidate['start']}:{candidate['end']}] "
            f"similarity={ratio:.3f}"
        )
        if ratio >= 0.55:
            diff = "".join(
                unified_diff(
                    search_block.splitlines(keepends=True),
                    candidate["text"].splitlines(keepends=True),
                    fromfile="search_block",
                    tofile="file_window",
                    n=2,
                )
            ).strip()
            if diff:
                lines.append("best-window diff:")
                lines.append(diff)
        else:
            lines.append("best-window diff omitted: similarity below threshold 0.55")
    return "\n".join(lines)


def run_replace_range(args: dict) -> dict:
    tools_mod = importlib.import_module("toas.tools")
    path_arg = args["path"]
    start_line = args["start_line"]
    end_line = args["end_line"]
    replacement_block = args["replacement_block"]
    indent = _normalize_indent(
        args.get("indent", ""),
        tool_name="replace_range",
        arg_name="indent",
        default="",
    )
    context_start = args.get("context_start")
    context_end = args.get("context_end")

    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool replace_range: path must be a non-empty string")
    if not isinstance(start_line, int) or start_line < 1:
        raise RuntimeError("invalid arguments for tool replace_range: start_line must be a positive int")
    if not isinstance(end_line, int) or end_line < start_line:
        raise RuntimeError("invalid arguments for tool replace_range: end_line must be >= start_line")
    if not isinstance(replacement_block, str):
        raise RuntimeError("invalid arguments for tool replace_range: replacement_block must be a string")
    if context_start is not None and not isinstance(context_start, str):
        raise RuntimeError("invalid arguments for tool replace_range: context_start must be a string")
    if context_end is not None and not isinstance(context_end, str):
        raise RuntimeError("invalid arguments for tool replace_range: context_end must be a string")

    path = tools_mod._workspace_path(path_arg)
    if not path.is_file():
        raise RuntimeError(f"tool replace_range requires a file: {path_arg}")

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if start_line > len(lines):
        raise RuntimeError(f"start_line {start_line} is beyond file length {len(lines)}")
    if end_line > len(lines):
        raise RuntimeError(f"end_line {end_line} is beyond file length {len(lines)}")

    def _render_numbered(start: int, end: int) -> str:
        start_i = max(1, start)
        end_i = min(len(lines), end)
        out: list[str] = []
        width = len(str(end_i))
        for idx in range(start_i, end_i + 1):
            text = lines[idx - 1].rstrip("\n")
            out.append(f"{str(idx).rjust(width)}: {text}")
        return "\n".join(out)

    if isinstance(context_start, str):
        actual_start = lines[start_line - 1].rstrip("\n")
        if actual_start != context_start:
            excerpt = _render_numbered(start_line, min(end_line, start_line + 2))
            raise RuntimeError(
                "tool replace_range context_start mismatch\n"
                f"expected start line {start_line}: {context_start!r}\n"
                f"actual   start line {start_line}: {actual_start!r}\n"
                "file excerpt:\n"
                f"{excerpt}"
            )
    if isinstance(context_end, str):
        actual_end = lines[end_line - 1].rstrip("\n")
        if actual_end != context_end:
            excerpt = _render_numbered(max(start_line, end_line - 2), end_line)
            raise RuntimeError(
                "tool replace_range context_end mismatch\n"
                f"expected end line {end_line}: {context_end!r}\n"
                f"actual   end line {end_line}: {actual_end!r}\n"
                "file excerpt:\n"
                f"{excerpt}"
            )

    idx_start = start_line - 1
    idx_end_exclusive = end_line
    effective_replacement = _apply_indent(replacement_block, indent)
    replacement_lines = effective_replacement.splitlines(keepends=True)
    updated_lines = lines[:idx_start] + replacement_lines + lines[idx_end_exclusive:]
    path.write_text("".join(updated_lines), encoding="utf-8")
    return {
        "tool_name": "replace_range",
        "ok": True,
        "summary": f"replaced lines {start_line}-{end_line}",
        "path": path_arg,
        "lines_replaced": end_line - start_line + 1,
    }


def run_replace_block(args: dict) -> dict:
    tools_mod = importlib.import_module("toas.tools")
    path_arg = args["path"]
    search_block = args["search_block"]
    replacement_block = args["replacement_block"]

    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool replace_block: path must be a non-empty string")
    if not isinstance(search_block, str) or not search_block:
        raise RuntimeError("invalid arguments for tool replace_block: search_block must be a non-empty string")
    if not isinstance(replacement_block, str):
        raise RuntimeError("invalid arguments for tool replace_block: replacement_block must be a string")

    expected_count = args.get("expected_count", 1)
    if not isinstance(expected_count, int) or expected_count <= 0:
        raise RuntimeError("invalid arguments for tool replace_block: expected_count must be a positive int")
    match_mode = args.get("match_mode", "default")
    if not isinstance(match_mode, str):
        raise RuntimeError(
            "invalid arguments for tool replace_block: match_mode must be one of strict, default, lax"
        )
    search_indent = _normalize_indent(
        args.get("search_indent"),
        tool_name="replace_block",
        arg_name="search_indent",
        default="",
    )
    replacement_indent = _normalize_indent(
        args.get("replacement_indent"),
        tool_name="replace_block",
        arg_name="replacement_indent",
        default=search_indent,
    )
    ensure_trailing_newline = args.get("ensure_trailing_newline", True)
    if not isinstance(ensure_trailing_newline, bool):
        raise RuntimeError(
            "invalid arguments for tool replace_block: ensure_trailing_newline must be boolean"
        )

    path = tools_mod._workspace_path(path_arg)
    if not path.is_file():
        raise RuntimeError(f"tool replace_block requires a file: {path_arg}")

    effective_search = _apply_indent(search_block, search_indent)
    effective_replacement = _apply_indent(replacement_block, replacement_indent)
    if ensure_trailing_newline and effective_replacement and not effective_replacement.endswith("\n"):
        effective_replacement = effective_replacement + "\n"
    content = path.read_text(encoding="utf-8")
    pattern = _replace_block_pattern(effective_search, match_mode)
    matches = list(pattern.finditer(content))
    count = len(matches)
    if count == 0:
        hint_lines = []
        if search_indent:
            hint_lines.append(f"effective search_indent={search_indent!r}")
        if replacement_indent:
            hint_lines.append(f"effective replacement_indent={replacement_indent!r}")
        hint = "\n".join(hint_lines)
        raise RuntimeError(
            "tool replace_block found no matches\n"
            f"{_replace_block_mismatch_diagnostics(content, effective_search)}"
            + (f"\n{hint}" if hint else "")
        )
    if count != expected_count:
        raise RuntimeError(
            f"tool replace_block matched {count} blocks; expected {expected_count}"
        )

    updated = pattern.sub(lambda _m: effective_replacement, content)
    path.write_text(updated, encoding="utf-8")

    changed_line_start = None
    changed_line_end = None
    preview = None
    replacement_pos = updated.find(effective_replacement)
    if replacement_pos >= 0:
        changed_line_start = updated.count("\n", 0, replacement_pos) + 1
        replacement_lines = max(1, len(effective_replacement.splitlines()))
        changed_line_end = changed_line_start + replacement_lines - 1
        all_lines = updated.splitlines()
        ctx_start = max(1, changed_line_start - 2)
        ctx_end = min(len(all_lines), changed_line_end + 2)
        width = len(str(ctx_end))
        excerpt = [
            f"{str(idx).rjust(width)}: {all_lines[idx - 1]}"
            for idx in range(ctx_start, ctx_end + 1)
        ]
        preview = "\n".join(excerpt)

    return {
        "tool_name": "replace_block",
        "ok": True,
        "summary": f"replaced {count} block",
        "path": path_arg,
        "replacements": count,
        "content": updated,
        "changed_line_start": changed_line_start,
        "changed_line_end": changed_line_end,
        "preview": preview,
    }
