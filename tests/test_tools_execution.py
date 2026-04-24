from toas.tools_execution import adapt_call_for_execution, execute_plan_calls


def test_adapt_call_for_execution_no_default_cwd_returns_original_call():
    call = {"tool_name": "shell", "args": {"argv": ["pwd"]}}
    assert adapt_call_for_execution(call, default_shell_cwd=None, default_shell_env=None) is call


def test_adapt_call_for_execution_shell_sets_default_cwd_and_env_filters_none(tmp_path):
    call = {"tool_name": "shell", "args": {"argv": ["pwd"]}}
    adapted = adapt_call_for_execution(
        call,
        default_shell_cwd=str(tmp_path),
        default_shell_env={"A": "1", "B": None},
    )
    assert adapted is not call
    assert adapted["args"]["cwd"] == str(tmp_path.resolve())
    assert adapted["args"]["env"] == {"A": "1"}


def test_adapt_call_for_execution_shell_resolves_relative_and_absolute_cwd(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    rel = {"tool_name": "shell", "args": {"argv": ["pwd"], "cwd": "sub"}}
    abs_target = tmp_path / "abs"
    abs_call = {"tool_name": "shell", "args": {"argv": ["pwd"], "cwd": str(abs_target)}}

    rel_adapted = adapt_call_for_execution(rel, default_shell_cwd=str(base), default_shell_env=None)
    abs_adapted = adapt_call_for_execution(abs_call, default_shell_cwd=str(base), default_shell_env=None)

    assert rel_adapted["args"]["cwd"] == str((base / "sub").resolve())
    assert abs_adapted["args"]["cwd"] == str(abs_target.resolve())


def test_adapt_call_for_execution_resolves_supported_path_tools(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    for tool_name in ["read_file", "search", "write_file", "get_structure", "code_survey", "replace_range", "replace_block"]:
        call = {"tool_name": tool_name, "args": {"path": "x/y.txt"}}
        adapted = adapt_call_for_execution(call, default_shell_cwd=str(base), default_shell_env=None)
        assert adapted["args"]["path"] == str((base / "x/y.txt").resolve())


def test_adapt_call_for_execution_ignores_unsupported_or_non_string_paths(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    not_supported = {"tool_name": "echo", "args": {"path": "x"}}
    non_string = {"tool_name": "read_file", "args": {"path": 123}}

    not_supported_adapted = adapt_call_for_execution(not_supported, default_shell_cwd=str(base), default_shell_env=None)
    non_string_adapted = adapt_call_for_execution(non_string, default_shell_cwd=str(base), default_shell_env=None)

    assert not_supported_adapted["args"]["path"] == "x"
    assert non_string_adapted["args"]["path"] == 123


def test_execute_plan_calls_success_error_and_intention_projection(tmp_path):
    base = tmp_path / "base"
    base.mkdir()

    seen = []

    def _execute(call):
        seen.append(call)
        if call["tool_name"] == "bad":
            raise RuntimeError("boom")
        return {"tool_name": call["tool_name"], "ok": True, "summary": "ok"}

    plan = [
        {"tool_name": "shell", "args": {"argv": ["pwd"]}, "intention": "inspect cwd"},
        {"tool_name": "read_file", "args": {"path": "a.txt"}},
        {"tool_name": "bad", "args": {}, "intention": "should fail"},
    ]
    results = execute_plan_calls(
        plan,
        execute_call=_execute,
        default_shell_cwd=str(base),
        default_shell_env={"A": "1", "B": None},
    )

    assert seen[0]["args"]["cwd"] == str(base.resolve())
    assert seen[0]["args"]["env"] == {"A": "1"}
    assert seen[1]["args"]["path"] == str((base / "a.txt").resolve())

    assert results[0]["intention"] == "inspect cwd"
    assert results[1]["tool_name"] == "read_file"
    assert results[2] == {
        "tool_name": "bad",
        "ok": False,
        "summary": "boom",
        "error": "boom",
        "intention": "should fail",
    }


def test_execute_plan_calls_keeps_empty_intention_off_output():
    def _execute(call):
        return {"tool_name": call["tool_name"], "ok": True}

    plan = [{"tool_name": "echo", "args": {}, "intention": "   "}]
    results = execute_plan_calls(plan, execute_call=_execute)
    assert results == [{"tool_name": "echo", "ok": True}]


def test_execute_plan_calls_preserves_intent_alias_in_results():
    def _execute(call):
        return {"tool_name": call["tool_name"], "ok": True}

    plan = [{"tool_name": "echo", "args": {}, "intent": "inspect flow"}]
    results = execute_plan_calls(plan, execute_call=_execute)
    assert results == [{"tool_name": "echo", "ok": True, "intention": "inspect flow"}]
