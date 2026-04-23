from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster.apply_patch_ops import parse_apply_patch_hunks, run_apply_patch


def test_parse_apply_patch_hunks_requires_envelope():
    with pytest.raises(RuntimeError, match="must start with"):
        parse_apply_patch_hunks("nope")


def test_run_apply_patch_update_hunk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = Path("a.txt")
    target.write_text("old\n", encoding="utf-8")
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: a.txt",
            "@@",
            "-old",
            "+new",
            "*** End Patch",
        ]
    )
    out = run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())
    assert out["ok"] is True
    assert target.read_text(encoding="utf-8") == "new\n"


def test_run_apply_patch_context_free_insert_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("a.txt").write_text("x\n", encoding="utf-8")
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: a.txt",
            "@@",
            "+new",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="unsupported context-free insertion"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())
