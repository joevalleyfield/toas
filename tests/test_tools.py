from pathlib import Path

import pytest

from toas.tools import REGISTRY, execute_call, execute_plan, get_tool, shape_result_content, validate_call


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
    with pytest.raises(RuntimeError, match="tool shell disallows command: python"):
        execute_call({"tool_name": "shell", "args": {"argv": ["python", "-V"]}})


def test_shell_tool_rejects_cwd_outside_workspace():
    with pytest.raises(RuntimeError, match="tool shell disallows cwd outside workspace"):
        execute_call({"tool_name": "shell", "args": {"argv": ["pwd"], "cwd": "../.."}})


def test_shell_tool_rejects_bad_timeout():
    with pytest.raises(RuntimeError, match="timeout_s must be an int between 1 and 30"):
        execute_call({"tool_name": "shell", "args": {"argv": ["pwd"], "timeout_s": 0}})


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
