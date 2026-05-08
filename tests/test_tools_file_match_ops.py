import pytest

from toas.tools_cluster.file_match_ops import (
    best_equal_length_region,
    replace_block_mismatch_diagnostics,
    replace_block_pattern,
)


def test_replace_block_pattern_modes():
    assert replace_block_pattern("a\n\nb\n", "strict").search("a\n\nb\n")
    assert replace_block_pattern("a\n\nb\n", "default").search("a\n\nb\n")
    assert replace_block_pattern("a b", "lax").search("a    b")
    with pytest.raises(RuntimeError, match="match_mode must be one of strict, default, lax"):
        replace_block_pattern("x", "weird")


def test_replace_block_mismatch_diagnostics_contains_overlap_hints():
    out = replace_block_mismatch_diagnostics("foo\nbar\n", "foo\nbaz\n")
    assert "search chars=" in out
    assert "closest overlap:" in out


def test_replace_block_mismatch_diagnostics_newline_mismatch_and_none_overlap():
    out = replace_block_mismatch_diagnostics("foo\r\nbar\r\n", "zzz\n")
    assert "newline style mismatch" in out

    out2 = replace_block_mismatch_diagnostics("", "abc")
    assert "closest overlap: none" in out2


def test_best_equal_length_region_edge_cases():
    assert best_equal_length_region("", "abc") is None
    assert best_equal_length_region("abc", "") is None
    out = best_equal_length_region("abc", "abcdef")
    assert out == {"start": 0, "end": 3, "text": "abc"}


def test_best_equal_length_region_end_window_beats_sampled_windows():
    search = "Z" * 20
    content = ("A" * 4000) + search
    out = best_equal_length_region(content, search)
    assert out is not None
    assert out["start"] == len(content) - len(search)
