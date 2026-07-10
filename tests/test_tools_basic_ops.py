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
    with pytest.raises(RuntimeError, match="path must be a non-empty string"):
        run_write_file({"path": "", "content": "x"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())

    result = run_write_file(
        {"path": "a/b.txt", "content": "hello\n"},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )
    assert result["ok"] is True
    out = run_read_file({"path": "a/b.txt"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    assert out["content"] == "hello\n"
    assert out["display_content"] == "hello\n"
    ranged = run_read_file(
        {"path": "a/b.txt", "start_line": 1, "end_line": 1},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )
    assert ranged["content"] == "hello\n"
    assert ranged["display_content"] == "hello\n"
    assert ranged["summary"] == "a/b.txt:1-1"

    echo = run_echo_block({"block": "x\n  y\n"})
    assert echo["line_count"] == 2
    assert echo["leading_spaces"] == [0, 2]

    with pytest.raises(RuntimeError, match="content must be a string"):
        run_write_file({"path": "x.txt", "content": 1}, workspace_path_fn=lambda p: (tmp_path / p).resolve())

    with pytest.raises(RuntimeError, match="block must be a string"):
        run_echo_block({"block": 1})


def test_run_write_file_auto_preserves_existing_crlf(tmp_path):
    path = tmp_path / "a" / "b.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("hello\r\n", encoding="utf-8", newline="")

    result = run_write_file(
        {"path": "a/b.txt", "content": "bye\n"},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )

    assert result["newline_style"] == "crlf"
    with path.open("r", encoding="utf-8", newline="") as handle:
        assert handle.read() == "bye\r\n"


def test_run_write_file_explicit_lf_overrides_existing_crlf(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("hello\r\n", encoding="utf-8", newline="")

    result = run_write_file(
        {"path": "x.txt", "content": "bye\n"},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
        newline_style_policy="lf",
    )

    assert result["newline_style"] == "lf"
    with path.open("r", encoding="utf-8", newline="") as handle:
        assert handle.read() == "bye\n"


def test_run_read_file_errors(tmp_path):
    with pytest.raises(RuntimeError, match="path must be a non-empty string"):
        run_read_file({"path": ""}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="number_lines must be a bool"):
        run_read_file({"path": "missing.txt", "number_lines": "yes"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="start_line must be a positive int"):
        run_read_file({"path": "missing.txt", "start_line": "bad"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="end_line must be a positive int"):
        run_read_file({"path": "missing.txt", "end_line": "bad"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="requires a file"):
        run_read_file({"path": "missing.txt"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="start_line must be a positive int"):
        run_read_file({"path": "missing.txt", "start_line": 0}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="end_line must be a positive int"):
        run_read_file({"path": "missing.txt", "end_line": 0}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="end_line must be >= start_line"):
        run_read_file({"path": "missing.txt", "start_line": 2, "end_line": 1}, workspace_path_fn=lambda p: (tmp_path / p).resolve())


def test_run_read_file_line_window(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    out = run_read_file(
        {"path": "x.txt", "start_line": 2, "end_line": 3},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )
    assert out["content"] == "beta\ngamma\n"
    assert out["summary"] == "x.txt:2-3"


def test_run_read_file_numbered_output_preserves_raw_content(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    out = run_read_file(
        {"path": "x.txt", "start_line": 2, "end_line": 3, "number_lines": True},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )

    assert out["content"] == "beta\ngamma\n"
    assert out["display_content"] == "   2: beta\n   3: gamma\n"
    assert out["number_lines"] is True

    with pytest.raises(RuntimeError, match="start_line 4 is beyond file length 3"):
        run_read_file({"path": "x.txt", "start_line": 4}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="end_line 4 is beyond file length 3"):
        run_read_file({"path": "x.txt", "end_line": 4}, workspace_path_fn=lambda p: (tmp_path / p).resolve())


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


def test_run_search_non_regex_subprocess_error(monkeypatch, tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("alpha\n", encoding="utf-8")

    class _Done:
        returncode = 2
        stderr = "ripgrep boom"
        stdout = ""

    monkeypatch.setattr("toas.tools_cluster.basic_ops.subprocess.run", lambda *a, **k: _Done())
    with pytest.raises(RuntimeError, match="tool search failed: ripgrep boom"):
        run_search({"query": "a", "path": str(path), "regex": False}, workspace_path_fn=lambda p: Path(p))


def test_run_search_fallback_when_rg_missing(monkeypatch, tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("alpha\nbeta\nalpha2\n", encoding="utf-8")
    monkeypatch.setattr(
        "toas.tools_cluster.basic_ops.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("rg missing")),
    )
    out = run_search({"query": "alpha", "path": str(path), "regex": False, "limit": 1}, workspace_path_fn=lambda p: Path(p))
    assert out["ok"] is True
    assert out["summary"] == "1 matches"
    assert len(out["matches"]) == 1


def test_fallback_search_handles_nonexistent_path_and_read_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "toas.tools_cluster.basic_ops.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("rg missing")),
    )
    missing = run_search({"query": "alpha", "path": str(tmp_path / "nope"), "regex": False}, workspace_path_fn=lambda p: Path(p))
    assert missing["matches"] == []

    bad = tmp_path / "bad.txt"
    bad.write_text("alpha\n", encoding="utf-8")
    original_read_text = Path.read_text
    monkeypatch.setattr(
        "pathlib.Path.read_text",
        lambda self, **kwargs: (_ for _ in ()).throw(OSError("denied")) if self == bad else original_read_text(self, **kwargs),
    )
    out = run_search({"query": "alpha", "path": str(tmp_path), "regex": False}, workspace_path_fn=lambda p: Path(p))
    assert out["matches"] == []


def test_run_search_fallback_regex_compile_error_hint_when_rg_missing(monkeypatch, tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("alpha\n", encoding="utf-8")
    monkeypatch.setattr(
        "toas.tools_cluster.basic_ops.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("rg missing")),
    )
    with pytest.raises(RuntimeError, match="query was treated as regex"):
        run_search({"query": "[", "path": str(path), "regex": True}, workspace_path_fn=lambda p: Path(p))


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
    with pytest.raises(RuntimeError, match="path must be a non-empty string"):
        run_get_structure({"path": ""}, workspace_path_fn=lambda p: Path(p))
