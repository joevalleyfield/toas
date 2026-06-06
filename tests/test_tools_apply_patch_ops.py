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


def test_run_apply_patch_validation_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # empty patch
    with pytest.raises(RuntimeError, match="patch must be a non-empty string"):
        run_apply_patch({"patch": ""}, workspace_path_fn=lambda p: Path(p).resolve())

    with pytest.raises(RuntimeError, match="patch must be a non-empty string"):
        run_apply_patch({"patch": 123}, workspace_path_fn=lambda p: Path(p).resolve())

    # missing file path
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: ",
            "@@",
            "-old",
            "+new",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="missing file path"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())

    # file does not exist (update)
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: missing.txt",
            "@@",
            "-old",
            "+new",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="update failed: file does not exist"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())

    # file already exists (add)
    Path("existing.txt").write_text("x\n", encoding="utf-8")
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Add File: existing.txt",
            "+new",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="add failed: file already exists"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())

    # file does not exist (delete)
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Delete File: missing.txt",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="delete failed: file does not exist"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())

    # path is a directory (delete)
    (tmp_path / "a_dir").mkdir(exist_ok=True)
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Delete File: a_dir",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="delete failed: path is a directory"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())

    # target exists (move)
    Path("src.txt").write_text("x\n", encoding="utf-8")
    Path("dst.txt").write_text("y\n", encoding="utf-8")
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: src.txt",
            "*** Move to: dst.txt",
            "@@",
            "-x",
            "+x",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="move failed: target exists"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())

    # invalid hunk header
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Unknown: x.txt",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="invalid apply_patch hunk header"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())


def test_run_apply_patch_invalid_hunk_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("a.txt").write_text("old\n", encoding="utf-8")
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: a.txt",
            "@@",
            "Xinvalid line",
            "*** End Patch",
        ]
    )
    with pytest.raises(RuntimeError, match="expected context/add/remove lines"):
        run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())


def test_run_apply_patch_noop_and_helpers(tmp_path, monkeypatch):
    from toas.tools_cluster.apply_patch_ops import (
        apply_update_change_lines,
        find_chunk_start,
        format_change_chunk_preview,
    )

    # find_chunk_start with empty chunk
    assert find_chunk_start(["a", "b"], [], 0) == 0

    # format_change_chunk_preview with empty lines
    assert format_change_chunk_preview([]) == "<empty>"

    # format_change_chunk_preview with truncation
    preview = format_change_chunk_preview(["a" * 100], max_width=80)
    assert "..." in preview

    # apply_update_change_lines with empty change_lines
    result = apply_update_change_lines(["a", "b"], [], "test.txt")
    assert result == ["a", "b"]

    # apply_update_change_lines noop (old == new)
    change_lines = [" old", " old"]
    result = apply_update_change_lines(["old", "old"], change_lines, "test.txt")
    assert result == ["old", "old"]


def test_run_apply_patch_move_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("src.txt").write_text("x\n", encoding="utf-8")
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: src.txt",
            "*** Move to: dst.txt",
            "@@",
            "-x",
            "+x",
            "*** End Patch",
        ]
    )
    out = run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())
    assert out["ok"] is True
    assert not Path("src.txt").exists()
    assert Path("dst.txt").read_text(encoding="utf-8") == "x\n"


def test_apply_patch_helpers_edge_cases(tmp_path, monkeypatch):
    from toas.tools_cluster.apply_patch_ops import (
        format_change_chunk_preview,
        split_old_new_chunk,
    )

    # split_old_new_chunk with empty line
    old, new = split_old_new_chunk(["", "+new"])
    assert old == [""]
    assert new == ["", "new"]

    # format_change_chunk_preview with more than max_lines
    preview = format_change_chunk_preview(["a", "b", "c", "d", "e"], max_lines=3)
    assert "..." in preview


def test_run_apply_patch_invalid_hunk_kind(tmp_path, monkeypatch):
    """Test invalid hunk kind (line 198)."""
    monkeypatch.chdir(tmp_path)

    # Mock parse_apply_patch_hunks to return a hunk with invalid kind
    monkeypatch.setattr(
        "toas.tools_cluster.apply_patch_ops.parse_apply_patch_hunks",
        lambda _p: [{"kind": "invalid_kind", "path": "a.txt"}],
    )
    with pytest.raises(RuntimeError, match="invalid apply_patch hunk kind"):
        run_apply_patch({"patch": "nope"}, workspace_path_fn=lambda p: Path(p).resolve())
