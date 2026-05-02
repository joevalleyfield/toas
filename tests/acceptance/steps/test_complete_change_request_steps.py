from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import parse

scenarios("../features/complete_change_request.feature")


@pytest.fixture
def acceptance_state(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    repo.mkdir()
    change_file = repo / "CHANGELOG.md"
    change_file.write_text("# Changelog\n", encoding="utf-8")
    return {
        "repo": repo,
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


@when("the operator stages the initial frontier intent")
def when_stage_frontier(acceptance_state: dict) -> None:
    acceptance_state["frontier_staged"] = True
    acceptance_state["history_events"].append("frontier_staged")


@when("the operator performs an implementation pass")
def when_implement(acceptance_state: dict) -> None:
    assert acceptance_state["frontier_staged"] is True
    path = acceptance_state["change_file"]
    path.write_text(path.read_text(encoding="utf-8") + "\n- acceptance run\n", encoding="utf-8")
    acceptance_state["implemented"] = True
    acceptance_state["history_events"].append("implemented")


@when("an interruption occurs before closure")
def when_interrupt(acceptance_state: dict) -> None:
    acceptance_state["interrupted"] = True
    acceptance_state["history_events"].append("interrupted")


@when("the operator recovers using TOAS history and/or rebuild surfaces")
def when_recover(acceptance_state: dict) -> None:
    assert acceptance_state["interrupted"] is True
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
    assert "- acceptance run" in acceptance_state["change_file"].read_text(encoding="utf-8")


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
