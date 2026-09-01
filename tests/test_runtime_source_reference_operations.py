from __future__ import annotations

from pathlib import Path

import pytest

from toas.config import OperatorConfig
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_commands import execute_operator_command
from toas.runtime.source_reference_operations import (
    SourceSelection,
    _retry_source,
    _selected_source_for_index,
    _tail_selector_for_failure,
    handle_source_reference_commands,
)


def _ctx(working):
    return OperatorCommandContext(
        execute=lambda _working, _plan: [],
        events=[],
        working=working,
        frontier_role="user",
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[str(Path(".").resolve())],
        config=OperatorConfig(),
        config_sources=None,
        already_executed_indices=None,
    )


class _Step:
    @staticmethod
    def _select_assistant_plan_candidates(*, content, plan, yaml_position, arbitration_mode):
        assert plan is None
        return [
            {"kind": "plan", "value": [{"tool_name": "echo", "args": {"text": "one"}}]},
            {
                "kind": "plan",
                "value": [
                    {"tool_name": "echo", "args": {"text": "two"}},
                    {"tool_name": "echo", "args": {"text": "three"}},
                ],
            },
        ]

    @staticmethod
    def resolve_effective_env_modifiers(_working):
        return {}

    @staticmethod
    def resolve_effective_shell_allowed(_working, _config, _events):
        return ("echo",)

    @staticmethod
    def resolve_effective_shell_stream_stdout(_config, _env):
        return False

    @staticmethod
    def _execute_plan(plan, **_kwargs):
        return [{"role": "result", "content": "ran", "payload": {"ok": True}, "plan": plan}]


def test_stage_is_quiet_reference_with_source_provenance():
    out = handle_source_reference_commands(
        "stage",
        ["p-1.o-1.."],
        step_mod=_Step,
        context=_ctx([{"role": "assistant", "id": "a1", "content": "source"}, {"role": "user", "content": "/stage"}]),
    )

    assert out == [
        {
            "role": "user",
            "content": "/run p2.o2..",
            "provenance": {
                "source": "assistant_reference",
                "mode": "quiet_stage",
                "reference": {
                    "message_index": 0,
                    "message_id": "a1",
                    "candidate_count": 2,
                    "operation": "stage",
                    "selectors": ["p2.o2.."],
                },
            },
        }
    ]


def test_stage_without_selector_projects_the_whole_local_sequence():
    out = handle_source_reference_commands(
        "stage",
        [],
        step_mod=_Step,
        context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/stage"}]),
    )
    assert out[0]["content"] == "/run p1.."


def test_stage_plan_tail_resolves_to_absolute_forward_selector():
    out = handle_source_reference_commands(
        "stage",
        ["p-2.."],
        step_mod=_Step,
        context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/stage"}]),
    )
    assert out[0]["content"] == "/run p1.."


def test_source_root_survives_intervening_user_and_result_turns():
    out = handle_source_reference_commands(
        "stage",
        ["p1"],
        step_mod=_Step,
        context=_ctx(
            [
                {"role": "assistant", "id": "a1", "content": "source"},
                {"role": "user", "content": "intervening"},
                {"role": "result", "content": "audit"},
                {"role": "user", "content": "/stage p1"},
            ]
        ),
    )
    assert out[0]["content"] == "/run p1"
    assert out[0]["provenance"]["reference"]["message_id"] == "a1"


def test_run_executes_selected_source_in_assistant_lane():
    out = handle_source_reference_commands(
        "run",
        ["p2.o1"],
        step_mod=_Step,
        context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/run p2.o1"}]),
    )
    assert out[0]["plan"] == [{"tool_name": "echo", "args": {"text": "two"}}]
    assert out[0]["source_reference"]["selectors"] == ["p2.o1"]


def test_failed_run_projects_direct_retry_and_bounded_reference_tail():
    class FailingStep(_Step):
        @staticmethod
        def _execute_plan(plan, **_kwargs):
            return [
                {"role": "result", "content": "ok", "payload": {"ok": True}},
                {
                    "role": "result",
                    "content": "failed",
                    "payload": {"tool_name": "echo", "ok": False, "error": "boom"},
                },
            ]

    out = handle_source_reference_commands(
        "run",
        [],
        step_mod=FailingStep,
        context=_ctx(
            [
                {
                    "role": "assistant",
                    "id": "a1",
                    "content": (
                        "```yaml\n- tool_name: echo\n  args:\n    text: one\n```\n"
                        "```yaml\n- tool_name: echo\n  args:\n    text: two\n- tool_name: echo\n  args:\n    text: three\n```"
                    ),
                },
                {"role": "user", "content": "/run"},
            ]
        ),
    )
    recovery = out[-1]
    assert recovery["role"] == "user"
    assert "timeout_s: 5" in recovery["content"]
    assert "Remaining referenced assistant source (bounded):\n\n/run p2.o2.." in recovery["content"]
    assert recovery["provenance"]["source"] == "adopted"
    assert recovery["provenance"]["source_reference"]["selectors"] == ["p1..", "p2.."]
    assert recovery["recovery_transition"] == "frontier"


def test_failed_final_operation_of_one_plan_references_the_next_plan():
    class FirstFailureStep(_Step):
        @staticmethod
        def _execute_plan(plan, **_kwargs):
            return [{"role": "result", "content": "failed", "payload": {"ok": False}}]

    out = handle_source_reference_commands(
        "run",
        [],
        step_mod=FirstFailureStep,
        context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/run"}]),
    )
    assert "/run p2.." in out[-1]["content"]


def test_tail_selector_returns_none_for_unmatched_failure_position():
    assert _tail_selector_for_failure(selections=[], failed_index=0) is None
    selection = SourceSelection(
        plan=[{"tool_name": "echo", "args": {}}],
        selector="p1",
        source_plan_start=1,
        source_operation_start=1,
        source_operation_end=1,
    )
    assert _tail_selector_for_failure(selections=[selection], failed_index=0) is None


def test_retry_source_preserves_existing_timeout_and_handles_missing_args():
    assert _retry_source("# authored\n- tool_name: echo\n  args:\n    timeout_s: 2\n", 9).endswith("timeout_s: 2\n")
    assert "timeout_s: 9" in _retry_source("- tool_name: echo\n", 9)
    assert "timeout_s: 9" in _retry_source("- tool_name: echo\n  args: {}\n", 9)
    assert _retry_source("", 9) is None


def test_selected_source_for_index_returns_none_outside_selected_sequence():
    selection = SourceSelection(
        plan=[{"tool_name": "echo", "args": {}}],
        selector="p1",
        source_plan_start=1,
        source_operation_start=1,
        source_operation_end=1,
        operation_sources=("authored",),
    )
    assert _selected_source_for_index(selections=[selection], index=1) is None


def test_completed_shell_failure_does_not_create_reference_recovery():
    class ShellFailureStep(_Step):
        @staticmethod
        def _select_assistant_plan_candidates(**_kwargs):
            return [{"kind": "plan", "value": [{"tool_name": "shell", "args": {"argv": ["false"]}}]}]

        @staticmethod
        def _execute_plan(plan, **_kwargs):
            return [
                {
                    "role": "result",
                    "content": "exit=1",
                    "payload": {"tool_name": "shell", "ok": False, "exit_code": 1},
                }
            ]

    out = handle_source_reference_commands(
        "run",
        ["p1"],
        step_mod=ShellFailureStep,
        context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/run p1"}]),
    )
    assert len(out) == 1


def test_run_without_selector_executes_all_local_operations():
    out = handle_source_reference_commands(
        "run",
        [],
        step_mod=_Step,
        context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/run"}]),
    )
    assert [call["args"]["text"] for call in out[0]["plan"]] == ["one", "two", "three"]


def test_operation_tail_crosses_later_plans_in_source_order():
    out = handle_source_reference_commands(
        "run",
        ["p1.o1.."],
        step_mod=_Step,
        context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/run"}]),
    )
    assert [call["args"]["text"] for call in out[0]["plan"]] == ["one", "two", "three"]


def test_stage_operation_tail_keeps_the_compact_resolved_reference():
    class MultiStep(_Step):
        @staticmethod
        def _select_assistant_plan_candidates(**_kwargs):
            return [
                {"kind": "plan", "value": [{"tool_name": "echo", "args": {"text": "one"}}, {"tool_name": "echo", "args": {"text": "two"}}]},
                {"kind": "plan", "value": [{"tool_name": "echo", "args": {"text": "three"}}]},
            ]

    out = handle_source_reference_commands(
        "stage",
        ["p1.o2.."],
        step_mod=MultiStep,
        context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/stage"}]),
    )
    assert out[0]["content"] == "/run p1.o2.."


@pytest.mark.parametrize("args", [["p0"], ["p1.o0"], ["p1.o1..o2"], ["a1.p1"]])
def test_invalid_selectors_are_rejected(args):
    with pytest.raises(ValueError, match="(usage|index out of range)"):
        handle_source_reference_commands(
            "stage",
            args,
            step_mod=_Step,
            context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/stage"}]),
        )


def test_selector_argument_and_negative_index_errors():
    context = _ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/stage"}])
    with pytest.raises(ValueError, match="usage"):
        handle_source_reference_commands("stage", ["p1", "p2"], step_mod=_Step, context=context)
    with pytest.raises(ValueError, match="plan index out of range"):
        handle_source_reference_commands("stage", ["p-3"], step_mod=_Step, context=context)


def test_source_reference_errors_and_dispatch_guard():
    with pytest.raises(ValueError, match="no prior assistant"):
        handle_source_reference_commands("stage", [], step_mod=_Step, context=_ctx([{"role": "user", "content": "/stage"}]))
    with pytest.raises(ValueError, match="no addressable"):
        handle_source_reference_commands(
            "stage",
            [],
            step_mod=type("NoCandidates", (), {"_select_assistant_plan_candidates": lambda **_kwargs: []}),
            context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/stage"}]),
        )
    assert handle_source_reference_commands("other", [], step_mod=_Step, context=_ctx([])) is None


def test_operator_dispatch_reaches_source_reference_handler():
    working = [
        {
            "role": "assistant",
            "id": "a1",
            "content": "```yaml\n- tool_name: echo\n  args:\n    text: hello\n```",
        },
        {"role": "user", "content": "/stage p1"},
    ]
    out = execute_operator_command(
        "stage",
        ["p1"],
        execute=lambda _working, _plan: [],
        events=[],
        working=working,
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[str(Path(".").resolve())],
        config=OperatorConfig(),
    )
    assert out[0]["content"] == "/run p1"
    assert out[0]["provenance"]["source"] == "assistant_reference"


def test_real_dispatch_keeps_inert_blocks_out_of_coordinates_and_recovers_tail():
    working = [
        {
            "role": "assistant",
            "id": "a1",
            "content": (
                "[[inert]]\n"
                "```yaml\n- tool_name: echo\n  args:\n    text: inert\n```\n"
                "[[/inert]]\n"
                "```yaml\n- tool_name: unknown_reference_tool\n  args: {}\n- tool_name: echo\n  args:\n    text: tail\n```"
            ),
        },
        {"role": "user", "content": "/run p1"},
    ]
    out = execute_operator_command(
        "run",
        ["p1"],
        execute=lambda _working, _plan: [],
        events=[],
        working=working,
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[str(Path(".").resolve())],
        config=OperatorConfig(),
    )
    assert out[-1]["role"] == "user"
    assert "timeout_s: 5" in out[-1]["content"]
    assert "Remaining referenced assistant source (bounded):\n\n/run p1.o2.." in out[-1]["content"]


def test_empty_candidate_plan_is_not_selectable():
    class EmptyStep(_Step):
        @staticmethod
        def _select_assistant_plan_candidates(**_kwargs):
            return [{"kind": "plan", "value": []}]

    with pytest.raises(ValueError, match="no executable operations"):
        handle_source_reference_commands(
            "stage",
            [],
            step_mod=EmptyStep,
            context=_ctx([{"role": "assistant", "content": "source"}, {"role": "user", "content": "/stage"}]),
        )
