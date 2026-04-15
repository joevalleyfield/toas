from pathlib import Path

import pytest

from toas.tools import (
    REGISTRY,
    execute_call,
    execute_plan,
    get_tool,
    run_user_shell,
    shape_result_content,
    shell_allow_policy,
    validate_call,
)


def test_get_tool_returns_registered_tool():
    tool = get_tool("echo")

    assert tool.name == "echo"
    assert tool.required_args == ("text",)
    assert tool.runner({"text": "hi"}) == {
        "tool_name": "echo",
        "ok": True,
        "summary": "hi",
        "text": "hi",
    }


def test_registry_contains_echo():
    assert "echo" in REGISTRY
    assert "shell" in REGISTRY
    assert "shell_script" in REGISTRY
    assert "read_file" in REGISTRY
    assert "search" in REGISTRY
    assert "write_file" in REGISTRY
    assert "echo_block" in REGISTRY
    assert "capability_help" in REGISTRY
    assert "get_structure" in REGISTRY
    assert "replace_range" in REGISTRY
    assert "replace_block" in REGISTRY
    assert "apply_patch" in REGISTRY


def test_get_tool_rejects_unknown_tool():
    with pytest.raises(RuntimeError, match="unknown tool: missing"):
        get_tool("missing")


def test_validate_call_returns_tool_and_args():
    tool, args = validate_call({"tool_name": "echo", "args": {"text": "hi"}})

    assert tool.name == "echo"
    assert args == {"text": "hi"}


def test_validate_call_rejects_missing_required_args():
    with pytest.raises(RuntimeError, match="invalid arguments for tool echo: missing text"):
        validate_call({"tool_name": "echo", "args": {}})


def test_execute_call_runs_validated_tool():
    assert execute_call({"tool_name": "echo", "args": {"text": "hi"}}) == {
        "tool_name": "echo",
        "ok": True,
        "summary": "hi",
        "text": "hi",
    }


def test_execute_plan_returns_success_and_error_results():
    assert execute_plan(
        [
            {"tool_name": "echo", "args": {"text": "hi"}},
            {"tool_name": "missing", "args": {}},
        ]
    ) == [
        {"tool_name": "echo", "ok": True, "summary": "hi", "text": "hi"},
        {"tool_name": "missing", "ok": False, "summary": "unknown tool: missing", "error": "unknown tool: missing"},
    ]


def test_execute_plan_preserves_intention_in_results():
    result = execute_plan(
        [
            {"tool_name": "echo", "args": {"text": "hi"}, "intention": "confirm write path"},
        ]
    )
    assert result[0]["intention"] == "confirm write path"


def test_shape_result_content_formats_canonical_result_text():
    assert shape_result_content({"tool_name": "echo", "ok": True, "summary": "hi"}) == "[OK] echo: hi"
    assert (
        shape_result_content({"tool_name": "echo", "ok": False, "error": "bad args"})
        == "[ERROR] echo: bad args"
    )


def test_shape_result_content_includes_intention_when_present():
    assert (
        shape_result_content({"tool_name": "echo", "ok": True, "summary": "hi", "intention": "check connectivity"})
        == "[OK] echo (check connectivity): hi"
    )


def test_shape_result_content_formats_shell_output():
    assert shape_result_content(
        {
            "tool_name": "shell",
            "ok": True,
            "summary": "exit=0",
            "stdout": "hello",
            "stderr": "",
        }
    ) == "[OK] shell: exit=0\nstdout:\nhello"


def test_shape_result_content_formats_shell_error_output():
    assert shape_result_content(
        {
            "tool_name": "shell",
            "ok": False,
            "summary": "exit=1",
            "stdout": "",
            "stderr": "command not found: nope",
        }
    ) == "[ERROR] shell: exit=1\nstderr:\ncommand not found: nope"


def test_shape_result_content_formats_read_file_output():
    assert shape_result_content(
        {
            "tool_name": "read_file",
            "ok": True,
            "summary": "note.txt",
            "path": "note.txt",
            "content": "hello\n",
        }
    ) == "[OK] read_file: note.txt\nhello\n"


def test_shape_result_content_formats_search_output():
    assert shape_result_content(
        {
            "tool_name": "search",
            "ok": True,
            "summary": "2 matches",
            "content": "a.txt:1:alpha\nb.txt:2:alpha",
        }
    ) == "[OK] search: 2 matches\na.txt:1:alpha\nb.txt:2:alpha"


def test_shape_result_content_includes_capability_help_content_block():
    rendered = shape_result_content(
        {
            "tool_name": "capability_help",
            "ok": True,
            "summary": "shell: 1 tool(s)",
            "content": "capability help: shell\n- `shell`: run bounded shell commands inside the workspace",
        }
    )
    assert rendered.startswith("[OK] capability_help: shell: 1 tool(s)\n")
    assert "capability help: shell" in rendered


def test_shape_result_content_formats_replace_block_preview():
    rendered = shape_result_content(
        {
            "tool_name": "replace_block",
            "ok": True,
            "summary": "replaced 1 block",
            "path": "a.txt",
            "changed_line_start": 10,
            "changed_line_end": 12,
            "preview": " 8: keep\n 9: keep\n10: new\n11: new\n12: new\n13: keep",
            "content": "ignored full content",
        }
    )
    assert rendered.startswith("[OK] replace_block: replaced 1 block (a.txt) lines 10-12")
    assert "preview:" in rendered
    assert "10: new" in rendered


def test_write_file_tool_creates_and_overwrites_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = execute_call(
        {
            "tool_name": "write_file",
            "args": {"path": "notes/a.txt", "content": "hello\n"},
        }
    )
    assert result["ok"] is True
    assert result["path"] == "notes/a.txt"
    assert (tmp_path / "notes" / "a.txt").read_text(encoding="utf-8") == "hello\n"

    execute_call(
        {
            "tool_name": "write_file",
            "args": {"path": "notes/a.txt", "content": "bye\n"},
        }
    )
    assert (tmp_path / "notes" / "a.txt").read_text(encoding="utf-8") == "bye\n"


def test_echo_block_tool_reports_line_diagnostics():
    result = execute_call(
        {
            "tool_name": "echo_block",
            "args": {"block": "a\n  b\n"},
        }
    )
    assert result["ok"] is True
    assert result["line_count"] == 2
    assert result["leading_spaces"] == [0, 2]
    assert result["content"] == "a\n  b\n"


def test_capability_help_tool_returns_core_topic_details():
    result = execute_call({"tool_name": "capability_help", "args": {"topic": "core"}})
    assert result["ok"] is True
    assert result["topic"] == "core"
    assert "shell" in result["tools"]
    assert "apply_patch" in result["tools"]
    assert "capability help: core" in result["content"]


def test_capability_help_tool_supports_single_tool_topic():
    result = execute_call({"tool_name": "capability_help", "args": {"topic": "shell_script"}})
    assert result["ok"] is True
    assert result["tools"] == ["shell_script"]
    assert "arguments.script" in result["content"]


def test_capability_help_shell_topic_includes_both_shell_lanes():
    result = execute_call({"tool_name": "capability_help", "args": {"topic": "shell"}})
    assert result["ok"] is True
    assert result["tools"] == ["shell", "shell_script"]
    assert "arguments.argv" in result["content"]
    assert "arguments.script" in result["content"]


def test_capability_help_tool_normalizes_close_topic_typo():
    result = execute_call({"tool_name": "capability_help", "args": {"topic": "capaility_help"}})
    assert result["ok"] is True
    assert result["topic"] == "capability_help"
    assert result["tools"] == ["capability_help"]
    assert "normalized from topic: capaility_help" in result["content"]


def test_capability_help_tool_errors_on_unknown_topic():
    with pytest.raises(RuntimeError, match="unknown capability_help topic"):
        execute_call({"tool_name": "capability_help", "args": {"topic": "missing"}})


def test_shell_tool_runs_allowed_command():
    content = execute_call({"tool_name": "shell", "args": {"argv": ["echo", "hi"]}})

    assert content == {
        "tool_name": "shell",
        "ok": True,
        "summary": "exit=0",
        "argv": ["echo", "hi"],
        "cwd": str(Path.cwd().resolve()),
        "exit_code": 0,
        "stdout": "hi",
        "stderr": "",
        "content": "exit=0\nstdout:\nhi",
    }


def test_shell_tool_rejects_disallowed_command():
    with pytest.raises(RuntimeError, match="tool shell disallows command: python .*override needed"):
        execute_call({"tool_name": "shell", "args": {"argv": ["python", "-V"]}})


def test_shell_tool_accepts_prefix_grant():
    with shell_allow_policy(allowed_commands=("echo", "prefix:py")):
        result = execute_call({"tool_name": "shell", "args": {"argv": ["python", "-V"]}})
    assert result["ok"] is True
    assert result["argv"] == ["python", "-V"]


def test_shell_tool_rejects_cwd_outside_workspace():
    with pytest.raises(RuntimeError, match="tool shell disallows cwd outside workspace"):
        execute_call({"tool_name": "shell", "args": {"argv": ["pwd"], "cwd": "../.."}})


def test_shell_tool_rejects_bad_timeout():
    with pytest.raises(RuntimeError, match="timeout_s must be an int between 1 and 30"):
        execute_call({"tool_name": "shell", "args": {"argv": ["pwd"], "timeout_s": 0}})


def test_shell_script_tool_runs_allowed_script():
    result = execute_call(
        {
            "tool_name": "shell_script",
            "args": {"script": "echo hi | head -1"},
        }
    )
    assert result["tool_name"] == "shell_script"
    assert result["ok"] is True
    assert result["argv"] == ["sh", "-lc", "echo hi | head -1"]
    assert result["stdout"] == "hi"


def test_shell_script_tool_rejects_disallowed_leading_command():
    with pytest.raises(RuntimeError, match="tool shell_script disallows command: python .*override needed"):
        execute_call({"tool_name": "shell_script", "args": {"script": "python -V"}})


def test_shell_script_tool_rejects_disallowed_segmented_command():
    with shell_allow_policy(allowed_commands=("echo",)):
        with pytest.raises(RuntimeError, match="tool shell_script disallows command: head .*override needed"):
            execute_call({"tool_name": "shell_script", "args": {"script": "echo hi | head -1"}})


def test_user_shell_allows_unrestricted_command():
    content = run_user_shell(["python", "-V"])

    assert content["tool_name"] == "shell"
    assert content["argv"] == ["python", "-V"]
    assert content["exit_code"] == 0
    assert "Python " in content["stdout"]


def test_user_shell_allows_cwd_outside_workspace():
    content = run_user_shell(["pwd"], cwd="/")

    assert content["tool_name"] == "shell"
    assert content["cwd"] == "/"
    assert content["exit_code"] == 0
    assert content["stdout"] == "/"


def test_user_shell_reports_needs_shell_for_operator_tokens():
    content = run_user_shell(["find", ".", "-type", "f", "|", "head", "-5"])

    assert content["tool_name"] == "shell"
    assert content["ok"] is False
    assert content["summary"] == "needs shell"
    assert "operator '|'" in content["stderr"]
    assert "sh -lc" in content["stderr"]


def test_user_shell_auto_executes_with_shell_when_command_needs_shell():
    content = run_user_shell(
        ["find", ".", "-type", "f", "|", "head", "-1"],
        command="find . -type f | head -1",
    )

    assert content["tool_name"] == "shell"
    assert content["ok"] is True
    assert content["argv"] == ["sh", "-lc", "find . -type f | head -1"]
    assert content["exit_code"] == 0
    assert content["stdout"]


def test_user_shell_needs_shell_hint_preserves_escaped_grouping():
    content = run_user_shell(
        ["find", ".", "-type", "f", "(", "-name", "*.py", ")", "|", "head", "-1"],
        command=r"find . -type f \( -name \"*.py\" \) | head -1",
    )

    assert content["tool_name"] == "shell"
    assert content["ok"] is True
    assert content["argv"] == ["sh", "-lc", r"find . -type f \( -name \"*.py\" \) | head -1"]


def test_read_file_tool_reads_workspace_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")

    assert execute_call({"tool_name": "read_file", "args": {"path": "note.txt"}}) == {
        "tool_name": "read_file",
        "ok": True,
        "summary": "note.txt",
        "path": "note.txt",
        "content": "hello\n",
    }


def test_read_file_tool_rejects_path_outside_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="tool disallows path outside workspace"):
        execute_call({"tool_name": "read_file", "args": {"path": "../note.txt"}})


def test_search_tool_uses_rg_and_returns_matches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta\ngamma\n", encoding="utf-8")

    content = execute_call({"tool_name": "search", "args": {"query": "beta"}})

    assert content["tool_name"] == "search"
    assert content["ok"] is True
    assert content["summary"] == "2 matches"
    assert content["regex"] is False
    assert "a.txt:2:beta" in content["content"]
    assert "b.txt:1:beta" in content["content"]
    assert len(content["matches"]) == 2


def test_search_tool_literal_default_handles_regex_metacharacters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text('if scenario_set in {"all", "core"}:\n', encoding="utf-8")

    content = execute_call(
        {
            "tool_name": "search",
            "args": {"query": 'if scenario_set in {"all", "core"}:'},
        }
    )

    assert content["ok"] is True
    assert content["summary"] == "1 matches"
    assert content["regex"] is False
    assert 'a.txt:1:if scenario_set in {"all", "core"}:' in content["content"]


def test_search_tool_regex_mode_can_use_regex_syntax(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("label=\"exact_ok\",\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("label=\"json_exact\",\n", encoding="utf-8")

    content = execute_call(
        {
            "tool_name": "search",
            "args": {"query": 'label=".*_ok",', "regex": True},
        }
    )

    assert content["ok"] is True
    assert content["summary"] == "1 matches"
    assert content["regex"] is True
    assert 'a.txt:1:label="exact_ok",' in content["content"]


def test_search_tool_regex_mode_reports_hint_on_invalid_regex(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("x\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="query was treated as regex; set regex=false for literal matching"):
        execute_call(
            {
                "tool_name": "search",
                "args": {"query": "{bad", "regex": True},
            }
        )


def test_search_tool_rejects_bad_limit():
    with pytest.raises(RuntimeError, match="limit must be an int between 1 and 200"):
        execute_call({"tool_name": "search", "args": {"query": "x", "limit": 0}})


def test_search_tool_rejects_non_bool_regex_flag():
    with pytest.raises(RuntimeError, match="regex must be a bool"):
        execute_call({"tool_name": "search", "args": {"query": "x", "regex": "yes"}})


def test_execute_plan_allows_shell_cwd_under_added_workspace_root(tmp_path, monkeypatch):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    monkeypatch.chdir(root_a)

    result = execute_plan(
        [{"tool_name": "shell", "args": {"argv": ["pwd"]}}],
        default_shell_cwd=str(root_b),
        workspace_roots=[str(root_a), str(root_b)],
        workspace_mode="strict",
    )

    assert result[0]["ok"] is True
    assert result[0]["cwd"] == str(root_b)


def test_execute_plan_resolves_relative_shell_cwd_from_command_context(tmp_path, monkeypatch):
    root = tmp_path / "root"
    child = root / "child"
    root.mkdir()
    child.mkdir()
    monkeypatch.chdir(root)

    result = execute_plan(
        [{"tool_name": "shell", "args": {"argv": ["pwd"], "cwd": "."}}],
        default_shell_cwd=str(child),
        workspace_roots=[str(root)],
        workspace_mode="strict",
    )

    assert result[0]["ok"] is True
    assert result[0]["cwd"] == str(child)


def test_execute_plan_resolves_read_file_path_from_command_context(tmp_path, monkeypatch):
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    note = child / "note.txt"
    note.write_text("hello\n", encoding="utf-8")
    monkeypatch.chdir(root)

    result = execute_plan(
        [{"tool_name": "read_file", "args": {"path": "note.txt"}}],
        default_shell_cwd=str(child),
        workspace_roots=[str(root)],
        workspace_mode="strict",
    )

    assert result[0]["ok"] is True
    assert result[0]["path"] == str(note)
    assert result[0]["content"] == "hello\n"


def test_replace_block_tool_replaces_unique_match(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_block",
            "args": {
                "path": "note.txt",
                "search_block": "beta\n",
                "replacement_block": "BETA\n",
            },
        }
    )

    assert result["tool_name"] == "replace_block"
    assert result["ok"] is True
    assert result["replacements"] == 1
    assert result["changed_line_start"] == 2
    assert result["changed_line_end"] == 2
    assert "2: BETA" in (result["preview"] or "")
    assert path.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"


def test_replace_block_tool_fails_when_search_block_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="tool replace_block found no matches"):
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "note.txt",
                    "search_block": "delta\n",
                    "replacement_block": "DELTA\n",
                },
            }
        )


def test_replace_block_tool_missing_includes_divergence_diagnostics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as excinfo:
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "note.txt",
                    "search_block": "alpha\nbetX\ngamma\n",
                    "replacement_block": "alpha\nbeta\ngamma\n",
                },
            }
        )

    msg = str(excinfo.value)
    assert "tool replace_block found no matches" in msg
    assert "closest overlap:" in msg
    assert "expected next:" in msg
    assert "actual next:" in msg


def test_replace_block_tool_fails_on_ambiguous_match_count(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("repeat\nrepeat\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="tool replace_block matched 2 blocks; expected 1"):
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "note.txt",
                    "search_block": "repeat\n",
                    "replacement_block": "done\n",
                },
            }
        )


def test_replace_block_tool_supports_indent_controls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("    foo\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_block",
            "args": {
                "path": "snippet.txt",
                "search_block": "foo\n",
                "replacement_block": "bar\n",
                "search_indent": "    ",
                "replacement_indent": "    ",
            },
        }
    )

    assert result["ok"] is True
    assert path.read_text(encoding="utf-8") == "    bar\n"


def test_replace_block_tool_accepts_int_indent_controls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("    foo\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_block",
            "args": {
                "path": "snippet.txt",
                "search_block": "foo\n",
                "replacement_block": "bar\n",
                "search_indent": 4,
                "replacement_indent": 4,
            },
        }
    )

    assert result["ok"] is True
    assert path.read_text(encoding="utf-8") == "    bar\n"


def test_replace_block_defaults_replacement_indent_to_search_indent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("    foo\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_block",
            "args": {
                "path": "snippet.txt",
                "search_block": "foo\n",
                "replacement_block": "bar\n",
                "search_indent": "    ",
            },
        }
    )

    assert result["ok"] is True
    assert path.read_text(encoding="utf-8") == "    bar\n"


def test_replace_block_whitespace_lax_matching(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("if True:\n    print('x')\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_block",
            "args": {
                "path": "snippet.txt",
                "search_block": "if True:\n  print('x')\n",
                "replacement_block": "if True:\n  print('y')\n",
            },
        }
    )

    assert result["ok"] is True
    assert path.read_text(encoding="utf-8") == "if True:\n  print('y')\n"


def test_replace_block_no_match_includes_effective_indent_hints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("x\n", encoding="utf-8")
    with pytest.raises(RuntimeError) as excinfo:
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "snippet.txt",
                    "search_block": "foo\n",
                    "replacement_block": "bar\n",
                    "search_indent": "    ",
                    "replacement_indent": "  ",
                },
            }
        )
    msg = str(excinfo.value)
    assert "effective search_indent='    '" in msg
    assert "effective replacement_indent='  '" in msg


def test_replace_block_rejects_negative_indent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("x\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="search_indent must be a non-negative int or a string"):
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "snippet.txt",
                    "search_block": "x\n",
                    "replacement_block": "y\n",
                    "search_indent": -1,
                },
            }
        )


def test_apply_patch_tool_updates_file_with_context_hunk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    patch = (
        "*** Begin Patch\n"
        "*** Update File: note.txt\n"
        "@@\n"
        " alpha\n"
        "-beta\n"
        "+BETA\n"
        " gamma\n"
        "*** End Patch\n"
    )
    result = execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})

    assert result["ok"] is True
    assert result["hunks_applied"] == 1
    assert result["files_touched"] == ["note.txt"]
    assert path.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"


def test_apply_patch_tool_fails_on_context_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    patch = (
        "*** Begin Patch\n"
        "*** Update File: note.txt\n"
        "@@\n"
        " alpha\n"
        "-delta\n"
        "+DELTA\n"
        " gamma\n"
        "*** End Patch\n"
    )
    with pytest.raises(RuntimeError, match="context mismatch"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


def test_apply_patch_tool_add_and_delete_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    doomed = tmp_path / "doomed.txt"
    doomed.write_text("bye\n", encoding="utf-8")

    patch = (
        "*** Begin Patch\n"
        "*** Add File: new.txt\n"
        "+hello\n"
        "*** Delete File: doomed.txt\n"
        "*** End Patch\n"
    )
    result = execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})

    assert result["ok"] is True
    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "hello\n"
    assert not doomed.exists()


def test_get_structure_python_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "module.py"
    test_file.write_text(
        "class MyClass:\n    def method_one(self):\n        pass\n\ndef top_level():\n    pass\n",
        encoding="utf-8",
    )

    result = execute_call({"tool_name": "get_structure", "args": {"path": "module.py"}})

    assert result["ok"] is True
    structure = result["structure"]
    assert len(structure) == 3
    assert any(s["kind"] == "class" and s["name"] == "MyClass" for s in structure)
    assert any(s["kind"] == "def" and s["name"] == "method_one" for s in structure)
    assert any(s["kind"] == "def" and s["name"] == "top_level" for s in structure)
    assert structure[0]["name"] == "MyClass"
    assert structure[1]["name"] == "method_one"
    assert structure[2]["name"] == "top_level"


def test_get_structure_python_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (pkg / "b.py").write_text("class B:\n    pass\n", encoding="utf-8")

    result = execute_call({"tool_name": "get_structure", "args": {"path": "pkg"}})
    assert result["ok"] is True
    names = [item["name"] for item in result["structure"]]
    assert "a" in names
    assert "B" in names


def test_replace_range_replaces_target_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_range",
            "args": {
                "path": "test.txt",
                "start_line": 2,
                "end_line": 3,
                "replacement_block": "new_line_2\nnew_line_3\n",
            },
        }
    )

    assert result["ok"] is True
    content = test_file.read_text(encoding="utf-8")
    assert content == "line1\nnew_line_2\nnew_line_3\nline4\n"


def test_replace_range_out_of_bounds(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="beyond file length"):
        execute_call(
            {
                "tool_name": "replace_range",
                "args": {
                    "path": "test.txt",
                    "start_line": 5,
                    "end_line": 6,
                    "replacement_block": "fail",
                },
            }
        )


def test_replace_range_supports_indent_option(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "sample.py"
    test_file.write_text("def f():\n    pass\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_range",
            "args": {
                "path": "sample.py",
                "start_line": 2,
                "end_line": 2,
                "replacement_block": "print('x')\n",
                "indent": "    ",
            },
        }
    )

    assert result["ok"] is True
    content = test_file.read_text(encoding="utf-8")
    assert content == "def f():\n    print('x')\n"


def test_replace_range_accepts_int_indent_option(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "sample.py"
    test_file.write_text("def f():\n    pass\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_range",
            "args": {
                "path": "sample.py",
                "start_line": 2,
                "end_line": 2,
                "replacement_block": "print('x')\n",
                "indent": 4,
            },
        }
    )

    assert result["ok"] is True
    content = test_file.read_text(encoding="utf-8")
    assert content == "def f():\n    print('x')\n"


def test_replace_range_context_checks_match(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_range",
            "args": {
                "path": "test.txt",
                "start_line": 2,
                "end_line": 3,
                "replacement_block": "new2\nnew3\n",
                "context_start": "line2",
                "context_end": "line3",
            },
        }
    )

    assert result["ok"] is True
    assert test_file.read_text(encoding="utf-8") == "line1\nnew2\nnew3\nline4\n"


def test_replace_range_context_start_mismatch_has_numbered_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "test.txt"
    test_file.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc:
        execute_call(
            {
                "tool_name": "replace_range",
                "args": {
                    "path": "test.txt",
                    "start_line": 2,
                    "end_line": 2,
                    "replacement_block": "BETA\n",
                    "context_start": "wrong",
                },
            }
        )
    msg = str(exc.value)
    assert "context_start mismatch" in msg
    assert "2: beta" in msg


def test_replace_range_context_end_mismatch_has_numbered_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "test.txt"
    test_file.write_text("alpha\nbeta\ngamma\ndelta\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc:
        execute_call(
            {
                "tool_name": "replace_range",
                "args": {
                    "path": "test.txt",
                    "start_line": 2,
                    "end_line": 4,
                    "replacement_block": "B\nG\nD\n",
                    "context_end": "wrong",
                },
            }
        )
    msg = str(exc.value)
    assert "context_end mismatch" in msg
    assert "4: delta" in msg
