from __future__ import annotations

import re
import time
from difflib import SequenceMatcher, unified_diff
from typing import Any

NEAR_MATCH_TIME_BUDGET_SECONDS = 0.2
MAX_HEURISTIC_LINE_OCCURRENCES = 16
MAX_SAMPLED_WINDOWS = 64


def _monotonic() -> float:
    return time.monotonic()


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


def _line_based_candidate_starts(content: str, search_block: str, target_len: int) -> list[int]:
    candidates: list[int] = []
    seen: set[int] = set()
    search_lines = [line for line in search_block.splitlines() if line.strip()]
    search_lines.sort(key=len, reverse=True)
    total_windows = max(1, len(content) - target_len + 1)

    def add(start: int) -> None:
        bounded = min(max(0, start), total_windows - 1)
        if bounded not in seen:
            seen.add(bounded)
            candidates.append(bounded)

    add(0)
    add(total_windows - 1)

    for line in search_lines[:3]:
        line_start = 0
        hits = 0
        while hits < MAX_HEURISTIC_LINE_OCCURRENCES:
            found = content.find(line, line_start)
            if found < 0:
                break
            add(found)
            add(found - min(32, target_len // 4))
            add(found - target_len // 2)
            line_start = found + max(1, len(line))
            hits += 1
        if candidates:
            break

    return candidates


def best_equal_length_region(
    content: str,
    search_block: str,
    *,
    deadline: float | None = None,
) -> dict[str, Any] | None:
    target_len = len(search_block)
    if target_len <= 0 or not content:
        return None
    if len(content) <= target_len:
        return {
            "start": 0,
            "end": len(content),
            "text": content,
            "similarity": SequenceMatcher(a=search_block, b=content, autojunk=False).ratio(),
            "exhausted_budget": False,
            "candidates_considered": 1,
        }

    total_windows = len(content) - target_len + 1
    best_start = 0
    best_ratio = -1.0
    candidates_considered = 0
    exhausted_budget = False

    candidate_starts = _line_based_candidate_starts(content, search_block, target_len)
    if total_windows > 1:
        stride = max(1, total_windows // MAX_SAMPLED_WINDOWS)
        for start in range(0, total_windows, stride):
            if len(candidate_starts) >= MAX_SAMPLED_WINDOWS + 8:
                break
            candidate_starts.append(start)

    seen_candidates: set[int] = set()
    for start in candidate_starts:
        if start in seen_candidates:
            continue
        seen_candidates.add(start)
        if deadline is not None and _monotonic() >= deadline:
            exhausted_budget = True
            break
        window = content[start : start + target_len]
        ratio = SequenceMatcher(a=search_block, b=window, autojunk=False).ratio()
        candidates_considered += 1
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = start

    return {
        "start": best_start,
        "end": best_start + target_len,
        "text": content[best_start : best_start + target_len],
        "similarity": best_ratio,
        "exhausted_budget": exhausted_budget,
        "candidates_considered": candidates_considered,
    }


def _leading_space_count(line: str) -> int:
    count = 0
    for ch in line:
        if ch != " ":
            break
        count += 1
    return count


def _full_block_indent_shift(search_block: str, content: str) -> int | None:
    search_lines = [line for line in search_block.splitlines() if line.strip()]
    if not search_lines:
        return None

    content_lines = content.splitlines()
    if len(search_lines) > len(content_lines):
        return None

    search_text = [line.lstrip(" ") for line in search_lines]
    search_indent = _leading_space_count(search_lines[0])

    for start in range(0, len(content_lines) - len(search_lines) + 1):
        candidate = content_lines[start : start + len(search_lines)]
        candidate_text = [line.lstrip(" ") for line in candidate]
        if candidate_text != search_text:
            continue
        candidate_indent = _leading_space_count(candidate[0])
        delta = candidate_indent - search_indent
        if delta <= 0:
            continue
        if all(_leading_space_count(line) - _leading_space_count(search_lines[idx]) == delta for idx, line in enumerate(candidate)):
            return delta
    return None


def replace_block_mismatch_diagnostics(content: str, search_block: str) -> str:
    lines: list[str] = []
    deadline = _monotonic() + NEAR_MATCH_TIME_BUDGET_SECONDS
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

    candidate = best_equal_length_region(content, search_block, deadline=deadline)
    if candidate is not None:
        window_start = 0 if candidate["start"] <= 0 else content.rfind("\n", 0, candidate["start"]) + 1
        window_end = len(content) if candidate["end"] >= len(content) else content.find("\n", candidate["end"]) + 1
        window_text = content[window_start:window_end]
        lines.append(
            "best equal-length region: "
            f"file[{window_start}:{window_end}] "
            f"similarity={candidate['similarity']:.3f} "
            f"candidates={candidate['candidates_considered']}"
        )
        overlap = SequenceMatcher(a=search_block, b=window_text, autojunk=False).find_longest_match(
            0,
            len(search_block),
            0,
            len(window_text),
        )
        if overlap.size <= 0:
            lines.append("closest overlap: none")
        else:
            search_end = overlap.a + overlap.size
            file_end = overlap.b + overlap.size
            lines.append(
                f"closest overlap: search[{overlap.a}:{search_end}] <-> "
                f"file[{window_start + overlap.b}:{window_start + file_end}] "
                f"(chars={overlap.size})"
            )
            expected_next = search_block[search_end : search_end + 80]
            actual_next = window_text[file_end : file_end + 80]
            if expected_next:
                lines.append(f"expected next: {expected_next!r}")
            if actual_next:
                lines.append(f"actual next:   {actual_next!r}")
            context_start = max(0, overlap.b - 40)
            context_end = min(len(window_text), file_end + 40)
            lines.append(f"file context near overlap: {window_text[context_start:context_end]!r}")

        if candidate["similarity"] >= 0.55:
            diff = "".join(
                unified_diff(
                    search_block.splitlines(keepends=True),
                    window_text.splitlines(keepends=True),
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
        hint = None if candidate["similarity"] < 0.55 else _full_block_indent_shift(search_block, content)
        if hint is not None:
            hint = f"possible full-block indent-only mismatch: try search_indent={hint}"
        if hint:
            lines.append(hint)
        if candidate["exhausted_budget"]:
            lines.append(
                f"near-match budget exhausted after {NEAR_MATCH_TIME_BUDGET_SECONDS:.1f}s; returning best-so-far"
            )
    else:
        lines.append("closest overlap: none")
    return "\n".join(lines)
