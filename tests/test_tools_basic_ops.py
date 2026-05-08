from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster.basic_ops import (
    collect_python_structure,
    run_echo_block,
    run_get_structure,
    run_read_file,
    run_search,
    run_write_file,
)


def test_run_write_read_and_echo_block(tmp_path):
    result = run_write_file(
        {"path": "a/b.txt", "content": "hello\n"},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )
    assert result["ok"] is True
    out = run_read_file({"path": "a/b.txt"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    assert out["content"] == "hello\n"

    echo = run_echo_block({"block": "x\n  y\n"})
    assert echo["line_count"] == 2
    assert echo["leading_spaces"] == [0, 2]

    with pytest.raises(RuntimeError, match="content must be a string"):
        run_write_file({"path": "x.txt", "content": 1}, workspace_path_fn=lambda p: (tmp_path / p).resolve())

    with pytest.raises(RuntimeError, match="block must be a string"):
        run_echo_block({"block": 1})


def test_run_read_file_errors(tmp_path):
    with pytest.raises(RuntimeError, match="path must be a non-empty string"):
        run_read_file({"path": ""}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="requires a file"):
        run_read_file({"path": "missing.txt"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())


def test_run_search_validates_and_runs(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("alpha\nbeta\n", encoding="utf-8")
    out = run_search(
        {"query": "alpha", "path": str(path), "regex": False, "limit": 10},
        workspace_path_fn=lambda p: Path(p),
    )
    assert out["ok"] is True
    assert out["matches"]

    with pytest.raises(RuntimeError, match="query must be a non-empty string"):
        run_search({"query": "", "path": str(path)}, workspace_path_fn=lambda p: Path(p))
    with pytest.raises(RuntimeError, match="limit must be an int between 1 and 200"):
        run_search({"query": "a", "path": str(path), "limit": 0}, workspace_path_fn=lambda p: Path(p))
    with pytest.raises(RuntimeError, match="path must be a string"):
        run_search({"query": "a", "path": 1}, workspace_path_fn=lambda p: Path(p))
    with pytest.raises(RuntimeError, match="regex must be a bool"):
        run_search({"query": "a", "path": str(path), "regex": "no"}, workspace_path_fn=lambda p: Path(p))


def test_run_search_regex_error_hint(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("alpha\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="query was treated as regex"):
        run_search(
            {"query": "[", "path": str(path), "regex": True},
            workspace_path_fn=lambda p: Path(p),
        )


def test_collect_and_run_get_structure(tmp_path):
    py = tmp_path / "m.py"
    py.write_text("""\nclass C:\n    pass\n\ndef f():\n    return 1\n""", encoding="utf-8")
    entries = collect_python_structure(py)
    assert {item["name"] for item in entries} >= {"C", "f"}

    single = run_get_structure({"path": str(py)}, workspace_path_fn=lambda p: Path(p))
    assert single["ok"] is True
    folder = run_get_structure({"path": str(tmp_path)}, workspace_path_fn=lambda p: Path(p))
    assert folder["ok"] is True

    txt = tmp_path / "a.txt"
    txt.write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError, match="only supports .py files"):
        run_get_structure({"path": str(txt)}, workspace_path_fn=lambda p: Path(p))
    with pytest.raises(RuntimeError, match="requires a file or directory"):
        run_get_structure({"path": str(tmp_path / 'missing')}, workspace_path_fn=lambda p: Path(p))
