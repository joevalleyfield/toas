from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from toas.tools_cluster.powershell_ops import run_powershell_script, validate_powershell_script_args


def _workspace(tmp_path: Path):
    return lambda path: tmp_path / path if not Path(path).is_absolute() else Path(path)


def test_powershell_script_executes_and_cleans_ephemeral_artifact(tmp_path: Path):
    result = run_powershell_script(
        {"script": 'print("Hi Mom!")', "runtime": [sys.executable]},
        workspace_path_fn=_workspace(tmp_path),
    )

    assert result["tool_name"] == "powershell_script"
    assert result["ok"] is True
    assert "Hi Mom!" in result["stdout"]
    assert list(tmp_path.glob("script*.ps1")) == []


def test_powershell_script_records_runtime_source_and_persists_artifact(tmp_path: Path):
    result = run_powershell_script(
        {"script": "print(1)", "runtime": [sys.executable], "persist": True},
        workspace_path_fn=_workspace(tmp_path),
        runtime_source="configured",
    )

    artifact = Path(result["script_path"])
    assert result["runtime_source"] == "configured"
    assert result["persist"] is True
    assert artifact.suffix == ".ps1"
    artifact.unlink()


def test_powershell_script_reports_missing_runtime(tmp_path: Path):
    with pytest.raises(RuntimeError, match="tool powershell_script runtime not found: missing-pwsh"):
        run_powershell_script(
            {"script": "print(1)", "runtime": ["missing-pwsh"]},
            workspace_path_fn=_workspace(tmp_path),
        )


def test_powershell_script_overwrites_persisted_target(tmp_path: Path):
    target = tmp_path / "script.ps1"
    target.write_text("old", encoding="utf-8")

    result = run_powershell_script(
        {
            "script": "print('new')",
            "runtime": [sys.executable],
            "persist": True,
            "path": str(target),
            "overwrite": True,
        },
        workspace_path_fn=_workspace(tmp_path),
    )

    assert result["ok"] is True
    assert target.read_text(encoding="utf-8") == "print('new')"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({"script": 1}, "script must be a non-empty string"),
        ({"script": "x", "cwd": 1}, "cwd must be a string"),
        ({"script": "x", "timeout_s": 0}, "timeout_s must be a positive int"),
        ({"script": "x", "runtime": []}, "runtime must be a non-empty list[str]"),
        ({"script": "x", "persist": 1}, "persist must be a bool"),
        ({"script": "x", "path": ""}, "path must be a non-empty string"),
        ({"script": "x", "overwrite": 1}, "overwrite must be a bool"),
    ],
)
def test_validate_powershell_script_rejects_invalid_arguments(tmp_path: Path, args, message):
    with pytest.raises(RuntimeError, match=re.escape(message)):
        validate_powershell_script_args(args, workspace_path_fn=_workspace(tmp_path))


def test_validate_powershell_script_rejects_workspace_and_artifact_errors(tmp_path: Path):
    with pytest.raises(RuntimeError, match="disallows cwd outside workspace"):
        validate_powershell_script_args(
            {"script": "x", "cwd": "."}, workspace_path_fn=lambda _path: (_ for _ in ()).throw(RuntimeError("outside"))
        )
    with pytest.raises(RuntimeError, match="requires the parent of path to be a directory"):
        validate_powershell_script_args(
            {"script": "x", "path": "missing/script.ps1"}, workspace_path_fn=_workspace(tmp_path)
        )
    with pytest.raises(RuntimeError, match="disallows path outside workspace"):
        def reject_artifact(path):
            if path == ".":
                return tmp_path
            raise RuntimeError("outside")

        validate_powershell_script_args(
            {"script": "x", "path": "script.ps1"},
            workspace_path_fn=reject_artifact,
        )
    with pytest.raises(RuntimeError, match="overwrite requires persist=true"):
        validate_powershell_script_args(
            {"script": "x", "overwrite": True}, workspace_path_fn=_workspace(tmp_path)
        )


def test_validate_powershell_script_requires_existing_cwd(tmp_path: Path):
    with pytest.raises(RuntimeError, match="requires cwd to be a directory"):
        validate_powershell_script_args(
            {"script": "x", "cwd": "missing"}, workspace_path_fn=_workspace(tmp_path)
        )


def test_run_powershell_script_ignores_missing_ephemeral_cleanup_file(tmp_path: Path, monkeypatch):
    def disappear(_path):
        raise FileNotFoundError

    monkeypatch.setattr(Path, "unlink", disappear)
    result = run_powershell_script(
        {"script": "print(1)", "runtime": [sys.executable]},
        workspace_path_fn=_workspace(tmp_path),
    )

    assert result["ok"] is True
