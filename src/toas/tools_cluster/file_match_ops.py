from __future__ import annotations

import re
from difflib import SequenceMatcher, unified_diff
from typing import Any


def whitespace_lax_block_pattern(block: str) -> re.Pattern[str]:
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


def blankline_tolerant_pattern(block: str) -> re.Pattern[str]:
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


def replace_block_pattern(search_block: str, match_mode: str) -> re.Pattern[str]:
    if match_mode == "strict":
        return re.compile(re.escape(search_block), re.DOTALL)
    if match_mode == "default":
        return blankline_tolerant_pattern(search_block)
    if match_mode == "lax":
        return whitespace_lax_block_pattern(search_block)
    raise RuntimeError(
        "invalid arguments for tool replace_block: match_mode must be one of strict, default, lax"
    )


def best_equal_length_region(content: str, search_block: str) -> dict[str, Any] | None:
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


def replace_block_mismatch_diagnostics(content: str, search_block: str) -> str:
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

    candidate = best_equal_length_region(content, search_block)
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
