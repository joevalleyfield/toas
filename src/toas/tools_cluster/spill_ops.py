from __future__ import annotations

from dataclasses import dataclass

DEFAULT_ERROR_ANCHORS: tuple[str, ...] = (
    "Traceback (most recent call last):",
    "panic:",
    "fatal:",
    "FAILED",
    "FAIL:",
    "AssertionError",
    "ERROR",
)


@dataclass(frozen=True)
class LineMeta:
    text: str
    orig_start: int
    orig_end: int


@dataclass(frozen=True)
class PreviewExtractionResult:
    lines: list[str]
    range_summary: str
    omitted_lines: int


def elide_duplicate_lines(items: list[LineMeta], min_repeat: int = 3) -> list[LineMeta]:
    """Collapse consecutive duplicate or near-identical lines."""
    if not items:
        return []

    result: list[LineMeta] = []
    current_text = items[0].text
    current_start = items[0].orig_start
    current_end = items[0].orig_end
    count = 1

    for item in items[1:]:
        if item.text.strip() == current_text.strip():
            count += 1
            current_end = item.orig_end
        else:
            if count >= min_repeat:
                rep_marker = f"{current_text} [repeated {count} times]" if current_text else f"[repeated {count} times]"
                result.append(
                    LineMeta(
                        text=rep_marker,
                        orig_start=current_start,
                        orig_end=current_end,
                    )
                )
            else:
                for k in range(count):
                    line_no = current_start + k
                    result.append(LineMeta(text=current_text, orig_start=line_no, orig_end=line_no))
            current_text = item.text
            current_start = item.orig_start
            current_end = item.orig_end
            count = 1

    if count >= min_repeat:
        rep_marker = f"{current_text} [repeated {count} times]" if current_text else f"[repeated {count} times]"
        result.append(
            LineMeta(
                text=rep_marker,
                orig_start=current_start,
                orig_end=current_end,
            )
        )
    else:
        for k in range(count):
            line_no = current_start + k
            result.append(LineMeta(text=current_text, orig_start=line_no, orig_end=line_no))

    return result


def find_error_anchor_index(items: list[LineMeta], anchors: tuple[str, ...] = DEFAULT_ERROR_ANCHORS) -> int | None:
    """Find the index of the first matching diagnostic anchor in priority order."""
    for anchor in anchors:
        for idx, item in enumerate(items):
            if anchor in item.text:
                return idx
    return None


def _omission_divider(count: int, path: str) -> str:
    return f"--- [{count} lines omitted; full output in {path}] ---"


def _extract_head(items: list[LineMeta], total_lines: int, preview_lines: int, scratch_path: str) -> PreviewExtractionResult:
    slice_items = items[:preview_lines]
    if not slice_items:
        return PreviewExtractionResult(lines=[], range_summary="lines=0..0 of 0", omitted_lines=total_lines)
    last_end = slice_items[-1].orig_end
    omitted = max(0, total_lines - last_end)
    out_lines = [item.text for item in slice_items]
    return PreviewExtractionResult(
        lines=out_lines,
        range_summary=f"lines=1..{last_end} of {total_lines}",
        omitted_lines=omitted,
    )


def _extract_tail(items: list[LineMeta], total_lines: int, preview_lines: int, scratch_path: str) -> PreviewExtractionResult:
    slice_items = items[-preview_lines:]
    if not slice_items:
        return PreviewExtractionResult(lines=[], range_summary="lines=0..0 of 0", omitted_lines=total_lines)
    first_start = slice_items[0].orig_start
    omitted = max(0, first_start - 1)
    out_lines: list[str] = []
    if omitted > 0:
        out_lines.append(_omission_divider(omitted, scratch_path))
    out_lines.extend(item.text for item in slice_items)
    return PreviewExtractionResult(
        lines=out_lines,
        range_summary=f"lines={first_start}..{total_lines} of {total_lines}",
        omitted_lines=omitted,
    )


def _extract_head_tail(
    items: list[LineMeta],
    total_lines: int,
    preview_lines: int,
    head_lines: int,
    tail_lines: int,
    scratch_path: str,
) -> PreviewExtractionResult:
    effective_head = min(head_lines, preview_lines)
    effective_tail = min(tail_lines, max(0, preview_lines - effective_head))

    if effective_tail == 0:
        return _extract_head(items, total_lines, preview_lines, scratch_path)

    head_items = items[:effective_head]
    tail_items = items[-effective_tail:]
    head_end = head_items[-1].orig_end
    tail_start = tail_items[0].orig_start
    omitted = max(0, tail_start - head_end - 1)

    out_lines = [item.text for item in head_items]
    if omitted > 0:
        out_lines.append(_omission_divider(omitted, scratch_path))
    out_lines.extend(item.text for item in tail_items)

    range_summary = (
        f"lines=1..{head_end},{tail_start}..{total_lines} of {total_lines}"
        if omitted > 0
        else f"lines=1..{total_lines} of {total_lines}"
    )
    return PreviewExtractionResult(
        lines=out_lines,
        range_summary=range_summary,
        omitted_lines=omitted,
    )


def _extract_error_focus(
    items: list[LineMeta],
    total_lines: int,
    preview_lines: int,
    head_lines: int,
    tail_lines: int,
    scratch_path: str,
    anchors: tuple[str, ...] = DEFAULT_ERROR_ANCHORS,
) -> PreviewExtractionResult:
    anchor_idx = find_error_anchor_index(items, anchors)
    if anchor_idx is None:
        return _extract_head_tail(items, total_lines, preview_lines, head_lines, tail_lines, scratch_path)

    lead_lines = 5
    start_idx = max(0, anchor_idx - lead_lines)
    end_idx = min(len(items), start_idx + preview_lines)
    if (end_idx - start_idx) < preview_lines and start_idx > 0:
        start_idx = max(0, end_idx - preview_lines)

    slice_items = items[start_idx:end_idx]
    slice_start = slice_items[0].orig_start
    slice_end = slice_items[-1].orig_end

    out_lines: list[str] = []
    omitted_before = max(0, slice_start - 1)
    if omitted_before > 0:
        out_lines.append(_omission_divider(omitted_before, scratch_path))
    out_lines.extend(item.text for item in slice_items)
    omitted_after = max(0, total_lines - slice_end)
    if omitted_after > 0:
        out_lines.append(_omission_divider(omitted_after, scratch_path))

    return PreviewExtractionResult(
        lines=out_lines,
        range_summary=f"lines={slice_start}..{slice_end} of {total_lines}",
        omitted_lines=omitted_before + omitted_after,
    )


def _extract_head_shuf_tail(
    items: list[LineMeta],
    total_lines: int,
    preview_lines: int,
    scratch_path: str,
) -> PreviewExtractionResult:
    n_items = len(items)
    head_budget = min(5, preview_lines // 3)
    tail_budget = min(5, preview_lines // 3)
    mid_budget = max(0, preview_lines - head_budget - tail_budget)

    chosen_indices: set[int] = set(range(min(head_budget, n_items)))
    chosen_indices.update(range(max(0, n_items - tail_budget), n_items))

    mid_start = head_budget
    mid_end = max(mid_start, n_items - tail_budget)
    mid_total = mid_end - mid_start

    if mid_total > 0 and mid_budget > 0:
        step = mid_total / mid_budget
        for step_i in range(mid_budget):
            chosen_indices.add(mid_start + int(step_i * step))

    sorted_indices = sorted(chosen_indices)
    if not sorted_indices:
        return _extract_head(items, total_lines, preview_lines, scratch_path)

    # Group into contiguous segments
    segments: list[list[LineMeta]] = []
    current_segment: list[LineMeta] = [items[sorted_indices[0]]]
    prev_idx = sorted_indices[0]

    for idx in sorted_indices[1:]:
        if idx == prev_idx + 1:
            current_segment.append(items[idx])
        else:
            segments.append(current_segment)
            current_segment = [items[idx]]
        prev_idx = idx
    segments.append(current_segment)

    out_lines: list[str] = []
    range_parts: list[str] = []
    total_omitted = 0

    first_start = segments[0][0].orig_start
    if first_start > 1:
        omitted = first_start - 1
        out_lines.append(_omission_divider(omitted, scratch_path))
        total_omitted += omitted

    for i, seg in enumerate(segments):
        seg_start = seg[0].orig_start
        seg_end = seg[-1].orig_end
        range_parts.append(f"{seg_start}..{seg_end}" if seg_start != seg_end else str(seg_start))
        out_lines.extend(item.text for item in seg)

        if i < len(segments) - 1:
            next_start = segments[i + 1][0].orig_start
            gap = next_start - seg_end - 1
            if gap > 0:
                out_lines.append(_omission_divider(gap, scratch_path))
                total_omitted += gap

    last_end = segments[-1][-1].orig_end
    if last_end < total_lines:
        omitted = total_lines - last_end
        out_lines.append(_omission_divider(omitted, scratch_path))
        total_omitted += omitted

    range_summary = f"lines={','.join(range_parts)} of {total_lines}"
    return PreviewExtractionResult(
        lines=out_lines,
        range_summary=range_summary,
        omitted_lines=total_omitted,
    )


def extract_spill_preview(
    raw_lines: list[str],
    *,
    mode: str = "head_tail",
    preview_lines: int = 30,
    head_lines: int = 10,
    tail_lines: int = 20,
    elide_duplicates: bool = True,
    min_repeat: int = 3,
    scratch_rel_path: str = ".toas/scratch/preview.txt",
) -> PreviewExtractionResult:
    """Extract an in-transcript preview according to the requested strategy."""
    total_lines = len(raw_lines)
    if total_lines == 0:
        return PreviewExtractionResult(lines=[], range_summary="lines=0..0 of 0", omitted_lines=0)

    items = [LineMeta(text=line, orig_start=i + 1, orig_end=i + 1) for i, line in enumerate(raw_lines)]

    if elide_duplicates:
        items = elide_duplicate_lines(items, min_repeat=min_repeat)

    if len(items) <= preview_lines:
        out_lines = [item.text for item in items]
        omitted = max(0, total_lines - len(raw_lines))
        return PreviewExtractionResult(
            lines=out_lines,
            range_summary=f"lines=1..{total_lines} of {total_lines}",
            omitted_lines=omitted,
        )

    mode_normalized = mode.lower().strip()
    if mode_normalized == "head":
        return _extract_head(items, total_lines, preview_lines, scratch_rel_path)
    if mode_normalized == "tail":
        return _extract_tail(items, total_lines, preview_lines, scratch_rel_path)
    if mode_normalized == "error_focus":
        return _extract_error_focus(items, total_lines, preview_lines, head_lines, tail_lines, scratch_rel_path)
    if mode_normalized == "head_shuf_tail":
        return _extract_head_shuf_tail(items, total_lines, preview_lines, scratch_rel_path)

    # Default to head_tail
    return _extract_head_tail(items, total_lines, preview_lines, head_lines, tail_lines, scratch_rel_path)
