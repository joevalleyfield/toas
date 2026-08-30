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
    assert list(tmp_path.glob("script*.py")) == []


def test_run_python_script_uses_explicit_runtime(tmp_path: Path):
    result = run_python_script(
        {"script": "print(1)", "runtime": [sys.executable]},
        workspace_path_fn=lambda path: tmp_path / path,
    )

    assert result["ok"] is True
    assert result["argv"][0] == sys.executable


def test_run_python_script_records_runtime_resolution_source(tmp_path: Path):
    result = run_python_script(
        {"script": "print(1)", "runtime": [sys.executable]},
        workspace_path_fn=lambda path: tmp_path / path,
        runtime_source="configured",
    )

    assert result["runtime_source"] == "configured"


def test_run_python_script_reports_missing_explicit_runtime(tmp_path: Path):
    try:
        run_python_script(
            {"script": "print(1)", "runtime": ["definitely-not-a-python-runtime"]},
            workspace_path_fn=lambda path: tmp_path / path,
        )
    except RuntimeError as exc:
        assert str(exc) == "tool python_script runtime not found: definitely-not-a-python-runtime"
    else:
        raise AssertionError("expected missing runtime to fail")


def test_run_python_script_persists_generated_artifact(tmp_path: Path):
    result = run_python_script(
        {"script": "print(1)", "persist": True},
        workspace_path_fn=lambda path: tmp_path / path if not Path(path).is_absolute() else Path(path),
    )

    artifact = Path(result["script_path"])
    assert result["persist"] is True
    assert artifact.name.startswith("script")
    assert artifact.read_text(encoding="utf-8") == "print(1)"
    artifact.unlink()


def test_run_python_script_allows_explicit_overwrite_only_when_persisted(tmp_path: Path):
    target = tmp_path / "the_best_script_ever.py"
    target.write_text("print('old')", encoding="utf-8")

    result = run_python_script(
        {"script": "print('new')", "persist": True, "path": str(target), "overwrite": True},
        workspace_path_fn=lambda path: Path(path),
    )

    assert result["ok"] is True
    assert target.read_text(encoding="utf-8") == "print('new')"
    target.unlink()


def test_validate_python_script_rejects_overwrite_without_persistence(tmp_path: Path):
    try:
        validate_python_script_args(
            {"script": "print(1)", "overwrite": True},
            workspace_path_fn=lambda path: tmp_path / path,
        )
    except RuntimeError as exc:
        assert str(exc) == "invalid arguments for tool python_script: overwrite requires persist=true"
    else:
        raise AssertionError("expected overwrite without persistence to fail")


def test_validate_python_script_rejects_invalid_argument_shapes(tmp_path: Path):
    cases = [
        ({"script": 1}, "invalid arguments for tool python_script: script must be a non-empty string"),
        ({"script": "x", "cwd": 1}, "invalid arguments for tool python_script: cwd must be a string"),
        ({"script": "x", "timeout_s": 0}, "invalid arguments for tool python_script: timeout_s must be a positive int"),
        ({"script": "x", "runtime": []}, "invalid arguments for tool python_script: runtime must be a non-empty list[str]"),
        ({"script": "x", "persist": 1}, "invalid arguments for tool python_script: persist must be a bool"),
        ({"script": "x", "path": ""}, "invalid arguments for tool python_script: path must be a non-empty string"),
        ({"script": "x", "overwrite": 1}, "invalid arguments for tool python_script: overwrite must be a bool"),
    ]
    for args, message in cases:
        try:
            validate_python_script_args(args, workspace_path_fn=lambda path: tmp_path / path)
        except RuntimeError as exc:
            assert str(exc) == message
        else:
            raise AssertionError(f"expected {message}")


def test_validate_python_script_rejects_workspace_and_parent_paths(tmp_path: Path):
    def reject(_path):
        raise RuntimeError("outside")

    for args, message in [
        ({"script": "x", "cwd": "."}, "tool python_script disallows cwd outside workspace"),
        ({"script": "x", "path": "elsewhere/x.py"}, "tool python_script requires the parent of path to be a directory"),
    ]:
        try:
            validate_python_script_args(args, workspace_path_fn=reject if args.get("cwd") else lambda path: tmp_path / path)
        except RuntimeError as exc:
            assert str(exc) == message
        else:
            raise AssertionError(f"expected {message}")


def test_validate_python_script_rejects_artifact_outside_workspace(tmp_path: Path):
    def workspace_path(path):
        if path == ".":
            return tmp_path
        raise RuntimeError("outside")

    try:
        validate_python_script_args(
            {"script": "x", "path": "script.py"},
            workspace_path_fn=workspace_path,
        )
    except RuntimeError as exc:
        assert str(exc) == "tool python_script disallows path outside workspace"
    else:
        raise AssertionError("expected artifact path outside workspace to fail")


def test_run_python_script_ignores_missing_ephemeral_cleanup_file(tmp_path: Path, monkeypatch):
    original_unlink = Path.unlink

    def unlink_then_disappear(path):
        if path.name.startswith("script"):
            raise FileNotFoundError
        return original_unlink(path)

    monkeypatch.setattr(Path, "unlink", unlink_then_disappear)
    result = run_python_script({"script": "print(1)"}, workspace_path_fn=lambda path: tmp_path / path)

    assert result["ok"] is True


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
