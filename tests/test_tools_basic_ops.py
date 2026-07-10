from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster.basic_ops import (
    _existing_file_overwrite_is_safe,
    _git_head_captures_current_file_text,
    _jj_captures_current_file_text,
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


def test_run_write_file_append_existing_file(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("hello\n", encoding="utf-8")

    result = run_write_file(
        {"path": "a.txt", "content": "world\n", "append": True},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )

    assert result["mode"] == "append"
    assert path.read_text(encoding="utf-8") == "hello\nworld\n"


def test_run_write_file_append_creates_missing_file(tmp_path):
    result = run_write_file(
        {"path": "a.txt", "content": "hello\n", "append": True},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )

    assert result["mode"] == "append"
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello\n"


def test_run_write_file_force_overwrites_uncaptured_existing_file(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("hello\n", encoding="utf-8")

    result = run_write_file(
        {"path": "a.txt", "content": "bye\n", "force": True},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )

    assert result["mode"] == "force_overwrite"
    assert path.read_text(encoding="utf-8") == "bye\n"


def test_run_write_file_refuses_uncaptured_existing_file_without_force(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("hello\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="refused to overwrite existing file not captured in repository history"):
        run_write_file(
            {"path": "a.txt", "content": "bye\n"},
            workspace_path_fn=lambda p: (tmp_path / p).resolve(),
        )


def test_run_write_file_accepts_safe_overwrite_when_jj_captures_current_content(tmp_path, monkeypatch):
    path = tmp_path / "a.txt"
    path.write_text("hello\n", encoding="utf-8")

    class _Completed:
        returncode = 0
        stdout = b"hello\n"

    monkeypatch.setattr("toas.tools_cluster.basic_ops.subprocess.run", lambda *args, **kwargs: _Completed())

    result = run_write_file(
        {"path": "a.txt", "content": "bye\n"},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
        workspace_root=tmp_path,
    )

    assert result["mode"] == "safe_overwrite"
    assert path.read_text(encoding="utf-8") == "bye\n"


def test_run_write_file_accepts_safe_overwrite_when_git_head_captures_current_content(tmp_path, monkeypatch):
    path = tmp_path / "a.txt"
    path.write_text("hello\n", encoding="utf-8")

    def fake_run(argv, **_kwargs):
        class _Completed:
            def __init__(self, returncode, stdout):
                self.returncode = returncode
                self.stdout = stdout

        if argv[:3] == ["jj", "file", "show"]:
            return _Completed(1, b"")
        if argv[:2] == ["git", "show"]:
            return _Completed(0, b"hello\n")
        raise AssertionError(argv)

    monkeypatch.setattr("toas.tools_cluster.basic_ops.subprocess.run", fake_run)

    result = run_write_file(
        {"path": "a.txt", "content": "bye\n"},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
        workspace_root=tmp_path,
    )

    assert result["mode"] == "safe_overwrite"
    assert path.read_text(encoding="utf-8") == "bye\n"


def test_overwrite_history_checks_fail_closed_for_out_of_root_or_missing_tools(tmp_path, monkeypatch):
    path = tmp_path / "a.txt"
    path.write_text("hello\n", encoding="utf-8")
    outside_root = tmp_path / "workspace"
    outside_root.mkdir()

    assert _jj_captures_current_file_text(path=path, workspace_root=outside_root) is False
    assert _git_head_captures_current_file_text(path=path, workspace_root=outside_root) is False

    monkeypatch.setattr("toas.tools_cluster.basic_ops.subprocess.run", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    assert _existing_file_overwrite_is_safe(path=path, workspace_root=tmp_path) is False


def test_run_write_file_rejects_directory_target(tmp_path):
    (tmp_path / "dir").mkdir()

    with pytest.raises(RuntimeError, match="requires a file path"):
        run_write_file(
            {"path": "dir", "content": "x"},
            workspace_path_fn=lambda p: (tmp_path / p).resolve(),
        )


def test_run_write_file_rejects_invalid_force_append_args(tmp_path):
    with pytest.raises(RuntimeError, match="force must be a bool"):
        run_write_file({"path": "a.txt", "content": "x", "force": "yes"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="append must be a bool"):
        run_write_file({"path": "a.txt", "content": "x", "append": "yes"}, workspace_path_fn=lambda p: (tmp_path / p).resolve())
    with pytest.raises(RuntimeError, match="force and append cannot both be true"):
        run_write_file(
            {"path": "a.txt", "content": "x", "force": True, "append": True},
            workspace_path_fn=lambda p: (tmp_path / p).resolve(),
        )


def test_run_write_file_auto_preserves_existing_crlf(tmp_path):
    path = tmp_path / "a" / "b.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("hello\r\n", encoding="utf-8", newline="")

    result = run_write_file(
        {"path": "a/b.txt", "content": "bye\n", "force": True},
        workspace_path_fn=lambda p: (tmp_path / p).resolve(),
    )

    assert result["newline_style"] == "crlf"
    with path.open("r", encoding="utf-8", newline="") as handle:
        assert handle.read() == "bye\r\n"


def test_run_write_file_explicit_lf_overrides_existing_crlf(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("hello\r\n", encoding="utf-8", newline="")

    result = run_write_file(
        {"path": "x.txt", "content": "bye\n", "force": True},
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
