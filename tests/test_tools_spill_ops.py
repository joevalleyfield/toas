from __future__ import annotations

import pytest

from toas.tools_cluster.spill_ops import (
    DEFAULT_ERROR_ANCHORS,
    LineMeta,
    _extract_head_shuf_tail,
    _extract_head_tail,
    elide_duplicate_lines,
    extract_spill_preview,
    find_error_anchor_index,
    parse_spill_spec,
)


def test_elide_duplicate_lines_empty():
    assert elide_duplicate_lines([]) == []


def test_elide_duplicate_lines_under_min_repeat():
    items = [
        LineMeta("hello", 1, 1),
        LineMeta("hello", 2, 2),
        LineMeta("world", 3, 3),
    ]
    res = elide_duplicate_lines(items, min_repeat=3)
    assert len(res) == 3
    assert res[0].text == "hello"
    assert res[1].text == "hello"
    assert res[2].text == "world"


def test_elide_duplicate_lines_at_or_above_min_repeat():
    items = [
        LineMeta("waiting...", 1, 1),
        LineMeta("waiting...", 2, 2),
        LineMeta("waiting...", 3, 3),
        LineMeta("done", 4, 4),
    ]
    res = elide_duplicate_lines(items, min_repeat=3)
    assert len(res) == 2
    assert res[0].text == "waiting... [repeated 3 times]"
    assert res[0].orig_start == 1
    assert res[0].orig_end == 3
    assert res[1].text == "done"


def test_elide_duplicate_lines_50_consecutive():
    items = [LineMeta("polling loop", i, i) for i in range(1, 51)]
    items.append(LineMeta("completed", 51, 51))
    res = elide_duplicate_lines(items, min_repeat=3)
    assert len(res) == 2
    assert res[0].text == "polling loop [repeated 50 times]"
    assert res[0].orig_start == 1
    assert res[0].orig_end == 50
    assert res[1].text == "completed"


def test_elide_duplicate_lines_trailing_repetition():
    items = [
        LineMeta("start", 1, 1),
        LineMeta("tick", 2, 2),
        LineMeta("tick", 3, 3),
        LineMeta("tick", 4, 4),
    ]
    res = elide_duplicate_lines(items, min_repeat=3)
    assert len(res) == 2
    assert res[0].text == "start"
    assert res[1].text == "tick [repeated 3 times]"
    assert res[1].orig_start == 2
    assert res[1].orig_end == 4


def test_elide_duplicate_lines_blank_lines():
    items = [LineMeta("", i, i) for i in range(1, 6)]
    res = elide_duplicate_lines(items, min_repeat=3)
    assert len(res) == 1
    assert res[0].text == "[repeated 5 times]"
    assert res[0].orig_start == 1
    assert res[0].orig_end == 5


def test_extract_spill_preview_empty():
    res = extract_spill_preview([], mode="head_tail")
    assert res.lines == []
    assert res.range_summary == "lines=0..0 of 0"
    assert res.omitted_lines == 0


def test_extract_spill_preview_within_budget():
    raw = [f"line {i}" for i in range(1, 11)]
    res = extract_spill_preview(raw, preview_lines=30)
    assert len(res.lines) == 10
    assert res.range_summary == "lines=1..10 of 10"
    assert res.omitted_lines == 0


def test_extract_spill_preview_head_mode():
    raw = [f"line_{i}" for i in range(1, 101)]
    res = extract_spill_preview(raw, mode="head", preview_lines=30)
    assert len(res.lines) == 30
    assert res.lines[0] == "line_1"
    assert res.lines[-1] == "line_30"
    assert res.range_summary == "lines=1..30 of 100"
    assert res.omitted_lines == 70


def test_extract_spill_preview_tail_mode():
    raw = [f"line_{i}" for i in range(1, 101)]
    res = extract_spill_preview(raw, mode="tail", preview_lines=30, scratch_rel_path=".toas/scratch/tail.txt")
    assert len(res.lines) == 31  # 1 omission divider + 30 tail lines
    assert res.lines[0] == "--- [70 lines omitted; full output in .toas/scratch/tail.txt] ---"
    assert res.lines[1] == "line_71"
    assert res.lines[-1] == "line_100"
    assert res.range_summary == "lines=71..100 of 100"
    assert res.omitted_lines == 70


def test_extract_spill_preview_head_tail_acceptance_criterion_1():
    # AC 1: In head_tail mode, an output of 200 lines displays lines 1-10,
    # an explicit omission divider, and lines 181-200.
    raw = [f"line_{i}" for i in range(1, 201)]
    res = extract_spill_preview(
        raw,
        mode="head_tail",
        preview_lines=30,
        head_lines=10,
        tail_lines=20,
        scratch_rel_path=".toas/scratch/ac1.txt",
    )
    assert len(res.lines) == 31  # 10 head + 1 divider + 20 tail
    assert res.lines[0] == "line_1"
    assert res.lines[9] == "line_10"
    assert res.lines[10] == "--- [170 lines omitted; full output in .toas/scratch/ac1.txt] ---"
    assert res.lines[11] == "line_181"
    assert res.lines[-1] == "line_200"
    assert res.range_summary == "lines=1..10,181..200 of 200"
    assert res.omitted_lines == 170


def test_extract_spill_preview_head_tail_no_tail_budget_falls_back_to_head():
    raw = [f"line_{i}" for i in range(1, 50)]
    res = _extract_head_tail(
        [LineMeta(line, i + 1, i + 1) for i, line in enumerate(raw)],
        total_lines=len(raw),
        preview_lines=10,
        head_lines=10,
        tail_lines=0,
        scratch_path="scratch.txt",
    )
    assert res.range_summary == "lines=1..10 of 49"


def test_extract_spill_preview_head_tail_small_omitted_boundary():
    raw = [f"line_{i}" for i in range(1, 35)]
    res = extract_spill_preview(
        raw,
        mode="head_tail",
        preview_lines=30,
        head_lines=10,
        tail_lines=20,
        scratch_rel_path="scratch.txt",
    )
    assert res.lines[0] == "line_1"
    assert res.lines[9] == "line_10"
    assert res.lines[10] == "--- [4 lines omitted; full output in scratch.txt] ---"
    assert res.lines[11] == "line_15"
    assert res.lines[-1] == "line_34"
    assert res.range_summary == "lines=1..10,15..34 of 34"
    assert res.omitted_lines == 4


def test_extract_spill_preview_error_focus_with_traceback():
    raw = [f"startup_line_{i}" for i in range(1, 101)]
    raw.extend([
        "Traceback (most recent call last):",
        '  File "test.py", line 42, in test_case',
        "    assert x == y",
        "AssertionError: mismatch",
    ])
    raw.extend([f"trailing_line_{i}" for i in range(1, 51)])

    res = extract_spill_preview(
        raw,
        mode="error_focus",
        preview_lines=30,
        scratch_rel_path=".toas/scratch/err.txt",
    )
    # The traceback begins at 0-based index 100 (line 101).
    # 5 lead lines -> starts at index 95 (line 96).
    # 30 preview lines -> lines 96..125.
    assert "Traceback (most recent call last):" in res.lines
    assert "AssertionError: mismatch" in res.lines
    assert any("lines omitted" in line for line in res.lines)
    assert res.range_summary.startswith("lines=96..125 of")


def test_extract_spill_preview_error_focus_fallback_when_no_anchor():
    raw = [f"regular_line_{i}" for i in range(1, 201)]
    res = extract_spill_preview(
        raw,
        mode="error_focus",
        preview_lines=30,
        head_lines=10,
        tail_lines=20,
        scratch_rel_path="scratch.txt",
    )
    # Falls back to head_tail
    assert res.range_summary == "lines=1..10,181..200 of 200"


def test_extract_spill_preview_error_focus_near_start():
    raw = ["FAILED test_one"] + [f"line_{i}" for i in range(1, 100)]
    res = extract_spill_preview(raw, mode="error_focus", preview_lines=20, scratch_rel_path="scratch.txt")
    assert res.lines[0] == "FAILED test_one"
    assert res.range_summary == "lines=1..20 of 100"
    assert res.omitted_lines == 80


def test_extract_spill_preview_head_shuf_tail():
    raw = [f"data_row_{i}" for i in range(1, 101)]
    res = extract_spill_preview(
        raw,
        mode="head_shuf_tail",
        preview_lines=20,
        scratch_rel_path=".toas/scratch/shuf.txt",
    )
    assert res.lines[0] == "data_row_1"
    assert res.lines[-1] == "data_row_100"
    assert "lines=" in res.range_summary
    assert "of 100" in res.range_summary
    assert res.omitted_lines > 0


def test_extract_spill_preview_error_focus_at_very_end():
    raw = [f"line_{i}" for i in range(1, 100)]
    raw.append("panic: runtime error")
    res = extract_spill_preview(raw, mode="error_focus", preview_lines=30, scratch_rel_path="err.txt")
    assert res.lines[-1] == "panic: runtime error"
    assert res.range_summary == "lines=71..100 of 100"
    assert res.omitted_lines == 70


def test_extract_head_shuf_tail_empty_indices():
    res = _extract_head_shuf_tail([], total_lines=0, preview_lines=0, scratch_path="test.txt")
    assert res.range_summary == "lines=0..0 of 0"


def test_extract_tail_empty_slice():
    from toas.tools_cluster.spill_ops import _extract_tail
    res = _extract_tail([], total_lines=0, preview_lines=0, scratch_path="test.txt")
    assert res.range_summary == "lines=0..0 of 0"


def test_extract_head_shuf_tail_leading_and_trailing_gaps():
    items = [LineMeta("row", i, i) for i in range(10, 30)]
    # total lines is 50, so orig_start 10 > 1 and orig_end 29 < 50
    res = _extract_head_shuf_tail(items, total_lines=50, preview_lines=10, scratch_path="test.txt")
    assert "lines=" in res.range_summary
    assert res.omitted_lines > 0


def test_find_error_anchor_index_priority():
    items = [
        LineMeta("normal output", 1, 1),
        LineMeta("ERROR: general failure", 2, 2),
        LineMeta("Traceback (most recent call last):", 3, 3),
    ]
    # Priority prefers Traceback over generic ERROR
    idx = find_error_anchor_index(items, DEFAULT_ERROR_ANCHORS)
    assert idx == 2


def test_parse_spill_spec_valid():
    # Defaults
    assert parse_spill_spec() == (None, None)

    # Explicit
    assert parse_spill_spec(threshold_lines=50, spill_mode="head") == (50, "head")

    # Dense formats
    assert parse_spill_spec(">100") == (100, None)
    assert parse_spill_spec("tail@200") == (200, "tail")
    assert parse_spill_spec("150") == (150, None)
    assert parse_spill_spec("error_focus") == (None, "error_focus")

    # Explicit takes precedence over dense string
    assert parse_spill_spec(">100", threshold_lines=50) == (50, None)
    assert parse_spill_spec("tail@200", threshold_lines=80, spill_mode="head") == (80, "head")
    assert parse_spill_spec("300", threshold_lines=120) == (120, None)
    assert parse_spill_spec("tail", spill_mode="error_focus") == (None, "error_focus")


def test_parse_spill_spec_invalid():
    with pytest.raises(RuntimeError, match="threshold_lines must be a positive int"):
        parse_spill_spec(threshold_lines=True)
    with pytest.raises(RuntimeError, match="threshold_lines must be a positive int"):
        parse_spill_spec(threshold_lines=0)
    with pytest.raises(RuntimeError, match="threshold_lines must be a positive int"):
        parse_spill_spec(threshold_lines=-5)
    with pytest.raises(RuntimeError, match="threshold_lines must be a positive int"):
        parse_spill_spec(threshold_lines="100")

    with pytest.raises(RuntimeError, match="spill_mode must be a non-empty string"):
        parse_spill_spec(spill_mode="")
    with pytest.raises(RuntimeError, match="spill_mode must be a non-empty string"):
        parse_spill_spec(spill_mode=123)
    with pytest.raises(RuntimeError, match="spill_mode must be a non-empty string"):
        parse_spill_spec(spill_mode="   ")

    with pytest.raises(RuntimeError, match="spill must be a non-empty string"):
        parse_spill_spec(123)
    with pytest.raises(RuntimeError, match="spill must be a non-empty string"):
        parse_spill_spec("")
    with pytest.raises(RuntimeError, match="spill must be a non-empty string"):
        parse_spill_spec("   ")

    # Invalid dense formats
    with pytest.raises(RuntimeError, match="spill threshold must be a positive int"):
        parse_spill_spec(">abc")
    with pytest.raises(RuntimeError, match="spill threshold must be a positive int"):
        parse_spill_spec(">0")
    with pytest.raises(RuntimeError, match="spill mode must be non-empty"):
        parse_spill_spec("@100")
    with pytest.raises(RuntimeError, match="spill threshold must be a positive int"):
        parse_spill_spec("tail@abc")
    with pytest.raises(RuntimeError, match="spill threshold must be a positive int"):
        parse_spill_spec("tail@0")
    with pytest.raises(RuntimeError, match="spill threshold must be a positive int"):
        parse_spill_spec("0")


def test_truncate_line():
    from toas.tools_cluster.spill_ops import truncate_line

    # Unchanged if within max_width or disabled
    assert truncate_line("hello world", 20) == "hello world"
    assert truncate_line("hello world", 11) == "hello world"
    assert truncate_line("hello world", 0) == "hello world"
    assert truncate_line("hello world", -5) == "hello world"

    # Truncated with exact character marker
    long_line = "a" * 100
    res = truncate_line(long_line, 50)
    assert len(res) == 50
    assert res.endswith(" chars truncated]")
    assert "... [" in res
    # Extract number of truncated chars from marker
    import re

    m = re.search(r"\.\.\. \[(\d+) chars truncated\]", res)
    assert m is not None
    omitted = int(m.group(1))
    prefix = res[: m.start()]
    assert len(prefix) + omitted == 100

    # Very small widths
    assert truncate_line("abcdefghijklmnop", 10) == "abcdefg..."
    assert truncate_line("abcdefghijklmnop", 2) == "ab"


def test_extract_spill_preview_truncates_long_lines():
    from toas.tools_cluster.spill_ops import extract_spill_preview

    raw = [f"short_{i}" for i in range(1, 10)]
    raw.append("x" * 1000)
    res = extract_spill_preview(raw, preview_lines=30, max_line_width=100)
    assert len(res.lines) == 10
    assert res.lines[0] == "short_1"
    last_line = res.lines[-1]
    assert len(last_line) == 100
    assert "... [" in last_line
    assert last_line.endswith(" chars truncated]")


def test_extract_spill_preview_max_preview_bytes_backstop():
    from toas.tools_cluster.spill_ops import extract_spill_preview

    # 20 lines of 100 chars = 2000 chars. Cap preview at 500 bytes.
    raw = [("line_" + str(i).zfill(2) + "_" + "y" * 90) for i in range(1, 21)]
    res = extract_spill_preview(
        raw,
        mode="head",
        preview_lines=20,
        max_line_width=400,
        max_preview_bytes=500,
        scratch_rel_path=".toas/scratch/capped.txt",
    )
    # Total preview bytes must be <= 500
    total_bytes = sum(len(l.encode("utf-8")) + 1 for l in res.lines)
    assert total_bytes <= 500
    assert any("--- [preview capped at 500 bytes; full output in .toas/scratch/capped.txt] ---" in l for l in res.lines)
    assert res.omitted_lines > 0


def test_extract_spill_preview_max_preview_bytes_single_line_cap():
    from toas.tools_cluster.spill_ops import extract_spill_preview

    # 1 line of 5000 chars with max_preview_bytes=200
    raw = ["z" * 5000]
    res = extract_spill_preview(
        raw,
        max_line_width=400,
        max_preview_bytes=200,
        scratch_rel_path=".toas/scratch/single.txt",
    )
    total_bytes = sum(len(l.encode("utf-8")) + 1 for l in res.lines)
    assert total_bytes <= 200
    assert len(res.lines) == 2
    assert "--- [preview capped at 200 bytes" in res.lines[-1]


def test_extract_spill_preview_empty_and_zero_byte_cap():
    from toas.tools_cluster.spill_ops import extract_spill_preview

    empty_res = extract_spill_preview([], scratch_rel_path=".toas/scratch/empty.txt")
    assert empty_res.lines == []

    zero_cap_res = extract_spill_preview(
        ["line 1", "line 2"],
        max_preview_bytes=0,
        scratch_rel_path=".toas/scratch/zero.txt",
    )
    assert zero_cap_res.lines == ["line 1", "line 2"]



