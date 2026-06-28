from __future__ import annotations

import os
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from toas.acceptance_harness import load_workspace_config, materialize_workspace
from toas.graph import read_log
from toas.operator_api import step_once as operator_step_once

scenarios("../features/control_lane_multi_command_frontier.feature")


@given("a TOAS-managed repository workspace for control-lane batching", target_fixture="acceptance_state")
def given_workspace(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    (repo / ".toas").mkdir(exist_ok=True)
    state = {
        "repo": repo,
        "events_path": repo / ".toas" / "events.jsonl",
        "events": [],
    }
    return state


@when("the operator submits one TOAS:CONTROL turn with multiple slash commands")
def when_submit_multi_control_turn(acceptance_state: dict) -> None:
    session_path = acceptance_state["repo"] / ".toas" / "session.md"
    session_path.write_text(
        (
            "## TOAS:CONTROL\n\n"
            "/config set prompt.mode mimic\n"
            "/config set prompt.constraints tools-guidance-core,no-chatty\n"
            "/prompt role/pragmatic-engineer_v1\n"
        ),
        encoding="utf-8",
    )
    cwd = Path.cwd()
    try:
        os.chdir(acceptance_state["repo"])
        operator_step_once()
    finally:
        os.chdir(cwd)
    acceptance_state["events"] = read_log(str(acceptance_state["events_path"]))


@then("each slash command should execute in source order with durable outcomes")
def then_verify_order(acceptance_state: dict) -> None:
    events = acceptance_state["events"]
    controls = [e for e in events if e.get("role") == "control"]
    assert controls, "expected control lane events"
    joined = "\n".join((e.get("content") or "") for e in controls)
    assert "/config set prompt.mode mimic" in joined
    assert "/config set prompt.constraints tools-guidance-core,no-chatty" in joined
    assert "/prompt role/pragmatic-engineer_v1" in joined


@when("the operator submits one TOAS:USER turn with mixed multi-instance intents")
def when_submit_mixed_multi_instance_user_turn(acceptance_state: dict, capsys) -> None:
    (acceptance_state["repo"] / "toas.toml").write_text(
        (
            "[extraction]\n"
            'intent_arbitration = "in_order"\n'
            "user_shell = true\n"
            "operator_command = true\n"
        ),
        encoding="utf-8",
    )
    session_path = acceptance_state["repo"] / ".toas" / "session.md"
    session_path.write_text(
        (
            "## TOAS:USER\n\n"
            "```yaml\n"
            "- operation: echo\n"
            "  arguments:\n"
            "    text: first-plan\n"
            "```\n"
            "/help\n"
            "```yaml\n"
            "- operation: echo\n"
            "  arguments:\n"
            "    text: second-plan\n"
            "```\n"
            "$ echo first-shell\n"
            "$ echo second-shell\n"
        ),
        encoding="utf-8",
    )
    cwd = Path.cwd()
    try:
        os.chdir(acceptance_state["repo"])
        operator_step_once()
    finally:
        os.chdir(cwd)
    acceptance_state["rendered"] = capsys.readouterr().out
    acceptance_state["events"] = read_log(str(acceptance_state["events_path"]))


@then("mixed intent results should preserve source-order instance execution")
def then_verify_mixed_multi_instance_order(acceptance_state: dict) -> None:
    rendered = acceptance_state.get("rendered", "")
    i_plan1 = rendered.find("[OK] echo: first-plan")
    i_plan2 = rendered.find("[OK] echo: second-plan")
    # Shell stdout is projected inside a `toas-output` fence; key on the fence
    # header so we anchor on the durable RESULT block rather than the streamed
    # stdout copy that precedes the result lanes.
    i_shell1 = rendered.find("source=tool.shell potency=inert\nfirst-shell")
    i_shell2 = rendered.find("source=tool.shell potency=inert\nsecond-shell")
    assert -1 not in (i_plan1, i_plan2, i_shell1, i_shell2)
    assert i_plan1 < i_plan2 < i_shell1 < i_shell2
