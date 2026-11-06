from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster.apply_patch_ops import (
    _normalize_add_lines,
    _normalize_chunk_diff_lines,
    find_unique_stripped_match,
    parse_apply_patch_hunks,
    render_apply_patch_hunks,
    run_apply_patch,
)


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


def test_run_apply_patch_update_auto_preserves_existing_crlf(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = Path("a.txt")
    target.write_text("old\r\n", encoding="utf-8", newline="")
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
    with target.open("r", encoding="utf-8", newline="") as handle:
        assert handle.read() == "new\r\n"


def test_run_apply_patch_add_uses_configured_crlf_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[tool_writes]\nnewline_style = "crlf"\n', encoding="utf-8")
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Add File: a.txt",
            "+one",
            "+two",
            "*** End Patch",
        ]
    )
    out = run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())
    assert out["ok"] is True
    with Path("a.txt").open("r", encoding="utf-8", newline="") as handle:
        assert handle.read() == "one\r\ntwo\r\n"


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
        _shift_indent,
        find_unique_indent_shifted_chunk,
        format_change_chunk_preview,
        format_chunk_mismatch_diff,
        split_old_new_chunk,
    )

    # split_old_new_chunk with empty line
    old, new = split_old_new_chunk(["", "+new"])
    assert old == [""]
    assert new == ["", "new"]

    # format_change_chunk_preview with more than max_lines
    preview = format_change_chunk_preview(["a", "b", "c", "d", "e"], max_lines=3)
    assert "..." in preview

    # _shift_indent with blank lines and negative delta
    shifted_pos = _shift_indent(["", "  code"], 2)
    assert shifted_pos == ["", "    code"]
    shifted_neg = _shift_indent(["", "    code"], -2)
    assert shifted_neg == ["", "  code"]

    # find_unique_indent_shifted_chunk edge cases
    assert find_unique_indent_shifted_chunk(["a"], [], []) is None
    assert find_unique_indent_shifted_chunk(["a"], ["   "], ["   "]) is None

    # Candidate with empty line matching old_chunk empty line and mismatching
    lines_with_empty = ["", "    target"]
    chunk_with_empty = ["", "  target"]
    res = find_unique_indent_shifted_chunk(lines_with_empty, chunk_with_empty, chunk_with_empty)
    assert res is not None and res[0] == 0

    lines_non_empty = ["not empty", "    target"]
    assert find_unique_indent_shifted_chunk(lines_non_empty, chunk_with_empty, chunk_with_empty) is None

    # format_chunk_mismatch_diff empty inputs
    assert format_chunk_mismatch_diff([], ["x"]) == ""
    assert format_chunk_mismatch_diff(["x"], []) == ""


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


def test_render_apply_patch_hunks_and_normalization():
    hunks = [
        {"kind": "add", "path": "new.txt", "lines": ["line 1", "line 2"]},
        {"kind": "delete", "path": "old.txt"},
        {
            "kind": "update",
            "path": "mod.txt",
            "move_to": "moved.txt",
            "change_chunks": [
                [" context", "-remove", "+add"],
                ["@@", " more context"],
            ],
        },
    ]
    rendered = render_apply_patch_hunks(hunks)
    assert "*** Begin Patch" in rendered
    assert "*** Add File: new.txt" in rendered
    assert "*** Delete File: old.txt" in rendered
    assert "*** Update File: mod.txt" in rendered
    assert "*** Move to: moved.txt" in rendered
    assert "*** End Patch" in rendered

    with pytest.raises(RuntimeError, match="invalid apply_patch hunk kind"):
        render_apply_patch_hunks([{"kind": "unsupported", "path": "foo"}])

    # Test _normalize_add_lines and _normalize_chunk_diff_lines edge cases
    assert _normalize_add_lines([]) == []
    assert _normalize_add_lines(["", "  "]) == ["", "  "]
    assert _normalize_add_lines(["+already"]) == ["+already"]
    assert _normalize_add_lines(["  +first", "  +second"]) == ["+first", "+second"]

    assert _normalize_chunk_diff_lines([]) == []
    assert _normalize_chunk_diff_lines(["", "   "]) == ["", "   "]
    assert _normalize_chunk_diff_lines(["-already"]) == ["-already"]
    assert _normalize_chunk_diff_lines(["  -first", "  +second"]) == ["-first", "+second"]
    assert _normalize_chunk_diff_lines(["   context", "  -first", "  +second"]) == [" context", "-first", "+second"]
    assert _normalize_chunk_diff_lines(["  no_marker_1", "  no_marker_2"]) == ["  no_marker_1", "  no_marker_2"]


def test_parse_apply_patch_hunks_healing_indentation_and_blank_lines():
    # Patch with leading/trailing blank lines, outer indentation, and delimiter spaces
    patch = "\n\n  *** Begin Patch\n  *** Add File: test.txt\n    +first\n    +second\n  *** End Patch\n\n"
    hunks = parse_apply_patch_hunks(patch)
    assert len(hunks) == 1
    assert hunks[0]["kind"] == "add"
    assert hunks[0]["path"] == "test.txt"
    assert hunks[0]["lines"] == ["first", "second"]

    # Patch with indented @@ and shifted diff markers
    patch_update = "\n".join(
        [
            "*** Begin Patch",
            "  *** Update File: foo.py",
            "  *** Move to: bar.py",
            "    @@",
            "     context",
            "    -old",
            "    +new",
            "*** End Patch",
        ]
    )
    hunks_update = parse_apply_patch_hunks(patch_update)
    assert len(hunks_update) == 1
    assert hunks_update[0]["kind"] == "update"
    assert hunks_update[0]["path"] == "foo.py"
    assert hunks_update[0]["move_to"] == "bar.py"
    assert hunks_update[0]["change_chunks"] == [[" context", "-old", "+new"]]

    # Empty hunks after begin/end
    with pytest.raises(RuntimeError, match="patch must include at least one hunk"):
        parse_apply_patch_hunks("*** Begin Patch\n*** End Patch")


def test_find_unique_stripped_match_and_reconciliation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Empty or blank chunk edge cases
    assert find_unique_stripped_match(["a"], []) is None
    assert find_unique_stripped_match(["a"], ["   "]) is None
    assert find_unique_stripped_match([], ["-a"]) is None

    # Ambiguous match (multiple windows match stripped lines)
    dup_lines = ["def foo():", "    pass", "def foo():", "    pass"]
    assert find_unique_stripped_match(dup_lines, [" def foo():", "-pass", "+return 1"]) is None

    # Forward anchor test (added lines before any context line)
    target_lines = ["    x = 1"]
    change_lines = ["+y = 0", " x = 1"]
    res = find_unique_stripped_match(target_lines, change_lines)
    assert res is not None
    start, old_c, new_c = res
    assert start == 0
    assert new_c == ["    y = 0", "    x = 1"]

    # Blank added line preservation
    target_lines = ["    x = 1"]
    change_lines = [" x = 1", "+"]
    res = find_unique_stripped_match(target_lines, change_lines)
    assert res is not None
    assert res[2] == ["    x = 1", ""]


def test_apply_patch_unique_stripped_reconciliation_integration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = Path("sample.py")
    target.write_text(
        "def example():\n"
        "    if True:\n"
        "        print('old')\n"
        "        return True\n",
        encoding="utf-8",
    )
    # Hunk uses 2-space indentation instead of 4-space / 8-space
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: sample.py",
            "@@",
            "  if True:",
            "-   print('old')",
            "+   print('new')",
            "+   notify()",
            "    return True",
            "*** End Patch",
        ]
    )
    out = run_apply_patch({"patch": patch}, workspace_path_fn=lambda p: Path(p).resolve())
    assert out["ok"] is True
    assert target.read_text(encoding="utf-8") == (
        "def example():\n"
        "    if True:\n"
        "        print('new')\n"
        "        notify()\n"
        "        return True\n"
    )


def test_run_apply_patch_atomic_failure_rollback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    file1 = Path("f1.txt")
    file1.write_text("initial f1\n", encoding="utf-8")

    # 3 hunks: hunk 1 updates f1, hunk 2 adds f2, hunk 3 fails on missing f3
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: f1.txt",
            "@@",
            "-initial f1",
            "+updated f1",
            "*** Add File: f2.txt",
            "+f2 line",
            "*** Update File: missing.txt",
            "@@",
            "-old",
            "+new",
            "*** End Patch",
        ]
    )

    with pytest.raises(RuntimeError) as exc_info:
        run_apply_patch({"patch": patch, "atomic": True}, workspace_path_fn=lambda p: Path(p).resolve())

    exc = exc_info.value
    assert "update failed: file does not exist: missing.txt" in str(exc)
    assert exc.applied_hunks == []
    assert exc.failed_hunk["index"] == 3
    assert exc.skipped_hunks == []
    assert exc.files_touched == []
    assert exc.unapplied_patch == patch

    # Ensure disk state was NEVER touched
    assert file1.read_text(encoding="utf-8") == "initial f1\n"
    assert not Path("f2.txt").exists()


def test_run_apply_patch_atomic_success_and_edge_cases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f_mod = Path("mod.txt")
    f_mod.write_text("before\n", encoding="utf-8")
    f_del = Path("del.txt")
    f_del.write_text("delete me\n", encoding="utf-8")

    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Add File: added.txt",
            "+added content",
            "*** Delete File: del.txt",
            "*** Update File: mod.txt",
            "*** Move to: renamed.txt",
            "@@",
            "-before",
            "+after",
            "*** End Patch",
        ]
    )

    out = run_apply_patch({"patch": patch, "atomic": True}, workspace_path_fn=lambda p: Path(p).resolve())
    assert out["ok"] is True
    assert out["atomic"] is True
    assert Path("added.txt").read_text(encoding="utf-8") == "added content\n"
    assert not f_del.exists()
    assert not f_mod.exists()
    assert Path("renamed.txt").read_text(encoding="utf-8") == "after\n"

    # Missing file path in atomic mode
    monkeypatch.setattr(
        "toas.tools_cluster.apply_patch_ops.parse_apply_patch_hunks",
        lambda _p: [{"kind": "add", "path": ""}],
    )
    with pytest.raises(RuntimeError, match="missing file path"):
        run_apply_patch({"patch": "dummy", "atomic": True}, workspace_path_fn=lambda p: Path(p).resolve())


def test_run_apply_patch_non_atomic_partial_and_unapplied_patch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    file1 = Path("f1.txt")
    file1.write_text("initial f1\n", encoding="utf-8")

    # 3 hunks: hunk 1 updates f1 (succeeds), hunk 2 fails (missing f2), hunk 3 adds f3 (skipped)
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Update File: f1.txt",
            "@@",
            "-initial f1",
            "+updated f1",
            "*** Update File: missing.txt",
            "@@",
            "-old",
            "+new",
            "*** Add File: f3.txt",
            "+f3 content",
            "*** End Patch",
        ]
    )

    with pytest.raises(RuntimeError) as exc_info:
        run_apply_patch({"patch": patch, "atomic": False}, workspace_path_fn=lambda p: Path(p).resolve())

    exc = exc_info.value
    assert "tool apply_patch non-atomic execution failed" in str(exc)
    assert len(exc.applied_hunks) == 1
    assert exc.failed_hunk["index"] == 2
    assert len(exc.skipped_hunks) == 1
    assert exc.skipped_hunks[0]["path"] == "f3.txt"
    assert exc.files_touched == ["f1.txt"]

    # Verify disk state reflects partial execution
    assert file1.read_text(encoding="utf-8") == "updated f1\n"
    assert not Path("f3.txt").exists()

    # Verify unapplied_patch contains only hunk 2 and hunk 3
    unapplied = exc.unapplied_patch
    unapplied_hunks = parse_apply_patch_hunks(unapplied)
    assert len(unapplied_hunks) == 2
    assert unapplied_hunks[0]["path"] == "missing.txt"
    assert unapplied_hunks[1]["path"] == "f3.txt"

    # Non-atomic missing path
    monkeypatch.setattr(
        "toas.tools_cluster.apply_patch_ops.parse_apply_patch_hunks",
        lambda _p: [{"kind": "add", "path": ""}],
    )
    with pytest.raises(RuntimeError, match="missing file path"):
        run_apply_patch({"patch": "dummy", "atomic": False}, workspace_path_fn=lambda p: Path(p).resolve())


def test_run_apply_patch_non_atomic_success_and_string_atomic_arg(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    file1 = Path("f1.txt")
    file1.write_text("a\n", encoding="utf-8")
    del_file = Path("del.txt")
    del_file.write_text("d\n", encoding="utf-8")

    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Add File: f_added.txt",
            "+added",
            "*** Delete File: del.txt",
            "*** Update File: f1.txt",
            "*** Move to: f1_moved.txt",
            "@@",
            "-a",
            "+b",
            "*** End Patch",
        ]
    )

    out = run_apply_patch({"patch": patch, "atomic": "false"}, workspace_path_fn=lambda p: Path(p).resolve())
    assert out["ok"] is True
    assert out["atomic"] is False
    assert Path("f_added.txt").read_text(encoding="utf-8") == "added\n"
    assert not del_file.exists()
    assert not file1.exists()
    assert Path("f1_moved.txt").read_text(encoding="utf-8") == "b\n"

    # Non-atomic invalid hunk kind
    monkeypatch.setattr(
        "toas.tools_cluster.apply_patch_ops.parse_apply_patch_hunks",
        lambda _p: [{"kind": "unsupported", "path": "x.txt"}],
    )
    with pytest.raises(RuntimeError, match="invalid apply_patch hunk kind"):
        run_apply_patch({"patch": "dummy", "atomic": False}, workspace_path_fn=lambda p: Path(p).resolve())


def test_apply_patch_coverage_edge_cases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Line 83: decreasing indent in patch
    patch = "    *** Begin Patch\n  *** Add File: dec.txt\n  +x\n  *** End Patch"
    hunks = parse_apply_patch_hunks(patch)
    assert len(hunks) == 1
    assert hunks[0]["lines"] == ["x"]

    # Line 131: multi-chunk update with invalid line in first chunk
    invalid_patch = (
        "*** Begin Patch\n"
        "*** Update File: u.txt\n"
        "@@\n"
        "bad_line\n"
        "@@\n"
        " context\n"
        "*** End Patch"
    )
    with pytest.raises(RuntimeError, match="invalid apply_patch update hunk: expected context/add/remove lines"):
        parse_apply_patch_hunks(invalid_patch)

    # Line 449 & 458: atomic simulation modifying a file added in an earlier hunk of the same patch,
    # and re-adding a file deleted in an earlier hunk
    chained_patch = (
        "*** Begin Patch\n"
        "*** Add File: chained.txt\n"
        "+line1\n"
        "*** Update File: chained.txt\n"
        "@@\n"
        " line1\n"
        "+line2\n"
        "*** Delete File: chained.txt\n"
        "*** Add File: chained.txt\n"
        "+new_line\n"
        "*** End Patch"
    )
    out = run_apply_patch({"patch": chained_patch, "atomic": True}, workspace_path_fn=lambda p: Path(p).resolve())
    assert out["ok"] is True
    assert Path("chained.txt").read_text(encoding="utf-8") == "new_line\n"

    # Lines 588, 604, 606, 632: non-atomic validation error branches
    # 588: add existing file in non-atomic mode
    Path("already_exists.txt").write_text("exists\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="add failed: file already exists"):
        run_apply_patch(
            {"patch": "*** Begin Patch\n*** Add File: already_exists.txt\n+line\n*** End Patch", "atomic": False},
            workspace_path_fn=lambda p: Path(p).resolve(),
        )

    # 604: delete non-existent file in non-atomic mode
    with pytest.raises(RuntimeError, match="delete failed: file does not exist"):
        run_apply_patch(
            {"patch": "*** Begin Patch\n*** Delete File: non_existent.txt\n*** End Patch", "atomic": False},
            workspace_path_fn=lambda p: Path(p).resolve(),
        )

    # 606: delete directory in non-atomic mode
    Path("some_dir").mkdir(exist_ok=True)
    with pytest.raises(RuntimeError, match="delete failed: path is a directory"):
        run_apply_patch(
            {"patch": "*** Begin Patch\n*** Delete File: some_dir\n*** End Patch", "atomic": False},
            workspace_path_fn=lambda p: Path(p).resolve(),
        )

    # 632: move to existing target in non-atomic mode
    Path("src_m.txt").write_text("src\n", encoding="utf-8")
    Path("dst_m.txt").write_text("dst\n", encoding="utf-8")
    move_patch = (
        "*** Begin Patch\n"
        "*** Update File: src_m.txt\n"
        "*** Move to: dst_m.txt\n"
        "@@\n"
        "-src\n"
        "+src\n"
        "*** End Patch"
    )
    with pytest.raises(RuntimeError, match="move failed: target exists"):
        run_apply_patch({"patch": move_patch, "atomic": False}, workspace_path_fn=lambda p: Path(p).resolve())
