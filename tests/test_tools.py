from pathlib import Path

import pytest

from toas.tools import REGISTRY, execute_call, execute_plan, get_tool, run_user_shell, shape_result_content, validate_call


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
    assert "read_file" in REGISTRY
    assert "search" in REGISTRY
    assert "replace_block" in REGISTRY


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


def test_shape_result_content_formats_canonical_result_text():
    assert shape_result_content({"tool_name": "echo", "ok": True, "summary": "hi"}) == "[OK] echo: hi"
    assert (
        shape_result_content({"tool_name": "echo", "ok": False, "error": "bad args"})
        == "[ERROR] echo: bad args"
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


def test_shell_tool_rejects_cwd_outside_workspace():
    with pytest.raises(RuntimeError, match="tool shell disallows cwd outside workspace"):
        execute_call({"tool_name": "shell", "args": {"argv": ["pwd"], "cwd": "../.."}})


def test_shell_tool_rejects_bad_timeout():
    with pytest.raises(RuntimeError, match="timeout_s must be an int between 1 and 30"):
        execute_call({"tool_name": "shell", "args": {"argv": ["pwd"], "timeout_s": 0}})


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
    assert "a.txt:2:beta" in content["content"]
    assert "b.txt:1:beta" in content["content"]
    assert len(content["matches"]) == 2


def test_search_tool_rejects_bad_limit():
    with pytest.raises(RuntimeError, match="limit must be an int between 1 and 200"):
        execute_call({"tool_name": "search", "args": {"query": "x", "limit": 0}})


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
