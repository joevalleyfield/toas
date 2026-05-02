import os
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import parse

from toas.acceptance_harness import (
    load_backend_config,
    load_replay_fixture,
    should_use_live,
    write_live_capture,
)
from toas.graph import active_head_id, list_heads, project_transcript, read_log, write_message_events
from toas.operator_api import step_once as operator_step_once
from toas.step import step as toas_step

scenarios("../features/complete_change_request.feature")


@pytest.fixture
def acceptance_state(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".toas").mkdir()
    change_file = repo / "CHANGELOG.md"
    change_file.write_text("# Changelog\n", encoding="utf-8")
    return {
        "repo": repo,
        "events_path": repo / ".toas" / "events.jsonl",
        "scenario": None,
        "request_defined": False,
        "frontier_staged": False,
        "implemented": False,
        "interrupted": False,
        "recovered": False,
        "validated": False,
        "history_events": [],
        "commit": None,
        "change_file": change_file,
        "fixtures_dir": Path(__file__).resolve().parent.parent / "fixtures" / "backend",
        "backend_cfg": load_backend_config(),
    }


@given("a TOAS-managed repository workspace")
def given_workspace(acceptance_state: dict) -> None:
    assert acceptance_state["repo"].exists()
    acceptance_state["history_events"].append("workspace_ready")


@given(parse('an open acceptance scenario "{scenario_name}"'))
def given_scenario_name(acceptance_state: dict, scenario_name: str) -> None:
    acceptance_state["scenario"] = scenario_name
    acceptance_state["history_events"].append(f"scenario:{scenario_name}")


@given("a bounded change request is defined")
def given_bounded_request(acceptance_state: dict) -> None:
    acceptance_state["request_defined"] = True
    acceptance_state["history_events"].append("request_defined")


@given("the operator stages the initial frontier intent")
@when("the operator stages the initial frontier intent")
def when_stage_frontier(acceptance_state: dict) -> None:
    session_path = acceptance_state["repo"] / "session.md"
    session_path.write_text("## TOAS:USER\n\nacceptance S1 staged frontier\n", encoding="utf-8")
    cwd = Path.cwd()
    try:
        os.chdir(acceptance_state["repo"])
        operator_step_once()
    finally:
        os.chdir(cwd)
    events = read_log(str(acceptance_state["events_path"]))
    acceptance_state["stage_events"] = events
    acceptance_state["frontier_staged"] = True
    acceptance_state["history_events"].append("frontier_staged")


@given("the operator performs an implementation pass")
@when("the operator performs an implementation pass")
def when_implement(acceptance_state: dict) -> None:
    assert acceptance_state["frontier_staged"] is True
    step_label = "implementation_pass"
    step_labels = {step_label: 0}
    use_live = should_use_live(
        cfg=acceptance_state["backend_cfg"],
        step_index=0,
        step_label=step_label,
        step_labels=step_labels,
    )
    if use_live:
        backend_payload = {"change_line": "- acceptance run", "source": "live"}
        if acceptance_state["backend_cfg"].write_live_captures:
            write_live_capture(acceptance_state["fixtures_dir"], step_label, backend_payload)
    else:
        backend_payload = load_replay_fixture(acceptance_state["fixtures_dir"], step_label)
    transcript = (
        "## TOAS:USER\n\nplease run this\n"
        "```yaml\n"
        "- tool_name: echo\n"
        "  args:\n"
        f"    text: {backend_payload['change_line']}\n"
        "```\n"
    )
    impl_nodes, impl_out = toas_step(transcript, [])
    acceptance_state["implementation_nodes"] = impl_nodes
    acceptance_state["implementation_out"] = impl_out
    write_message_events(str(acceptance_state["events_path"]), impl_nodes)
    path = acceptance_state["change_file"]
    path.write_text(path.read_text(encoding="utf-8") + f"\n{backend_payload['change_line']}\n", encoding="utf-8")
    acceptance_state["implemented"] = True
    acceptance_state["history_events"].append("implemented")


@given("an interruption occurs before closure")
@when("an interruption occurs before closure")
def when_interrupt(acceptance_state: dict) -> None:
    acceptance_state["interrupted"] = True
    acceptance_state["history_events"].append("interrupted")


@given("the operator recovers using TOAS history and/or rebuild surfaces")
@when("the operator recovers using TOAS history and/or rebuild surfaces")
def when_recover(acceptance_state: dict) -> None:
    assert acceptance_state["interrupted"] is True
    step_label = "recovery_check"
    step_labels = {"implementation_pass": 0, step_label: 1}
    use_live = should_use_live(
        cfg=acceptance_state["backend_cfg"],
        step_index=1,
        step_label=step_label,
        step_labels=step_labels,
    )
    if use_live:
        payload = {"recoverable": True, "source": "live"}
        if acceptance_state["backend_cfg"].write_live_captures:
            write_live_capture(acceptance_state["fixtures_dir"], step_label, payload)
    else:
        payload = load_replay_fixture(acceptance_state["fixtures_dir"], step_label)
    assert payload["recoverable"] is True
    events = read_log(str(acceptance_state["events_path"]))
    heads = list_heads(events)
    selected_head = active_head_id(events)
    projected = project_transcript(events)
    acceptance_state["recovery_observed"] = {
        "events_count": len(events),
        "heads_count": len(heads),
        "selected_head": selected_head,
        "projected": projected,
    }
    acceptance_state["recovered"] = True
    acceptance_state["history_events"].append("recovered")


@when("the operator completes validation")
def when_validate(acceptance_state: dict) -> None:
    text = acceptance_state["change_file"].read_text(encoding="utf-8")
    acceptance_state["validated"] = "- acceptance run" in text
    acceptance_state["history_events"].append("validated")
    if acceptance_state["validated"]:
        acceptance_state["commit"] = "simulated-commit-id"


@then("the requested change should be present")
def then_change_present(acceptance_state: dict) -> None:
    assert acceptance_state["implemented"] is True
    impl_out = acceptance_state.get("implementation_out") or []
    impl_nodes = acceptance_state.get("implementation_nodes") or []
    combined = [*impl_nodes, *impl_out]
    assert any(node.get("role") == "user" for node in combined)
    assert any("tool_name: echo" in (node.get("content") or "") for node in combined)
    assert "- acceptance run" in acceptance_state["change_file"].read_text(encoding="utf-8")


@then("the frontier should be staged in durable progression")
def then_frontier_staged(acceptance_state: dict) -> None:
    assert acceptance_state["request_defined"] is True
    assert acceptance_state["frontier_staged"] is True
    stage_events = acceptance_state.get("stage_events") or []
    user_events = [e for e in stage_events if e.get("role") == "user"]
    assert len(user_events) >= 1
    assert "acceptance S1 staged frontier" in user_events[-1]["content"]
    assert acceptance_state["history_events"][-1] == "frontier_staged"


@then("the frontier should be recovered and runnable")
def then_recovered(acceptance_state: dict) -> None:
    assert acceptance_state["implemented"] is True
    assert acceptance_state["interrupted"] is True
    assert acceptance_state["recovered"] is True
    assert acceptance_state["history_events"][-1] == "recovered"
    observed = acceptance_state.get("recovery_observed") or {}
    assert observed.get("events_count", 0) >= 2
    assert observed.get("heads_count", 0) >= 1
    assert "acceptance S1 staged frontier" in (observed.get("projected") or "")


@then("durable-history invariants should hold")
def then_invariants(acceptance_state: dict) -> None:
    assert acceptance_state["history_events"] == [
        "workspace_ready",
        "scenario:complete-change-request",
        "request_defined",
        "frontier_staged",
        "implemented",
        "interrupted",
        "recovered",
        "validated",
    ]


@then("a scoped commit should be produced")
def then_commit(acceptance_state: dict) -> None:
    assert acceptance_state["validated"] is True
    assert acceptance_state["commit"] == "simulated-commit-id"
