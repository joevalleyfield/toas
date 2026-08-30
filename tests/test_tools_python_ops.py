from __future__ import annotations

import sys
from pathlib import Path

from toas.tools_cluster.python_ops import run_python_script, validate_python_script_args


def test_run_python_script_executes_from_temporary_file_and_cleans_up(tmp_path: Path):
    result = run_python_script(
        {"script": 'print("Hi Mom!")', "cwd": ".", "timeout_s": 5},
        workspace_path_fn=lambda path: tmp_path / path,
    )

    assert result["tool_name"] == "python_script"
    assert result["ok"] is True
    assert "Hi Mom!" in result["stdout"]
    assert list(tmp_path.glob("toas-script-*.py")) == []


def test_run_python_script_uses_explicit_runtime(tmp_path: Path):
    result = run_python_script(
        {"script": "print(1)", "runtime": [sys.executable]},
        workspace_path_fn=lambda path: tmp_path / path,
    )

    assert result["ok"] is True
    assert result["argv"][0] == sys.executable


def test_validate_python_script_requires_existing_directory(tmp_path: Path):
    try:
        validate_python_script_args(
            {"script": "print(1)", "cwd": "missing"},
            workspace_path_fn=lambda path: tmp_path / path,
        )
    except RuntimeError as exc:
        assert str(exc) == "tool python_script requires cwd to be a directory"
    else:
        raise AssertionError("expected missing cwd to fail")
