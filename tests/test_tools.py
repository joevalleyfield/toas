from pathlib import Path

import pytest

import toas.tools as tools_module
from toas.procedures import ProcedureAsset
from toas.tools import (
    REGISTRY,
    _shell_launcher_argv,
    execute_call,
    execute_plan,
    execute_shell_call,
    get_tool,
    run_user_shell,
    shape_result_content,
    shell_allow_policy,
    validate_call,
    workspace_policy,
)
from toas.tools_cluster.rendering import stable_import_block_id


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
    assert "code_survey" in REGISTRY
    assert "replace_range" in REGISTRY
    assert "replace_block" in REGISTRY
    assert "apply_patch" in REGISTRY
    assert "procedure" in REGISTRY


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


def test_phase0_contract_core_tool_required_args_are_stable():
    assert REGISTRY["read_file"].required_args == ("path",)
    assert REGISTRY["search"].required_args == ("query",)
    assert REGISTRY["replace_block"].required_args == ("path", "search_block", "replacement_block")
    assert REGISTRY["apply_patch"].required_args == ("patch",)
    assert REGISTRY["code_survey"].required_args == ()
    assert REGISTRY["shell"].required_args == ("argv",)
    assert REGISTRY["shell_script"].required_args == ("script",)


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


def test_capture_task_thread_tool_routes_args(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    captured: dict[str, object] = {}

    def fake_route_and_capture(**kwargs):
        captured.update(kwargs)
        return {"tool_name": "capture_task_thread", "ok": True, "summary": "captured"}

    monkeypatch.setattr("toas.tasks.route_and_capture", fake_route_and_capture)

    result = execute_call(
        {
            "tool_name": "capture_task_thread",
            "args": {
                "title": "Need follow-up",
                "kind": "todo",
                "evidence": "line one",
                "blocks_progress": True,
                "active_task_id": 12,
                "scope_hint": "micro",
                "capture_id": "cap-1",
            },
        }
    )

    assert result["ok"] is True
    assert captured == {
        "workspace_root": tmp_path.resolve(),
        "title": "Need follow-up",
        "kind": "todo",
        "evidence": "line one",
        "blocks_progress": True,
        "active_task_id": "12",
        "scope_hint": "micro",
        "capture_id": "cap-1",
    }


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
    ) == (
        "[OK] shell: exit=0\n"
        "stdout:\n"
        "```text toas-output kind=stdout source=tool.shell potency=inert\n"
        "hello\n"
        "```"
    )


def test_shape_result_content_formats_shell_error_output():
    assert shape_result_content(
        {
            "tool_name": "shell",
            "ok": False,
            "summary": "exit=1",
            "stdout": "",
            "stderr": "command not found: nope",
        }
    ) == (
        "[ERROR] shell: exit=1\n"
        "stderr:\n"
        "```text toas-output kind=stderr source=tool.shell potency=inert\n"
        "command not found: nope\n"
        "```"
    )


def test_shape_result_content_formats_read_file_output():
    block_id = stable_import_block_id(
        kind="file",
        path="note.txt",
        source="workspace",
        line_start=None,
        line_end=None,
        content="hello\n",
    )
    assert shape_result_content(
        {
            "tool_name": "read_file",
            "ok": True,
            "summary": "note.txt",
            "path": "note.txt",
            "content": "hello\n",
        }
    ) == (
        "[OK] read_file: note.txt\n"
        f"```text toas-output kind=file source=workspace potency=inert path=note.txt block_id={block_id}\n"
        "hello\n"
        "```"
    )


def test_shape_result_content_formats_search_output():
    result = shape_result_content(
        {
            "tool_name": "search",
            "ok": True,
            "summary": "2 matches",
            "content": "a.txt:1:alpha\nb.txt:2:alpha",
        }
    )
    # New grouped format
    assert "[OK] search: 2 matches" in result
    assert "a.txt" in result
    assert "    1: alpha" in result
    assert "b.txt" in result
    assert "    2: alpha" in result
    # Ensure it's a single block (starts with ``` and ends with ```)
    assert result.count("```") == 2


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
    assert result["newline_style"] == "lf"
    assert (tmp_path / "notes" / "a.txt").read_text(encoding="utf-8") == "hello\n"

    execute_call(
        {
            "tool_name": "write_file",
            "args": {"path": "notes/a.txt", "content": "bye\n"},
        }
    )
    assert (tmp_path / "notes" / "a.txt").read_text(encoding="utf-8") == "bye\n"


def test_write_file_tool_uses_configured_crlf_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "toas.toml").write_text('[tool_writes]\nnewline_style = "crlf"\n', encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "write_file",
            "args": {"path": "notes/a.txt", "content": "hello\nbye\n"},
        }
    )

    assert result["ok"] is True
    assert result["newline_style"] == "crlf"
    with (tmp_path / "notes" / "a.txt").open("r", encoding="utf-8", newline="") as handle:
        assert handle.read() == "hello\r\nbye\r\n"


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


def test_procedure_tool_dry_run_returns_summary():
    result = execute_call({"tool_name": "procedure", "args": {"name": "repo_discovery_triage_v1", "dry_run": True}})
    assert result["ok"] is True
    assert result["procedure"] == "repo_discovery_triage_v1"
    assert "dry-run" in result["summary"]
    assert "plan:" in result["content"]


def test_procedure_tool_executes_loaded_plan(monkeypatch):
    monkeypatch.setattr(
        "toas.tools.load_procedure",
        lambda name, params=None: ProcedureAsset(
            name=name,
            description="test procedure",
            plan=[{"tool_name": "echo", "args": {"text": "hello"}}],
        ),
    )
    result = execute_call({"tool_name": "procedure", "args": {"name": "test_proc"}})
    assert result["ok"] is True
    assert result["procedure"] == "test_proc"
    assert result["results"][0]["tool_name"] == "echo"
    assert result["results"][0]["summary"] == "hello"
    assert "--- Step 1 ---" in result["content"]


def test_procedure_tool_forwards_arguments(monkeypatch):
    seen = {}

    def _fake_load(name, params=None):
        seen["name"] = name
        seen["params"] = params
        return ProcedureAsset(
            name=name,
            description="test procedure",
            plan=[{"tool_name": "echo", "args": {"text": "ok"}}],
        )

    monkeypatch.setattr("toas.tools.load_procedure", _fake_load)
    result = execute_call(
        {"tool_name": "procedure", "args": {"name": "test_proc", "arguments": {"query": "needle"}}}
    )
    assert result["ok"] is True
    assert seen == {"name": "test_proc", "params": {"query": "needle"}}


def test_procedure_tool_reports_failed_step_and_renders_content(monkeypatch):
    monkeypatch.setattr(
        "toas.tools.load_procedure",
        lambda name, params=None: ProcedureAsset(
            name=name,
            description="test procedure",
            plan=[{"tool_name": "missing_tool", "args": {}}],
        ),
    )
    result = execute_call({"tool_name": "procedure", "args": {"name": "test_proc"}})
    assert result["ok"] is False
    assert result["results"][0]["ok"] is False
    assert "unknown tool: missing_tool" in result["content"]


def test_workspace_policy_and_workspace_path_modes(tmp_path, monkeypatch):
    root = tmp_path / "root"
    other = tmp_path / "other"
    root.mkdir()
    other.mkdir()
    monkeypatch.chdir(root)
    assert tools_module._workspace_path(".") == root.resolve()
    with pytest.raises(RuntimeError, match="outside workspace"):
        tools_module._workspace_path(str(other))
    with workspace_policy(mode="unbounded"):
        assert tools_module._workspace_path(str(other)) == other.resolve()
    with workspace_policy(roots=[str(root), str(other)]):
        assert tools_module._workspace_path(str(other)) == other.resolve()


def test_workspace_policy_base_anchors_relative_paths(tmp_path, monkeypatch):
    process_root = tmp_path / "process-root"
    command_root = tmp_path / "command-root"
    child = command_root / "child"
    process_root.mkdir()
    child.mkdir(parents=True)
    monkeypatch.chdir(process_root)

    with tools_module.workspace_policy(base=str(command_root)):
        assert tools_module._workspace_path(".") == command_root.resolve()
        assert tools_module._workspace_path("child") == child.resolve()


def test_shell_allow_policy_override_and_restore():
    baseline = tools_module._effective_shell_allowed()
    with shell_allow_policy(allowed_commands=("echo", "prefix:py")):
        effective = tools_module._effective_shell_allowed()
        assert "echo" in effective
        assert "prefix:py" in effective
        assert "python" not in effective
    restored = tools_module._effective_shell_allowed()
    assert restored == baseline


def test_procedure_tool_rejects_non_mapping_arguments():
    with pytest.raises(RuntimeError, match="arguments must be a dictionary"):
        execute_call({"tool_name": "procedure", "args": {"name": "repo_discovery_triage_v1", "arguments": "bad"}})


def test_capability_help_tool_normalizes_close_topic_typo():
    result = execute_call({"tool_name": "capability_help", "args": {"topic": "capaility_help"}})
    assert result["ok"] is True
    assert result["topic"] == "capability_help"
    assert result["tools"] == ["capability_help"]
    assert "normalized from topic: capaility_help" in result["content"]


def test_capability_help_tool_errors_on_unknown_topic():
    with pytest.raises(RuntimeError, match="unknown capability_help topic"):
        execute_call({"tool_name": "capability_help", "args": {"topic": "missing"}})


def test_capability_help_alias_tools_expands_to_all_registered_tools():
    result = execute_call({"tool_name": "capability_help", "args": {"topic": "tools"}})

    assert result["ok"] is True
    assert result["topic"] == "all"
    assert result["tools"] == sorted(REGISTRY)
    assert "normalized from topic: tools" in result["content"]


def test_capability_help_rejects_empty_topic():
    with pytest.raises(RuntimeError, match="topic must be a non-empty string"):
        execute_call({"tool_name": "capability_help", "args": {"topic": "   "}})


def test_shell_tool_runs_allowed_command(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
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
    assert result["argv"][2] == "echo hi | head -1"
    assert result["argv"][:2] in (["sh", "-lc"], ["bash", "-lc"])
    assert result["stdout"] == "hi"


def test_shell_script_tool_rejects_disallowed_leading_command():
    with pytest.raises(RuntimeError, match="tool shell_script disallows command: python .*override needed"):
        execute_call({"tool_name": "shell_script", "args": {"script": "python -V"}})


def test_shell_script_tool_rejects_disallowed_segmented_command():
    with shell_allow_policy(allowed_commands=("echo",)):
        with pytest.raises(RuntimeError, match="tool shell_script disallows command: head .*override needed"):
            execute_call({"tool_name": "shell_script", "args": {"script": "echo hi | head -1"}})


def test_user_shell_allows_unrestricted_command(fake_shell_subprocess):
    content = run_user_shell(["python", "-V"])

    assert content["tool_name"] == "shell"
    assert content["argv"] == ["python", "-V"]
    assert content["exit_code"] == 0


def test_user_shell_allows_cwd_outside_workspace(fake_shell_subprocess):
    content = run_user_shell(["pwd"], cwd="/")
    expected_root = str(Path("/").resolve())

    assert content["tool_name"] == "shell"
    # Validate the cwd was resolved correctly through the call chain
    call_kwargs = fake_shell_subprocess.call_args.kwargs
    assert str(call_kwargs["cwd"]) == expected_root


def test_user_shell_allows_empty_string_argument(fake_shell_subprocess):
    content = run_user_shell(["printf", "%s", "", "ok"])

    assert content["tool_name"] == "shell"
    assert content["ok"] is True
    assert content["argv"] == ["printf", "%s", "", "ok"]


def test_user_shell_reports_needs_shell_for_operator_tokens():
    content = run_user_shell(["find", ".", "-type", "f", "|", "head", "-5"])

    assert content["tool_name"] == "shell"
    assert content["ok"] is False
    assert content["summary"] == "needs shell"
    assert "operator '|'" in content["stderr"]
    assert ("sh -lc" in content["stderr"]) or ("bash -lc" in content["stderr"])


def test_shell_launcher_argv_uses_cmd_on_windows(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr("toas.tools_cluster.shell_ops.shutil.which", lambda name: None)
    assert _shell_launcher_argv("echo hi") == ["cmd.exe", "/d", "/s", "/c", "echo hi"]


def test_shell_launcher_argv_prefers_bash_on_windows(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.shutil.which",
        lambda name: "C:/Git/bin/bash.exe" if name == "bash" else None,
    )
    assert _shell_launcher_argv("echo hi") == ["bash", "-lc", "echo hi"]


def test_shell_launcher_argv_uses_sh_when_bash_missing_on_windows(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.shutil.which",
        lambda name: "C:/msys64/usr/bin/sh.exe" if name == "sh" else None,
    )
    assert _shell_launcher_argv("echo hi") == ["sh", "-lc", "echo hi"]


def test_shell_launcher_argv_uses_sh_on_non_windows(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "linux")
    assert _shell_launcher_argv("echo hi") == ["sh", "-lc", "echo hi"]


def test_user_shell_auto_executes_with_shell_when_command_needs_shell(fake_shell_subprocess):
    content = run_user_shell(
        ["find", ".", "-type", "f", "|", "head", "-1"],
        command="find . -type f | head -1",
    )

    assert content["tool_name"] == "shell"
    assert content["ok"] is True
    assert content["argv"][2] == "find . -type f | head -1"
    assert content["argv"][:2] in (["sh", "-lc"], ["bash", "-lc"])
    assert content["exit_code"] == 0
    assert content["stdout"]


def test_user_shell_needs_shell_hint_preserves_escaped_grouping(fake_shell_subprocess):
    content = run_user_shell(
        ["find", ".", "-type", "f", "(", "-name", "*.py", ")", "|", "head", "-1"],
        command=r"find . -type f \( -name \"*.py\" \) | head -1",
    )

    assert content["tool_name"] == "shell"
    assert content["ok"] is True
    assert content["argv"][2] == r"find . -type f \( -name \"*.py\" \) | head -1"
    assert content["argv"][:2] in (["sh", "-lc"], ["bash", "-lc"])


def test_execute_shell_call_user_accepts_command_without_argv(fake_shell_subprocess):
    result = execute_shell_call(
        {"command": "printf hi"},
        context="user",
        base_cwd=".",
    )

    assert result["tool_name"] == "shell"
    assert result["ok"] is True
    assert result["argv"] == ["printf", "hi"]


def test_execute_shell_call_user_command_with_shell_operator_without_argv(fake_shell_subprocess):
    result = execute_shell_call(
        {"command": "printf 'alpha\\n' | head -1"},
        context="user",
        base_cwd=".",
    )

    assert result["tool_name"] == "shell"
    assert result["ok"] is True
    assert result["argv"][2] == "printf 'alpha\\n' | head -1"
    assert result["argv"][:2] in (["sh", "-lc"], ["bash", "-lc"])


def test_execute_shell_call_user_forces_streaming_override(monkeypatch):
    seen = {}

    def _fake_run_subprocess(argv, *, cwd, timeout_s, env=None, stream_stdout_override=None):
        seen["argv"] = argv
        seen["cwd"] = str(cwd)
        seen["timeout_s"] = timeout_s
        seen["stream_stdout_override"] = stream_stdout_override
        return {
            "tool_name": "shell",
            "ok": True,
            "summary": "exit=0",
            "argv": argv,
            "cwd": str(cwd),
            "exit_code": 0,
            "stdout": "ok",
            "stderr": "",
            "content": "exit=0\nstdout:\nok",
        }

    monkeypatch.setattr("toas.tools_cluster.shell_ops.run_subprocess", _fake_run_subprocess)
    result = execute_shell_call({"command": "printf ok"}, context="user", base_cwd=".")
    assert result["ok"] is True
    assert seen["stream_stdout_override"] is True


def test_execute_shell_call_assistant_does_not_force_streaming_override(monkeypatch):
    seen = {}

    def _fake_run_subprocess(argv, *, cwd, timeout_s, env=None, stream_stdout_override=None):
        seen["stream_stdout_override"] = stream_stdout_override
        return {
            "tool_name": "shell",
            "ok": True,
            "summary": "exit=0",
            "argv": argv,
            "cwd": str(cwd),
            "exit_code": 0,
            "stdout": "ok",
            "stderr": "",
            "content": "exit=0\nstdout:\nok",
        }

    monkeypatch.setattr("toas.tools_cluster.shell_ops.run_subprocess", _fake_run_subprocess)
    result = execute_shell_call({"argv": ["pwd"]}, context="assistant")
    assert result["ok"] is True
    assert seen["stream_stdout_override"] is None


def test_read_file_tool_reads_workspace_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")

    out = execute_call({"tool_name": "read_file", "args": {"path": "note.txt"}})
    assert out == {
        "tool_name": "read_file",
        "ok": True,
        "summary": "note.txt",
        "path": "note.txt",
        "content": "hello\n",
        "display_content": "hello\n",
        "number_lines": False,
    }


def test_read_file_tool_rejects_path_outside_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="tool disallows path outside workspace"):
        execute_call({"tool_name": "read_file", "args": {"path": "../note.txt"}})


def test_read_file_tool_rejects_non_bool_number_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="number_lines must be a bool"):
        execute_call({"tool_name": "read_file", "args": {"path": "note.txt", "number_lines": "yes"}})


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


def test_replace_block_defaults_to_trailing_newline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    execute_call(
        {
            "tool_name": "replace_block",
            "args": {
                "path": "note.txt",
                "search_block": "two\n",
                "replacement_block": "TWO",
            },
        }
    )

    assert path.read_text(encoding="utf-8") == "one\nTWO\nthree\n"


def test_replace_block_can_disable_trailing_newline_normalization(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    execute_call(
        {
            "tool_name": "replace_block",
            "args": {
                "path": "note.txt",
                "search_block": "two\n",
                "replacement_block": "TWO",
                "ensure_trailing_newline": False,
            },
        }
    )

    assert path.read_text(encoding="utf-8") == "one\nTWOthree\n"


def test_replace_block_rejects_non_bool_newline_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("a\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="ensure_trailing_newline must be boolean"):
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "note.txt",
                    "search_block": "a\n",
                    "replacement_block": "b",
                    "ensure_trailing_newline": "yes",
                },
            }
        )


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
    assert "best equal-length region:" in msg


def test_replace_block_missing_includes_best_window_diff_for_high_similarity(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as excinfo:
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "note.txt",
                    "search_block": "alpha\nbetX\ngamma\n",
                    "replacement_block": "unused\n",
                    "match_mode": "strict",
                },
            }
        )
    msg = str(excinfo.value)
    assert "best equal-length region:" in msg
    assert "best-window diff:" in msg
    assert "--- search_block" in msg
    assert "+++ file_window" in msg


def test_replace_block_missing_preserves_first_line_indentation_in_best_window_diff(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("    alpha\n    beta\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as excinfo:
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "note.txt",
                    "search_block": "    alpha\n      beta\n",
                    "replacement_block": "unused\n",
                    "match_mode": "strict",
                },
            }
        )

    msg = str(excinfo.value)
    assert "best-window diff:" in msg
    assert "     alpha" in msg
    assert "-      beta" in msg
    assert "+    beta" in msg


def test_replace_block_missing_omits_best_window_diff_for_low_similarity(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as excinfo:
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "note.txt",
                    "search_block": "ZZZZ\nYYYY\nXXXX\n",
                    "replacement_block": "unused\n",
                    "match_mode": "strict",
                },
            }
        )
    msg = str(excinfo.value)
    assert "best equal-length region:" in msg
    assert "best-window diff omitted: similarity below threshold 0.55" in msg


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
                "match_mode": "lax",
            },
        }
    )

    assert result["ok"] is True
    assert path.read_text(encoding="utf-8") == "if True:\n  print('y')\n"


def test_replace_block_default_mode_tolerates_blank_line_whitespace_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("a\n \t \nb\n", encoding="utf-8")

    result = execute_call(
        {
            "tool_name": "replace_block",
            "args": {
                "path": "snippet.txt",
                "search_block": "a\n   \nb\n",
                "replacement_block": "a\n\nB\n",
            },
        }
    )
    assert result["ok"] is True
    assert path.read_text(encoding="utf-8") == "a\n\nB\n"


def test_replace_block_strict_mode_requires_exact_whitespace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("a\n\nb\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="tool replace_block found no matches"):
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "snippet.txt",
                    "search_block": "a\n   \nb\n",
                    "replacement_block": "a\n\nB\n",
                    "match_mode": "strict",
                },
            }
        )


def test_replace_block_rejects_invalid_match_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "snippet.txt"
    path.write_text("x\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="match_mode must be one of strict, default, lax"):
        execute_call(
            {
                "tool_name": "replace_block",
                "args": {
                    "path": "snippet.txt",
                    "search_block": "x\n",
                    "replacement_block": "y\n",
                    "match_mode": "nope",
                },
            }
        )


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


def test_apply_patch_tool_updates_file_with_multiple_context_hunks_in_single_update(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("alpha\nbeta\ngamma\ndelta\nepsilon\n", encoding="utf-8")

    patch = (
        "*** Begin Patch\n"
        "*** Update File: note.txt\n"
        "@@\n"
        " alpha\n"
        "-beta\n"
        "+BETA\n"
        " gamma\n"
        "@@\n"
        " gamma\n"
        "-delta\n"
        "+DELTA\n"
        " epsilon\n"
        "*** End Patch\n"
    )
    result = execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})

    assert result["ok"] is True
    assert result["hunks_applied"] == 1
    assert result["files_touched"] == ["note.txt"]
    assert path.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\nDELTA\nepsilon\n"


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
    with pytest.raises(RuntimeError, match="context mismatch") as excinfo:
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})
    msg = str(excinfo.value)
    assert "chunk:" in msg
    assert "-delta" in msg


def test_apply_patch_tool_fails_when_later_context_hunk_mismatches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("alpha\nbeta\ngamma\ndelta\nepsilon\n", encoding="utf-8")

    patch = (
        "*** Begin Patch\n"
        "*** Update File: note.txt\n"
        "@@\n"
        " alpha\n"
        "-beta\n"
        "+BETA\n"
        " gamma\n"
        "@@\n"
        " gamma\n"
        "-not-delta\n"
        "+DELTA\n"
        " epsilon\n"
        "*** End Patch\n"
    )
    with pytest.raises(RuntimeError, match="context mismatch"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})
    assert path.read_text(encoding="utf-8") == "alpha\nbeta\ngamma\ndelta\nepsilon\n"


def test_apply_patch_tool_rejects_context_free_update_chunk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "note.txt"
    path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    patch = (
        "*** Begin Patch\n"
        "*** Update File: note.txt\n"
        "@@\n"
        "+inserted without context\n"
        "*** End Patch\n"
    )
    with pytest.raises(RuntimeError, match="unsupported context-free insertion") as excinfo:
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})
    msg = str(excinfo.value)
    assert "chunk:" in msg
    assert "+inserted without context" in msg
    assert path.read_text(encoding="utf-8") == "alpha\nbeta\ngamma\n"


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


def test_apply_patch_rejects_patch_without_begin_marker():
    patch = "*** Update File: note.txt\n@@\n-a\n+b\n*** End Patch\n"
    with pytest.raises(RuntimeError, match="patch must start with '\\*\\*\\* Begin Patch'"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


def test_apply_patch_rejects_patch_without_end_marker():
    patch = "*** Begin Patch\n*** Update File: note.txt\n@@\n-a\n+b\n"
    with pytest.raises(RuntimeError, match="patch must end with '\\*\\*\\* End Patch'"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


def test_apply_patch_rejects_add_hunk_with_non_plus_line():
    patch = "*** Begin Patch\n*** Add File: note.txt\nline\n*** End Patch\n"
    with pytest.raises(RuntimeError, match="invalid apply_patch add hunk: expected '\\+' lines only"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


def test_apply_patch_rejects_update_hunk_with_invalid_line_prefix():
    patch = "*** Begin Patch\n*** Update File: note.txt\n@@\n!bad\n*** End Patch\n"
    with pytest.raises(RuntimeError, match="invalid apply_patch update hunk: expected context/add/remove lines"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


def test_apply_patch_rejects_unknown_hunk_header():
    patch = "*** Begin Patch\n*** Weird: note.txt\n*** End Patch\n"
    with pytest.raises(RuntimeError, match="invalid apply_patch hunk header"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


def test_apply_patch_rejects_empty_hunk_set():
    patch = "*** Begin Patch\n*** End Patch\n"
    with pytest.raises(RuntimeError, match="patch must include at least one hunk"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


def test_apply_patch_rejects_delete_directory_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a_dir").mkdir()
    patch = "*** Begin Patch\n*** Delete File: a_dir\n*** End Patch\n"
    with pytest.raises(RuntimeError, match="path is a directory: a_dir"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


def test_apply_patch_move_fails_when_target_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "source.txt").write_text("old\n", encoding="utf-8")
    (tmp_path / "target.txt").write_text("exists\n", encoding="utf-8")
    patch = (
        "*** Begin Patch\n"
        "*** Update File: source.txt\n"
        "*** Move to: target.txt\n"
        "@@\n"
        "-old\n"
        "+new\n"
        "*** End Patch\n"
    )
    with pytest.raises(RuntimeError, match="tool apply_patch move failed: target exists: target.txt"):
        execute_call({"tool_name": "apply_patch", "args": {"patch": patch}})


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


def test_code_survey_reports_ranked_file_function_and_class_sizes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text(
        "def short():\n"
        "    return 1\n\n"
        "def longer():\n"
        "    x = 1\n"
        "    y = 2\n"
        "    return x + y\n",
        encoding="utf-8",
    )
    (pkg / "b.py").write_text(
        "class Big:\n"
        "    def one(self):\n"
        "        return 1\n\n"
        "    def two(self):\n"
        "        a = 1\n"
        "        b = 2\n"
        "        return a + b\n",
        encoding="utf-8",
    )

    result = execute_call({"tool_name": "code_survey", "args": {"path": "pkg", "top_n": 3}})

    assert result["ok"] is True
    assert result["tool_name"] == "code_survey"
    assert result["files_top"][0]["path"].replace("\\", "/") in {"pkg/a.py", "pkg/b.py"}
    assert any(item["name"] == "longer" for item in result["functions_top"])
    assert any(item["name"] == "Big" for item in result["classes_top"])
    assert "top files by lines:" in result["content"]
    assert "top functions by lines:" in result["content"]
    assert "top classes by lines:" in result["content"]


def test_code_survey_rejects_invalid_top_n():
    with pytest.raises(RuntimeError, match="top_n must be an int between 1 and 200"):
        execute_call({"tool_name": "code_survey", "args": {"top_n": 0}})


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


def test_procedure_validation_errors():
    from toas.tools import _run_procedure

    # name must be a non-empty string
    with pytest.raises(RuntimeError, match="name must be a non-empty string"):
        _run_procedure({"name": ""})

    with pytest.raises(RuntimeError, match="name must be a non-empty string"):
        _run_procedure({"name": 123})

    # arguments must be a dictionary
    with pytest.raises(RuntimeError, match="arguments must be a dictionary"):
        _run_procedure({"name": "x", "arguments": "not-a-dict"})


def test_normalize_indent_validation():
    from toas.tools import _normalize_indent

    # None returns default
    assert _normalize_indent(None, tool_name="test", arg_name="indent") == ""

    # negative int raises
    with pytest.raises(RuntimeError, match="must be a non-negative int"):
        _normalize_indent(-1, tool_name="test", arg_name="indent")

    # non-int non-string raises
    with pytest.raises(RuntimeError, match="must be an int or a string"):
        _normalize_indent(1.5, tool_name="test", arg_name="indent")

    # valid int
    assert _normalize_indent(2, tool_name="test", arg_name="indent") == "  "

    # valid string
    assert _normalize_indent("\t", tool_name="test", arg_name="indent") == "\t"


def test_apply_indent_edge_cases():
    from toas.tools import _apply_indent

    # empty text
    assert _apply_indent("", "  ") == ""

    # empty indent
    assert _apply_indent("hello", "") == "hello"

    # normal case
    result = _apply_indent("a\nb\n", "  ")
    assert result == "  a\n  b\n"

    # blank lines preserved
    result = _apply_indent("a\n\nb\n", "  ")
    assert result == "  a\n\n  b\n"


def test_build_env_with_overrides():
    from toas.tools import _build_env_with_overrides

    # None returns None
    assert _build_env_with_overrides(None) is None

    # empty dict returns None
    assert _build_env_with_overrides({}) is None

    # with values
    result = _build_env_with_overrides({"FOO": "bar"})
    assert result is not None
    assert result.get("FOO") == "bar"


def test_resolve_workspace_roots_empty(tmp_path, monkeypatch):
    from toas.tools import _resolve_workspace_roots

    monkeypatch.chdir(tmp_path)
    result = _resolve_workspace_roots(None)
    assert result == [tmp_path.resolve()]

    result = _resolve_workspace_roots([])
    assert result == [tmp_path.resolve()]
