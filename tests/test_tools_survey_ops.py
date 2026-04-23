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
