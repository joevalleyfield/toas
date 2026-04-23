import pytest

from toas.tools_cluster.file_match_ops import (
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
