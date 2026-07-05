from toas.tools_cluster.rendering import (
    _infer_shell_file_output_path,
    _make_relative,
    _parse_search_match,
    _shell_source_text,
    infer_fence_language,
    render_fenced_output,
    render_import_block,
    render_search_excerpt_blocks,
    render_search_success,
    render_shell_stdout_import_block,
    shape_result_content,
    stable_import_block_id,
)


def test_shape_result_content_shell_success_and_error():
    success = shape_result_content(
        {
            "tool_name": "shell",
            "ok": True,
            "summary": "exit=0",
            "stdout": "hello",
            "stderr": "",
        }
    )
    assert success == (
        "[OK] shell: exit=0\n"
        "stdout:\n"
        "```text toas-output kind=stdout source=tool.shell potency=inert\n"
        "hello\n"
        "```"
    )

    error = shape_result_content(
        {
            "tool_name": "shell_script",
            "ok": False,
            "summary": "exit=1",
            "stdout": "",
            "stderr": "boom",
        }
    )
    assert error == (
        "[ERROR] shell_script: exit=1\n"
        "stderr:\n"
        "```text toas-output kind=stderr source=tool.shell_script potency=inert\n"
        "boom\n"
        "```"
    )


def test_shape_result_content_read_and_search_success():
    read = shape_result_content(
        {
            "tool_name": "read_file",
            "ok": True,
            "summary": "a.txt",
            "path": "a.txt",
            "content": "hello\n",
        }
    )
    block_id = stable_import_block_id(
        kind="file",
        path="a.txt",
        source="workspace",
        line_start=None,
        line_end=None,
        content="hello\n",
    )
    assert read == (
        "[OK] read_file: a.txt\n"
        f"```text toas-output kind=file source=workspace potency=inert path=a.txt block_id={block_id}\n"
        "hello\n"
        "```"
    )

    numbered = shape_result_content(
        {
            "tool_name": "read_file",
            "ok": True,
            "summary": "a.txt:2-3",
            "path": "a.txt",
            "content": "beta\ngamma\n",
            "display_content": "   2: beta\n   3: gamma\n",
        }
    )
    numbered_block_id = stable_import_block_id(
        kind="file",
        path="a.txt:2-3",
        source="workspace",
        line_start=None,
        line_end=None,
        content="   2: beta\n   3: gamma\n",
    )
    assert numbered == (
        "[OK] read_file: a.txt\n"
        f"```text toas-output kind=file source=workspace potency=inert path=a.txt:2-3 block_id={numbered_block_id}\n"
        "   2: beta\n"
        "   3: gamma\n"
        "```"
    )

    ranged = shape_result_content(
        {
            "tool_name": "read_file",
            "ok": True,
            "summary": "a.txt:2-3",
            "path": "a.txt",
            "content": "beta\ngamma\n",
        }
    )
    ranged_block_id = stable_import_block_id(
        kind="file",
        path="a.txt:2-3",
        source="workspace",
        line_start=None,
        line_end=None,
        content="beta\ngamma\n",
    )
    assert ranged == (
        "[OK] read_file: a.txt\n"
        f"```text toas-output kind=file source=workspace potency=inert path=a.txt:2-3 block_id={ranged_block_id}\n"
        "beta\ngamma\n"
        "```"
    )

    search_with_content = shape_result_content(
        {
            "tool_name": "search",
            "ok": True,
            "summary": "2 matches",
            "content": "a:1:x\nb:2:x",
        }
    )
    assert "[OK] search: 2 matches" in search_with_content
    assert "```python toas-output kind=result source=tool.search potency=inert block_id=" in search_with_content
    assert "a" in search_with_content
    assert "    1: x" in search_with_content
    assert "b" in search_with_content
    assert "    2: x" in search_with_content
    # Ensure it's a single block
    assert search_with_content.count("```") == 2

    search_without_content = shape_result_content(
        {
            "tool_name": "search",
            "ok": True,
            "summary": "0 matches",
            "content": "",
        }
    )
    assert search_without_content == "[OK] search: 0 matches"


def test_import_block_infers_language_and_formats_metadata():
    source = "sed -n '1,80p' src/toas/step.py"
    rendered = render_import_block(
        content="print('hi')",
        path="src/toas/step.py",
        source=source,
    )
    block_id = stable_import_block_id(
        kind="file",
        path="src/toas/step.py",
        source=source,
        line_start=None,
        line_end=None,
        content="print('hi')",
    )

    assert rendered == (
        "```python toas-output kind=file source=\"sed -n '1,80p' src/toas/step.py\" potency=inert path=src/toas/step.py "
        f"block_id={block_id}\n"
        "print('hi')\n"
        "```"
    )


def test_import_block_sizes_fence_to_contain_embedded_backticks():
    rendered = render_import_block(
        content="```\ninside\n```",
        path="notes/example.md",
    )

    assert rendered.startswith("````markdown toas-output kind=file source=workspace potency=inert path=notes/example.md block_id=")
    assert rendered.endswith("\n````")


def test_infer_fence_language_uses_overrides_and_text_fallback():
    assert infer_fence_language(None) == "text"
    assert infer_fence_language("src/toas/step.py") == "python"
    assert infer_fence_language("docs/roadmap.md") == "markdown"
    assert infer_fence_language("Makefile") == "makefile"
    assert infer_fence_language("unknown.extremely-custom") == "text"


def test_shape_result_content_shell_cat_stdout_uses_import_block():
    content = "def main():\n    pass"
    rendered = shape_result_content(
        {
            "tool_name": "shell",
            "ok": True,
            "summary": "exit=0",
            "argv": ["cat", "src/toas/step.py"],
            "stdout": content,
            "stderr": "",
        }
    )
    block_id = stable_import_block_id(
        kind="file",
        path="src/toas/step.py",
        source="cat src/toas/step.py",
        line_start=None,
        line_end=None,
        content=content,
    )

    assert rendered == (
        "[OK] shell: exit=0\n"
        "stdout:\n"
        f"```python toas-output kind=file source=\"cat src/toas/step.py\" potency=inert path=src/toas/step.py block_id={block_id}\n"
        "def main():\n"
        "    pass\n"
        "```"
    )


def test_shape_result_content_shell_sed_stdout_uses_import_block_from_shell_command():
    content = "line1\nline2"
    rendered = shape_result_content(
        {
            "tool_name": "shell",
            "ok": True,
            "summary": "exit=0",
            "argv": ["sh", "-lc", "sed -n '1,2p' src/toas/step.py"],
            "stdout": content,
            "stderr": "",
        }
    )
    block_id = stable_import_block_id(
        kind="file",
        path="src/toas/step.py",
        source="sed -n 1,2p src/toas/step.py",
        line_start=None,
        line_end=None,
        content=content,
    )

    assert rendered == (
        "[OK] shell: exit=0\n"
        "stdout:\n"
        f"```python toas-output kind=file source=\"sed -n 1,2p src/toas/step.py\" potency=inert path=src/toas/step.py block_id={block_id}\n"
        "line1\n"
        "line2\n"
        "```"
    )


def test_shape_result_content_shell_ambiguous_stdout_fenced():
    rendered = shape_result_content(
        {
            "tool_name": "shell",
            "ok": True,
            "summary": "exit=0",
            "argv": ["pwd"],
            "stdout": "/workspace",
            "stderr": "",
        }
    )

    assert rendered == (
        "[OK] shell: exit=0\n"
        "stdout:\n"
        "```text toas-output kind=stdout source=tool.shell potency=inert\n"
        "/workspace\n"
        "```"
    )


def test_shape_result_content_shell_head_without_path_fenced():
    rendered = shape_result_content(
        {
            "tool_name": "shell",
            "ok": True,
            "summary": "exit=0",
            "argv": ["head", "-n", "10"],
            "stdout": "alpha",
            "stderr": "",
        }
    )

    assert rendered == (
        "[OK] shell: exit=0\n"
        "stdout:\n"
        "```text toas-output kind=stdout source=tool.shell potency=inert\n"
        "alpha\n"
        "```"
    )


def test_shell_stdout_import_block_edge_cases():
    assert render_shell_stdout_import_block({"ok": False, "stdout": "x", "argv": ["cat", "x.py"]}) is None
    assert render_shell_stdout_import_block({"ok": True, "stdout": "", "argv": ["cat", "x.py"]}) is None
    assert _infer_shell_file_output_path(["sh", "-lc", ""]) is None
    assert _infer_shell_file_output_path(["sh", "-lc", "cat 'unterminated"]) is None
    assert _shell_source_text(123) == "shell"


def test_shape_result_content_get_structure_and_replace_range_success():
    structure = shape_result_content(
        {
            "tool_name": "get_structure",
            "ok": True,
            "summary": "2 symbols",
            "structure": [
                {"kind": "function", "name": "a", "start_line": 1, "end_line": 2, "path": "m.py"},
                {"kind": "class", "name": "B", "start_line": 4, "end_line": 8},
            ],
        }
    )
    assert structure == (
        "[OK] get_structure: 2 symbols\n"
        "```text toas-output kind=result source=tool.get_structure potency=inert\n"
        "function.a (1-2) m.py\n"
        "class.B (4-8) \n"
        "```"
    )

    replace_range = shape_result_content({"tool_name": "replace_range", "ok": True, "summary": "replaced"})
    assert replace_range == "[OK] replace_range: replaced"


def test_shape_result_content_replace_block_variants():
    with_preview = shape_result_content(
        {
            "tool_name": "replace_block",
            "ok": True,
            "summary": "replaced 1",
            "path": "x.py",
            "changed_line_start": 3,
            "changed_line_end": 5,
            "preview": "3:new\n4:new\n5:new",
        }
    )
    assert with_preview == (
        "[OK] replace_block: replaced 1 (x.py) lines 3-5\n"
        "preview:\n"
        "```text toas-output kind=result source=tool.replace_block potency=inert path=x.py\n"
        "3:new\n"
        "4:new\n"
        "5:new\n"
        "```"
    )

    content_long = "\n".join(f"l{i}" for i in range(1, 25))
    long_preview = shape_result_content(
        {
            "tool_name": "replace_block",
            "ok": True,
            "summary": "replaced",
            "content": content_long,
        }
    )
    assert "..." in long_preview
    assert long_preview.startswith(
        "[OK] replace_block: replaced\n"
        "preview:\n"
        "```text toas-output kind=result source=tool.replace_block potency=inert\n"
    )

    content_short = shape_result_content(
        {
            "tool_name": "replace_block",
            "ok": True,
            "summary": "replaced",
            "content": "a\nb",
        }
    )
    assert content_short == (
        "[OK] replace_block: replaced\n"
        "preview:\n"
        "```text toas-output kind=result source=tool.replace_block potency=inert\n"
        "a\n"
        "b\n"
        "```"
    )

    base_only = shape_result_content(
        {
            "tool_name": "replace_block",
            "ok": True,
            "summary": "replaced",
            "content": "   ",
        }
    )
    assert base_only == "[OK] replace_block: replaced"


def test_shape_result_content_default_success_and_error_variants():
    success_with_content = shape_result_content(
        {
            "tool_name": "echo",
            "ok": True,
            "summary": "done",
            "content": "detail",
            "intention": "intent",
        }
    )
    assert success_with_content == "[OK] echo (intent): done\ndetail"

    success_with_multiline_content = shape_result_content(
        {
            "tool_name": "echo",
            "ok": True,
            "summary": "done",
            "content": "detail\nmore detail",
        }
    )
    assert success_with_multiline_content == (
        "[OK] echo: done\n"
        "```text toas-output kind=result source=tool.echo potency=inert\n"
        "detail\n"
        "more detail\n"
        "```"
    )

    success_with_intent_alias = shape_result_content(
        {
            "tool_name": "echo",
            "ok": True,
            "summary": "done",
            "content": "detail",
            "intent": "intent",
        }
    )
    assert success_with_intent_alias == "[OK] echo (intent): done\ndetail"

    success_summary_only = shape_result_content(
        {
            "tool_name": "echo",
            "ok": True,
            "summary": "done",
            "content": "done",
        }
    )
    assert success_summary_only == "[OK] echo: done"

    success_fallback_content = shape_result_content(
        {
            "tool_name": "echo",
            "ok": True,
            "summary": "",
            "content": "detail",
        }
    )
    assert success_fallback_content == "[OK] echo: detail"

    error_with_intention = shape_result_content(
        {
            "tool_name": "echo",
            "ok": False,
            "error": "bad",
            "summary": "ignored",
            "content": "ignored",
            "intention": "intent",
        }
    )
    assert error_with_intention == "[ERROR] echo (intent): bad"

    error_with_intent_alias = shape_result_content(
        {
            "tool_name": "echo",
            "ok": False,
            "error": "bad",
            "summary": "ignored",
            "content": "ignored",
            "intent": "intent",
        }
    )
    assert error_with_intent_alias == "[ERROR] echo (intent): bad"

    error_fallback = shape_result_content(
        {
            "tool_name": "echo",
            "ok": False,
            "summary": "bad summary",
        }
    )
    assert error_fallback == "[ERROR] echo: bad summary"


def test_shape_result_content_error_includes_shell_argv_repair_hint():
    rendered = shape_result_content(
        {
            "tool_name": "shell",
            "ok": False,
            "summary": "invalid arguments for tool shell: argv must be a non-empty list[str]",
            "error": "invalid arguments for tool shell: argv must be a non-empty list[str]",
        }
    )
    assert "next valid shape:" in rendered
    assert "- operation: shell" in rendered
    assert 'argv: ["pwd"]' in rendered


def test_shape_result_content_error_includes_apply_patch_repair_hint():
    rendered = shape_result_content(
        {
            "tool_name": "apply_patch",
            "ok": False,
            "error": "invalid arguments for tool apply_patch: patch must start with '*** Begin Patch'",
        }
    )
    assert "next valid shape:" in rendered
    assert "- operation: apply_patch" in rendered
    assert "*** Begin Patch" in rendered


def test_shape_result_content_error_includes_missing_arg_repair_hint():
    rendered = shape_result_content(
        {
            "tool_name": "capability_help",
            "ok": False,
            "error": "invalid arguments for tool capability_help: missing topic",
        }
    )
    assert "next valid shape:" in rendered
    assert "- operation: capability_help" in rendered
    assert "topic: <value>" in rendered


def test_shape_result_content_error_repair_hints_for_shell_script_and_apply_patch_empty():
    shell_script = shape_result_content(
        {
            "tool_name": "shell_script",
            "ok": False,
            "summary": "invalid",
            "error": "invalid arguments for tool shell_script: script must be a non-empty string",
        }
    )
    assert "next valid shape:" in shell_script
    assert "operation: shell_script" in shell_script

    patch = shape_result_content(
        {
            "tool_name": "apply_patch",
            "ok": False,
            "summary": "invalid",
            "error": "invalid arguments for tool apply_patch: patch must be a non-empty string",
        }
    )
    assert "next valid shape:" in patch
    assert "*** Begin Patch" in patch


def test_shape_result_content_error_repair_hints_for_shell_cwd_and_capability_help_topic():
    shell_cwd = shape_result_content(
        {
            "tool_name": "shell",
            "ok": False,
            "summary": "invalid",
            "error": "invalid arguments for tool shell: cwd must be a string",
        }
    )
    assert "cwd: \".\"" in shell_cwd

    cap_help = shape_result_content(
        {
            "tool_name": "capability_help",
            "ok": False,
            "summary": "invalid",
            "error": "invalid arguments for tool capability_help: topic must be a non-empty string",
        }
    )
    assert "topic: core" in cap_help


# --- render_search_success fenced fallback (no parseable excerpt blocks) ---

def test_render_search_success_falls_back_to_fenced_when_content_not_parseable():
    result = {
        "summary": "1 match",
        "content": "not:a:valid:rg:line",
        "matches": None,
    }
    out = render_search_success(result, status="ok", tool_name="search")
    assert "[ok] search: 1 match" in out
    assert "```" in out


def test_render_search_success_empty_content_returns_summary_only():
    result = {"summary": "no results", "content": ""}
    out = render_search_success(result, status="ok", tool_name="search")
    assert out == "[ok] search: no results"


# --- _parse_search_match branches ---

def test_parse_search_match_returns_none_for_non_string():
    assert _parse_search_match(42) is None


def test_parse_search_match_returns_none_when_no_colon_separator():
    assert _parse_search_match("nodivider") is None


def test_parse_search_match_returns_none_when_line_number_not_digit():
    assert _parse_search_match("path:notanumber:text") is None


def test_parse_search_match_returns_none_for_empty_path():
    assert _parse_search_match(":1:text") is None


# --- render_search_excerpt_blocks with unparseable match bails early ---

def test_render_search_excerpt_blocks_bails_on_unparseable_match():
    result = {"matches": ["not-a-valid-match-line"]}
    assert render_search_excerpt_blocks(result) == []


def test_parse_search_match_returns_none_when_rest_has_no_second_colon():
    # "path:text" — has one colon so sep branch passes, but rest has no second colon
    assert _parse_search_match("path:justtext") is None


def test_render_fenced_output_includes_optional_metadata_and_expands_fence():
    rendered = render_fenced_output(
        content="```\ninside\n```",
        kind="result",
        source="space name",
        path="x y.py",
        line_start=2,
        line_end=4,
        block_id="ib_custom",
        status="done",
    )

    assert rendered.startswith(
        '````text toas-output kind=result source="space name" potency=inert '
        'path="x y.py" line_start=2 line_end=4 block_id=ib_custom status=done\n'
    )
    assert rendered.endswith("\n````")


def test_make_relative_covers_file_base_dir_and_error_fallback(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.rendering.os.path.relpath", lambda path, base: f"rel:{path}:{base}")
    monkeypatch.setattr("toas.tools_cluster.rendering.os.path.isfile", lambda base: base.endswith(".txt"))
    assert _make_relative("x/y.txt", "/base/file.txt") == "rel:x/y.txt:/base"
    assert _make_relative("x/y.txt", "/base/dir") == "rel:x/y.txt:/base/dir"
    assert _make_relative("x/y.txt", None) == "x/y.txt"
    assert _make_relative(None, "/base/dir") is None

    def raise_value_error(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr("toas.tools_cluster.rendering.os.path.relpath", raise_value_error)
    assert _make_relative("x/y.txt", "/base/dir") == "x/y.txt"


def test_render_search_excerpt_blocks_handles_empty_and_all_invalid_inputs(monkeypatch):
    assert render_search_excerpt_blocks({"matches": []}) == []
    assert render_search_excerpt_blocks({"content": ""}) == []
    assert render_search_excerpt_blocks({"matches": [123]}) == []

    monkeypatch.setattr("toas.tools_cluster.rendering._parse_search_match", lambda _raw: None)
    assert render_search_excerpt_blocks({"matches": ["a:1:x"]}) == []

    class TruthyEmptyList(list):
        def __bool__(self):
            return True

        def __iter__(self):
            return iter(())

    assert render_search_excerpt_blocks({"matches": TruthyEmptyList()}) == []
