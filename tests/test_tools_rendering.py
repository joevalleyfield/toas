from toas.tools_rendering import shape_result_content


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
    assert success == "[OK] shell: exit=0\nstdout:\nhello"

    error = shape_result_content(
        {
            "tool_name": "shell_script",
            "ok": False,
            "summary": "exit=1",
            "stdout": "",
            "stderr": "boom",
        }
    )
    assert error == "[ERROR] shell_script: exit=1\nstderr:\nboom"


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
    assert read == "[OK] read_file: a.txt\nhello\n"

    search_with_content = shape_result_content(
        {
            "tool_name": "search",
            "ok": True,
            "summary": "2 matches",
            "content": "a:1:x\nb:2:x",
        }
    )
    assert search_with_content == "[OK] search: 2 matches\na:1:x\nb:2:x"

    search_without_content = shape_result_content(
        {
            "tool_name": "search",
            "ok": True,
            "summary": "0 matches",
            "content": "",
        }
    )
    assert search_without_content == "[OK] search: 0 matches"


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
    assert structure == "[OK] get_structure: 2 symbols\nfunction.a (1-2) m.py\nclass.B (4-8)"

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
    assert with_preview == "[OK] replace_block: replaced 1 (x.py) lines 3-5\npreview:\n3:new\n4:new\n5:new"

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
    assert long_preview.startswith("[OK] replace_block: replaced\npreview:\n")

    content_short = shape_result_content(
        {
            "tool_name": "replace_block",
            "ok": True,
            "summary": "replaced",
            "content": "a\nb",
        }
    )
    assert content_short == "[OK] replace_block: replaced\npreview:\na\nb"

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
