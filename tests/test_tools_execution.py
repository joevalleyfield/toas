import sys

import pytest

from toas.runtime.environment_policy import EnvironmentPolicy, active_environment_policy
from toas.tools_cluster.execution import adapt_call_for_execution, execute_plan_calls
from toas.tools_cluster.file_match_ops import RepairSuggestionError
from toas.tools_cluster.shell_ops import run_subprocess


def test_adapt_call_for_execution_no_default_cwd_returns_original_call():
    call = {"tool_name": "shell", "args": {"argv": ["pwd"]}}
    assert adapt_call_for_execution(call, default_shell_cwd=None, default_shell_env=None) is call


def test_adapt_call_for_execution_shell_sets_default_cwd_and_env_filters_none(tmp_path):
    call = {"tool_name": "shell", "args": {"argv": ["pwd"]}}
    adapted = adapt_call_for_execution(
        call,
        default_shell_cwd=str(tmp_path),
        default_shell_env={"A": "1", "B": None},
        default_shell_timeout_s=120,
    )
    assert adapted is not call
    assert adapted["args"]["cwd"] == str(tmp_path.resolve())
    assert adapted["args"]["env"] == {"A": "1"}
    assert adapted["args"]["timeout_s"] == 120


def test_execute_plan_calls_applies_process_environment_to_runtime_subprocess(tmp_path, monkeypatch):
    monkeypatch.setenv("TOAS_ENV_TEST", "host-value")
    monkeypatch.setenv("TOAS_ENV_REMOVE", "remove-me")

    def _execute(_call):
        return run_subprocess(
            [sys.executable, "-c", "import os; print(os.getenv('TOAS_ENV_TEST', 'missing')); print(os.getenv('TOAS_ENV_REMOVE', 'missing')); print(bool(os.getenv('PATH')))"],
            cwd=tmp_path,
            timeout_s=5,
        )

    result = execute_plan_calls(
        [{"tool_name": "python_script", "args": {"script": "unused"}}],
        execute_call=_execute,
        default_process_env={"TOAS_ENV_TEST": "transcript-value", "TOAS_ENV_REMOVE": None},
    )[0]

    assert result["ok"] is True
    assert result["stdout"].splitlines() == ["transcript-value", "missing", "True"]


def test_execute_plan_calls_applies_replace_policy_after_process_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TOAS_ENV_TEST", "host-value")

    def _execute(_call):
        return run_subprocess(
            [sys.executable, "-c", "import os; print(os.getenv('TOAS_ENV_TEST', 'missing')); print(bool(os.getenv('PATH')))"],
            cwd=tmp_path,
            timeout_s=5,
        )

    with active_environment_policy(EnvironmentPolicy(mode="replace")):
        result = execute_plan_calls(
            [{"tool_name": "python_script", "args": {"script": "unused"}}],
            execute_call=_execute,
            default_process_env={"TOAS_ENV_TEST": "transcript-value"},
        )[0]

    assert result["ok"] is True
    assert result["stdout"].splitlines() == ["missing", "False"]


def test_adapt_call_for_execution_preserves_unbounded_explicit_positive_timeout(tmp_path):
    call = {"tool_name": "shell_script", "args": {"script": "echo hi", "timeout_s": 86400}}
    adapted = adapt_call_for_execution(
        call,
        default_shell_cwd=str(tmp_path),
        default_shell_env=None,
        default_shell_timeout_s=120,
    )

    assert adapted["args"]["timeout_s"] == 86400


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
        "failure_kind": "execution",
        "outcome": "failed",
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


def test_execute_plan_calls_preserves_structured_repair_suggestion():
    suggestion = {"type": "frontier_repair", "tool_name": "replace_block", "args_patch": {"search_indent": 4}}

    def _execute(_call):
        raise RepairSuggestionError("mismatch", repair_suggestion=suggestion)

    result = execute_plan_calls([{"tool_name": "replace_block", "args": {}}], execute_call=_execute)[0]

    assert result["repair_suggestion"] == suggestion


@pytest.mark.parametrize(
    ("failed_index", "expected_seen"),
    [
        (0, ["bad"]),
        (1, ["first", "bad"]),
        (2, ["first", "second", "bad"]),
    ],
)
def test_execute_plan_calls_stops_at_first_raised_failure(failed_index, expected_seen):
    names = ["first", "second", "third"]
    names[failed_index] = "bad"
    seen = []

    def _execute(call):
        seen.append(call["tool_name"])
        if call["tool_name"] == "bad":
            raise RuntimeError("boom")
        return {"tool_name": call["tool_name"], "ok": True}

    results = execute_plan_calls(
        [{"tool_name": name, "args": {}} for name in names],
        execute_call=_execute,
    )

    assert seen == expected_seen
    assert len(results) == failed_index + 1
    assert results[-1]["ok"] is False
    assert results[-1]["failure_kind"] == "execution"
    assert results[-1]["outcome"] == "failed"


def test_execute_plan_calls_stops_at_returned_failure():
    seen = []

    def _execute(call):
        seen.append(call["tool_name"])
        return {
            "tool_name": call["tool_name"],
            "ok": call["tool_name"] != "bad",
            "summary": "nope" if call["tool_name"] == "bad" else "ok",
        }

    results = execute_plan_calls(
        [
            {"tool_name": "first", "args": {}},
            {"tool_name": "bad", "args": {}},
            {"tool_name": "unattempted", "args": {}},
        ],
        execute_call=_execute,
    )

    assert seen == ["first", "bad"]
    assert len(results) == 2
    assert results[-1]["failure_kind"] == "execution"
    assert results[-1]["outcome"] == "failed"


@pytest.mark.parametrize(
    ("message", "failure_kind", "outcome"),
    [
        ("invalid arguments for tool echo: missing text", "validation", "failed"),
        ("tool shell disallows command: sh (override needed)", "authorization", "blocked"),
        ("tool shell timed out after 5s", "timeout", "indeterminate"),
    ],
)
def test_execute_plan_calls_classifies_runtime_failures(message, failure_kind, outcome):
    def _execute(_call):
        raise RuntimeError(message)

    result = execute_plan_calls(
        [{"tool_name": "echo", "args": {}}],
        execute_call=_execute,
    )[0]

    assert result["failure_kind"] == failure_kind
    assert result["outcome"] == outcome


@pytest.mark.parametrize(
    ("exc", "failure_kind"),
    [
        (TimeoutError("deadline"), "timeout"),
        (ConnectionError("lost response"), "transport"),
        (ChildProcessError("runner vanished"), "process"),
    ],
)
def test_execute_plan_calls_marks_unknown_completion_failures_indeterminate(exc, failure_kind):
    def _execute(_call):
        raise exc

    result = execute_plan_calls([{"tool_name": "echo", "args": {}}], execute_call=_execute)[0]

    assert result["failure_kind"] == failure_kind
    assert result["outcome"] == "indeterminate"


def test_execute_plan_calls_does_not_swallow_cancellation_or_dispatch_suffix():
    seen = []

    def _execute(call):
        seen.append(call["tool_name"])
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        execute_plan_calls(
            [
                {"tool_name": "cancelled", "args": {}},
                {"tool_name": "unattempted", "args": {}},
            ],
            execute_call=_execute,
        )

    assert seen == ["cancelled"]


def test_execute_plan_calls_captures_unexpected_exception_with_traceback():
    def _execute(_call):
        raise SyntaxError("unexpected syntax error in file.py", ("file.py", 10, 1, "bad"))

    result = execute_plan_calls([{"tool_name": "custom_tool", "args": {}}], execute_call=_execute)[0]

    assert result["ok"] is False
    assert result["tool_name"] == "custom_tool"
    assert "unexpected syntax error in file.py" in result["error"]
    assert "Traceback" in result["traceback"]


def test_execute_plan_calls_emits_tool_lifecycle_stream_events():
    from toas.runtime.tool_stream_context import tool_stream_emitter

    events = []

    def _emitter(event_type, payload):
        events.append((event_type, payload))

    plan = [
        {"tool_name": "read_file", "args": {"path": "a.txt"}},
        {"tool_name": "write_file", "args": {"path": "b.txt", "content": "hello"}},
    ]

    def _execute(call):
        return {"tool_name": call.get("tool_name"), "ok": True, "summary": "done"}

    with tool_stream_emitter(_emitter):
        results = execute_plan_calls(plan, execute_call=_execute)

    assert len(results) == 2
    assert events == [
        ("tool_start", {"operation": "read_file", "index": 1, "total": 2}),
        ("tool_done", {"operation": "read_file", "ok": True, "index": 1, "total": 2}),
        ("tool_start", {"operation": "write_file", "index": 2, "total": 2}),
        ("tool_done", {"operation": "write_file", "ok": True, "index": 2, "total": 2}),
    ]


@pytest.mark.parametrize(
    "exception_cls,exc_args",
    [
        (TimeoutError, ("command timed out",)),
        (ConnectionError, ("connection dropped",)),
        (ChildProcessError, ("child exited unexpectedly",)),
        (RuntimeError, ("failed runtime operation",)),
        (Exception, ("generic error",)),
    ],
)
def test_execute_plan_calls_continue_on_error_across_exceptions(exception_cls, exc_args):
    plan = [
        {"tool_name": "tool_fail", "args": {}},
        {"tool_name": "tool_succeed", "args": {}},
    ]

    def _execute(call):
        if call["tool_name"] == "tool_fail":
            raise exception_cls(*exc_args)
        return {"tool_name": call["tool_name"], "ok": True, "result": "ok"}

    # Default continue_on_error=False stops after first failure
    results_fail_fast = execute_plan_calls(plan, execute_call=_execute, continue_on_error=False)
    assert len(results_fail_fast) == 1
    assert results_fail_fast[0]["ok"] is False

    # continue_on_error=True runs both calls
    results_continue = execute_plan_calls(plan, execute_call=_execute, continue_on_error=True)
    assert len(results_continue) == 2
    assert results_continue[0]["ok"] is False
    assert results_continue[1]["ok"] is True


def test_execute_plan_calls_continue_on_error_returned_failure_and_call_override():
    plan = [
        {"tool_name": "tool_a", "args": {}, "continue_on_error": True},
        {"tool_name": "tool_b", "args": {}},
        {"tool_name": "tool_c", "args": {}},
    ]

    def _execute(call):
        name = call["tool_name"]
        if name == "tool_a":
            return {"tool_name": name, "ok": False, "summary": "failure a"}
        if name == "tool_b":
            return {"tool_name": name, "ok": False, "summary": "failure b"}
        return {"tool_name": name, "ok": True, "summary": "success c"}

    # tool_a has continue_on_error=True override, but tool_b fails with batch default continue_on_error=False
    results = execute_plan_calls(plan, execute_call=_execute, continue_on_error=False)
    assert len(results) == 2
    assert results[0]["ok"] is False
    assert results[1]["ok"] is False

    # When batch default is True, but tool_a overrides to False:
    plan_override_false = [
        {"tool_name": "tool_a", "args": {}, "continue_on_error": False},
        {"tool_name": "tool_b", "args": {}},
    ]
    results_override = execute_plan_calls(plan_override_false, execute_call=_execute, continue_on_error=True)
    assert len(results_override) == 1
    assert results_override[0]["ok"] is False



