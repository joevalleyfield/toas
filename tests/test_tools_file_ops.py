from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster.file_ops import run_replace_block, run_replace_range
from toas.tools_cluster.file_match_ops import best_equal_length_region, replace_block_mismatch_diagnostics


def test_run_replace_range_replaces_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = Path("test.txt")
    test_file.write_text("a\nb\nc\n", encoding="utf-8")

    result = run_replace_range(
        {
            "path": "test.txt",
            "start_line": 2,
            "end_line": 2,
            "replacement_block": "B\n",
        }
    )

    assert result["ok"] is True
    assert test_file.read_text(encoding="utf-8") == "a\nB\nc\n"


def test_run_replace_block_reports_mismatch_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = Path("test.txt")
    test_file.write_text("one\ntwo\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="found no matches") as exc:
        run_replace_block(
            {
                "path": "test.txt",
                "search_block": "three\n",
                "replacement_block": "THREE\n",
            }
        )

    assert "search chars=" in str(exc.value)


def test_replace_block_mismatch_diagnostics_reports_budget_exhaustion(monkeypatch):
    clock = iter([0.0, 0.2, 2.0])
    monkeypatch.setattr("toas.tools_cluster.file_match_ops._monotonic", lambda: next(clock))

    msg = replace_block_mismatch_diagnostics("alpha\nbeta\ngamma\n" * 20, "beta\nGAMMA\n")

    assert "best equal-length region:" in msg
    assert "near-match budget exhausted after 0.2s; returning best-so-far" in msg


def test_replace_block_mismatch_diagnostics_uses_bounded_candidate_count():
    content = "".join(f"line {idx}\n" for idx in range(2000))
    msg = replace_block_mismatch_diagnostics(content, "line 1999\nmissing\n")

    marker = "candidates="
    assert marker in msg
    suffix = msg.split(marker, 1)[1]
    count = int(suffix.split()[0])
    assert count <= 80


def test_best_equal_length_region_returns_none_for_empty_content():
    assert best_equal_length_region("", "alpha") is None


def test_best_equal_length_region_respects_sampling_cap(monkeypatch):
    monkeypatch.setattr(
        "toas.tools_cluster.file_match_ops._line_based_candidate_starts",
        lambda _content, _search_block, _target_len: list(range(72)),
    )

    candidate = best_equal_length_region("x" * 200, "abc")

    assert candidate is not None
    assert candidate["candidates_considered"] == 72


def test_replace_block_mismatch_diagnostics_reports_newline_mismatch():
    msg = replace_block_mismatch_diagnostics("alpha\r\nbeta\r\n", "alpha\nbeta\n")

    assert "newline style mismatch: search uses LF, file uses CRLF" in msg


def test_replace_block_mismatch_diagnostics_preserves_first_line_indentation_in_diff():
    msg = replace_block_mismatch_diagnostics(
        "    # Default config (streaming mode enabled)\n"
        "    config_default = OperatorConfig()\n"
        "    enabled, source = resolver.resolve_stdout_stream(config_default)\n"
        "    assert enabled\n"
        "    assert source == \"default\"\n"
        "\n"
        "    # Env override enabled\n",
        "# Default config (streaming mode enabled)\n"
        "config_default = OperatorConfig()\n"
        "enabled, source = resolver.resolve_stdout_stream(config_default)\n"
        "assert enabled\n"
        "assert source == \"default\"\n",
    )

    assert "full-block indent-only mismatch: search_indent=4" in msg
    assert "staged repair: /queue heal search_indent=4" in msg
    assert "best-window diff:" not in msg


def test_replace_block_mismatch_diagnostics_suggests_search_indent_for_indent_only_mismatch():
    msg = replace_block_mismatch_diagnostics(
        "    alpha\n    beta\n",
        "alpha\nbeta\n",
    )

    assert "full-block indent-only mismatch: search_indent=4" in msg


def test_replace_block_mismatch_diagnostics_suggests_search_indent_for_yaml_full_block_shift():
    msg = replace_block_mismatch_diagnostics(
        "    for name in sorted(TOOL_REGISTRY):\n"
        "        tool = TOOL_REGISTRY[name]\n"
        "        args_str = \", \".join(tool.required_args) if tool.required_args else \"none\"\n"
        "        if name == \"shell\":\n"
        "            allowed = \", \".join(sorted(SHELL_ALLOWED))\n"
        "            lines.append(f\"  {name}  (args: {args_str})\")\n"
        "            lines.append(f\"    allowed commands: {allowed}\")\n"
        "            lines.append(\"    limits: workspace-bounded; timeout_s max 30s\")\n"
        "        else:\n"
        "            lines.append(f\"  {name}  (args: {args_str})\")\n"
        "    lines.append(\"  callable aliases: operation/tool_name, arguments/args/params, intent/intention\")\n",
        "for name in sorted(TOOL_REGISTRY):\n"
        "    tool = TOOL_REGISTRY[name]\n"
        "    args_str = \", \".join(tool.required_args) if tool.required_args else \"none\"\n"
        "    if name == \"shell\":\n"
        "        allowed = \", \".join(sorted(SHELL_ALLOWED))\n"
        "        lines.append(f\"  {name}  (args: {args_str})\")\n"
        "        lines.append(f\"    allowed commands: {allowed}\")\n"
        "        lines.append(\"    limits: workspace-bounded; timeout_s max 30s\")\n"
        "    else:\n"
        "        lines.append(f\"  {name}  (args: {args_str})\")\n"
        "lines.append(\"  callable aliases: operation/tool_name, arguments/args/params, intent/intention\")\n",
    )

    assert "full-block indent-only mismatch: search_indent=4" in msg
    assert "best-window diff:" not in msg


def test_replace_block_mismatch_diagnostics_reports_no_overlap_for_candidate():
    msg = replace_block_mismatch_diagnostics("aaaa", "zz")

    assert "closest overlap: none" in msg


def test_replace_block_mismatch_diagnostics_reports_no_overlap_for_empty_file():
    msg = replace_block_mismatch_diagnostics("", "alpha")

    assert "closest overlap: none" in msg


def test_run_replace_range_context_mismatch_and_indent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = Path("test.txt")
    test_file.write_text("aa\nbb\ncc\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="context_start mismatch"):
        run_replace_range(
            {
                "path": "test.txt",
                "start_line": 2,
                "end_line": 2,
                "replacement_block": "x\n",
                "context_start": "WRONG",
            }
        )

    with pytest.raises(RuntimeError, match="context_end mismatch"):
        run_replace_range(
            {
                "path": "test.txt",
                "start_line": 2,
                "end_line": 2,
                "replacement_block": "x\n",
                "context_end": "WRONG",
            }
        )

    out = run_replace_range(
        {
            "path": "test.txt",
            "start_line": 2,
            "end_line": 2,
            "replacement_block": "y\nz\n",
            "indent": 2,
        }
    )
    assert out["ok"] is True
    assert test_file.read_text(encoding="utf-8") == "aa\n  y\n  z\ncc\n"


def test_run_replace_block_expected_count_and_indents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = Path("test.txt")
    test_file.write_text("k\nk\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="matched 2 blocks; expected 1"):
        run_replace_block(
            {
                "path": "test.txt",
                "search_block": "k\n",
                "replacement_block": "x\n",
                "expected_count": 1,
            }
        )

    with pytest.raises(RuntimeError, match="search_indent must be a non-negative int"):
        run_replace_block(
            {
                "path": "test.txt",
                "search_block": "k\n",
                "replacement_block": "x\n",
                "search_indent": -1,
            }
        )

    out = run_replace_block(
        {
            "path": "test.txt",
            "search_block": "k\nk\n",
            "replacement_block": "x",
            "ensure_trailing_newline": False,
            "search_indent": "",
            "replacement_indent": "",
        }
    )
    assert out["ok"] is True
    assert test_file.read_text(encoding="utf-8") == "x"


def test_run_replace_range_validation_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # path must be a non-empty string
    with pytest.raises(RuntimeError, match="path must be a non-empty string"):
        run_replace_range({"path": "", "start_line": 1, "end_line": 1, "replacement_block": "x"})

    with pytest.raises(RuntimeError, match="path must be a non-empty string"):
        run_replace_range({"path": 123, "start_line": 1, "end_line": 1, "replacement_block": "x"})

    # start_line must be a positive int
    with pytest.raises(RuntimeError, match="start_line must be a positive int"):
        run_replace_range({"path": "test.txt", "start_line": 0, "end_line": 1, "replacement_block": "x"})

    with pytest.raises(RuntimeError, match="start_line must be a positive int"):
        run_replace_range({"path": "test.txt", "start_line": "bad", "end_line": 1, "replacement_block": "x"})

    # end_line must be >= start_line
    with pytest.raises(RuntimeError, match="end_line must be >= start_line"):
        run_replace_range({"path": "test.txt", "start_line": 2, "end_line": 1, "replacement_block": "x"})

    # replacement_block must be a string
    with pytest.raises(RuntimeError, match="replacement_block must be a string"):
        run_replace_range({"path": "test.txt", "start_line": 1, "end_line": 1, "replacement_block": 123})

    # context_start must be a string
    with pytest.raises(RuntimeError, match="context_start must be a string"):
        run_replace_range({"path": "test.txt", "start_line": 1, "end_line": 1, "replacement_block": "x", "context_start": 123})

    # context_end must be a string
    with pytest.raises(RuntimeError, match="context_end must be a string"):
        run_replace_range({"path": "test.txt", "start_line": 1, "end_line": 1, "replacement_block": "x", "context_end": 123})

    # end_line beyond file length
    (tmp_path / "test.txt").write_text("a\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="end_line.*is beyond file length"):
        run_replace_range({"path": "test.txt", "start_line": 1, "end_line": 5, "replacement_block": "x"})


def test_run_replace_block_validation_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # path must be a non-empty string
    with pytest.raises(RuntimeError, match="path must be a non-empty string"):
        run_replace_block({"path": "", "search_block": "a", "replacement_block": "x"})

    # search_block must be a non-empty string
    with pytest.raises(RuntimeError, match="search_block must be a non-empty string"):
        run_replace_block({"path": "test.txt", "search_block": "", "replacement_block": "x"})

    with pytest.raises(RuntimeError, match="search_block must be a non-empty string"):
        run_replace_block({"path": "test.txt", "search_block": 123, "replacement_block": "x"})

    # replacement_block must be a string
    with pytest.raises(RuntimeError, match="replacement_block must be a string"):
        run_replace_block({"path": "test.txt", "search_block": "a", "replacement_block": 123})

    # expected_count must be a positive int
    with pytest.raises(RuntimeError, match="expected_count must be a positive int"):
        run_replace_block({"path": "test.txt", "search_block": "a", "replacement_block": "x", "expected_count": 0})

    with pytest.raises(RuntimeError, match="expected_count must be a positive int"):
        run_replace_block({"path": "test.txt", "search_block": "a", "replacement_block": "x", "expected_count": "bad"})

    # match_mode must be one of strict, default, lax
    with pytest.raises(RuntimeError, match="match_mode must be one of"):
        run_replace_block({"path": "test.txt", "search_block": "a", "replacement_block": "x", "match_mode": 123})

    # requires a file
    with pytest.raises(RuntimeError, match="requires a file"):
        run_replace_block({"path": "missing.txt", "search_block": "a", "replacement_block": "x"})


def test_run_replace_range_requires_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="requires a file"):
        run_replace_range({"path": "missing.txt", "start_line": 1, "end_line": 1, "replacement_block": "x"})


def test_normalize_indent_validation(tmp_path, monkeypatch):
    from toas.tools_cluster.file_ops import _normalize_indent

    # non-int, non-string value
    with pytest.raises(RuntimeError, match="must be an int or a string"):
        _normalize_indent(1.5, tool_name="test", arg_name="indent")

    # None returns default
    assert _normalize_indent(None, tool_name="test", arg_name="indent") == ""
    assert _normalize_indent(None, tool_name="test", arg_name="indent", default="  ") == "  "

    # _apply_indent empty text
    from toas.tools_cluster.file_ops import _apply_indent

    assert _apply_indent("", "  ") == ""
    assert _apply_indent("hello", "") == "hello"
