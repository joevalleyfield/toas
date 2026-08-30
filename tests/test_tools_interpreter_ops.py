from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from toas.tools_cluster.interpreter_ops import run_interpreter_script


def _workspace(tmp_path: Path):
    return lambda path: tmp_path / path if not Path(path).is_absolute() else Path(path)


def test_interpreter_script_runs_explicit_runtime_and_cleans_artifact(tmp_path: Path):
    result = run_interpreter_script(
        {"language": "bc", "script": 'print("Hi Mom!")', "runtime": [sys.executable]},
        workspace_path_fn=_workspace(tmp_path),
    )

    assert result["ok"] is True
    assert result["language"] == "bc"
    assert result["runtime"] == [sys.executable]
    assert list(tmp_path.glob("script*.bc")) == []


def test_interpreter_script_persists_and_overwrites_named_artifact(tmp_path: Path):
    target = tmp_path / "calc.bc"
    target.write_text("old", encoding="utf-8")

    result = run_interpreter_script(
        {
            "language": "bc",
            "script": "print('new')",
            "runtime": [sys.executable],
            "path": str(target),
            "persist": True,
            "overwrite": True,
        },
        workspace_path_fn=_workspace(tmp_path),
    )

    assert result["ok"] is True
    assert target.read_text(encoding="utf-8") == "print('new')"


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"language": "bc", "script": "x"},
        {"language": "bc", "script": "x", "runtime": []},
        {"language": "bc", "script": "x", "runtime": ["missing-runtime"]},
    ],
)
def test_interpreter_script_rejects_missing_or_invalid_runtime(tmp_path: Path, args):
    with pytest.raises(RuntimeError):
        run_interpreter_script(args, workspace_path_fn=_workspace(tmp_path))


def test_interpreter_script_preserves_nonzero_stderr(tmp_path: Path):
    result = run_interpreter_script(
        {
            "language": "bc",
            "script": "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)",
            "runtime": [sys.executable],
        },
        workspace_path_fn=_workspace(tmp_path),
    )

    assert result["ok"] is False
    assert result["exit_code"] == 3
    assert "out" in result["stdout"]
    assert "err" in result["stderr"]


def test_interpreter_script_rejects_cwd_and_artifact_paths(tmp_path: Path):
    with pytest.raises(RuntimeError, match="requires cwd to be a directory"):
        run_interpreter_script(
            {"language": "bc", "script": "x", "runtime": [sys.executable], "cwd": "missing"},
            workspace_path_fn=_workspace(tmp_path),
        )


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({"script": "x", "runtime": [sys.executable]}, "language must be a non-empty string"),
        ({"language": "bc", "runtime": [sys.executable]}, "script must be a non-empty string"),
        ({"language": "bc", "script": "x", "cwd": 1, "runtime": [sys.executable]}, "cwd must be a string"),
        ({"language": "bc", "script": "x", "timeout_s": 0, "runtime": [sys.executable]}, "timeout_s must be a positive int"),
        ({"language": "bc", "script": "x", "persist": 1, "runtime": [sys.executable]}, "persist must be a bool"),
        ({"language": "bc", "script": "x", "path": "", "runtime": [sys.executable]}, "path must be a non-empty string"),
        ({"language": "bc", "script": "x", "overwrite": 1, "runtime": [sys.executable]}, "overwrite must be a bool"),
    ],
)
def test_interpreter_script_rejects_invalid_arguments(tmp_path: Path, args, message):
    with pytest.raises(RuntimeError, match=re.escape(message)):
        run_interpreter_script(args, workspace_path_fn=_workspace(tmp_path))


def test_interpreter_script_rejects_workspace_and_cleanup_disappearance(tmp_path: Path, monkeypatch):
    with pytest.raises(RuntimeError, match="disallows cwd outside workspace"):
        run_interpreter_script(
            {"language": "bc", "script": "x", "runtime": [sys.executable]},
            workspace_path_fn=lambda _path: (_ for _ in ()).throw(RuntimeError("outside")),
        )
    with pytest.raises(RuntimeError, match="disallows path outside workspace"):
        def reject_artifact(path):
            if path == ".":
                return tmp_path
            raise RuntimeError("outside")

        run_interpreter_script(
            {"language": "bc", "script": "x", "runtime": [sys.executable], "path": "x.bc"},
            workspace_path_fn=reject_artifact,
        )

    def disappear(_path):
        raise FileNotFoundError

    monkeypatch.setattr(Path, "unlink", disappear)
    result = run_interpreter_script(
        {"language": "bc", "script": "print(1)", "runtime": [sys.executable]},
        workspace_path_fn=_workspace(tmp_path),
    )
    assert result["ok"] is True


def test_interpreter_script_rejects_overwrite_without_persistence(tmp_path: Path):
    with pytest.raises(RuntimeError, match="overwrite requires persist=true"):
        run_interpreter_script(
            {
                "language": "bc",
                "script": "x",
                "runtime": [sys.executable],
                "overwrite": True,
            },
            workspace_path_fn=_workspace(tmp_path),
        )
    with pytest.raises(RuntimeError, match="requires the parent of path to be a directory"):
        run_interpreter_script(
            {"language": "bc", "script": "x", "runtime": [sys.executable], "path": "missing/x.bc"},
            workspace_path_fn=_workspace(tmp_path),
        )
