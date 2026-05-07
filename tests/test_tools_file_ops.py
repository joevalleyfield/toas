from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster.file_ops import run_replace_block, run_replace_range


def test_run_replace_range_replaces_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = Path("test.txt")
    test_file.write_text("a\nb\nc\n", encoding="utf-8")

    result = run_replace_range(
        {
            "path": "test.txt",
            "start_line": 2,
            "end_line": 2,
            "replacement_block": "B\n",
        }
    )

    assert result["ok"] is True
    assert test_file.read_text(encoding="utf-8") == "a\nB\nc\n"


def test_run_replace_block_reports_mismatch_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = Path("test.txt")
    test_file.write_text("one\ntwo\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="found no matches") as exc:
        run_replace_block(
            {
                "path": "test.txt",
                "search_block": "three\n",
                "replacement_block": "THREE\n",
            }
        )

    assert "search chars=" in str(exc.value)


def test_run_replace_range_context_mismatch_and_indent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = Path("test.txt")
    test_file.write_text("aa\nbb\ncc\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="context_start mismatch"):
        run_replace_range(
            {
                "path": "test.txt",
                "start_line": 2,
                "end_line": 2,
                "replacement_block": "x\n",
                "context_start": "WRONG",
            }
        )

    with pytest.raises(RuntimeError, match="context_end mismatch"):
        run_replace_range(
            {
                "path": "test.txt",
                "start_line": 2,
                "end_line": 2,
                "replacement_block": "x\n",
                "context_end": "WRONG",
            }
        )

    out = run_replace_range(
        {
            "path": "test.txt",
            "start_line": 2,
            "end_line": 2,
            "replacement_block": "y\nz\n",
            "indent": 2,
        }
    )
    assert out["ok"] is True
    assert test_file.read_text(encoding="utf-8") == "aa\n  y\n  z\ncc\n"


def test_run_replace_block_expected_count_and_indents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = Path("test.txt")
    test_file.write_text("k\nk\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="matched 2 blocks; expected 1"):
        run_replace_block(
            {
                "path": "test.txt",
                "search_block": "k\n",
                "replacement_block": "x\n",
                "expected_count": 1,
            }
        )

    with pytest.raises(RuntimeError, match="search_indent must be a non-negative int"):
        run_replace_block(
            {
                "path": "test.txt",
                "search_block": "k\n",
                "replacement_block": "x\n",
                "search_indent": -1,
            }
        )

    out = run_replace_block(
        {
            "path": "test.txt",
            "search_block": "k\nk\n",
            "replacement_block": "x",
            "ensure_trailing_newline": False,
            "search_indent": "",
            "replacement_indent": "",
        }
    )
    assert out["ok"] is True
    assert test_file.read_text(encoding="utf-8") == "x"
