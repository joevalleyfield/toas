from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster.survey_ops import run_code_survey


def test_run_code_survey_reports_top_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = Path("src")
    src.mkdir()
    (src / "m.py").write_text(
        "class A:\n"
        "    def f(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    out = run_code_survey({"path": "src", "top_n": 5}, workspace_path_fn=lambda p: Path(p).resolve())
    assert out["ok"] is True
    assert out["files_top"]
    assert out["functions_top"]
    assert out["classes_top"]


def test_run_code_survey_invalid_top_n():
    with pytest.raises(RuntimeError, match="top_n must be an int"):
        run_code_survey({"path": "src", "top_n": 0}, workspace_path_fn=lambda p: Path.cwd() / p)


def test_run_code_survey_validates_path_and_missing_target():
    with pytest.raises(RuntimeError, match="path must be a non-empty string"):
        run_code_survey({"path": ""}, workspace_path_fn=lambda p: Path.cwd() / p)
    with pytest.raises(RuntimeError, match="requires a file or directory"):
        run_code_survey({"path": "missing.py", "top_n": 5}, workspace_path_fn=lambda p: Path.cwd() / p)


def test_run_code_survey_file_mode_and_skips_syntax_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = Path("src")
    src.mkdir()
    (src / "good.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (src / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    (src / "note.txt").write_text("x", encoding="utf-8")

    py_only = run_code_survey({"path": "src/note.txt", "top_n": 3}, workspace_path_fn=lambda p: Path(p).resolve())
    assert py_only["files_top"] == []

    out = run_code_survey({"path": "src", "top_n": 3}, workspace_path_fn=lambda p: Path(p).resolve())
    assert any(item["path"].endswith("bad.py") for item in out["skipped"])
