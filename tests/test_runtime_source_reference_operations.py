from __future__ import annotations

from pathlib import Path

import pytest

from toas.config import OperatorConfig
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_commands import execute_operator_command
from toas.runtime.source_reference_operations import handle_source_reference_commands


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
