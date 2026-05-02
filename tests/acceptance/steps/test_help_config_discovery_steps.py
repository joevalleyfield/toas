import os
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from toas.graph import read_log
from toas.operator_api import step_once as operator_step_once
from toas.acceptance_harness import load_workspace_config, materialize_workspace

scenarios("../features/help_config_discovery.feature")


@pytest.fixture
def acceptance_state(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    (repo / ".toas").mkdir(exist_ok=True)
    return {
        "repo": repo,
        "events_path": repo / ".toas" / "events.jsonl",
        "stdout": "",
    }


@given("a TOAS-managed repository workspace")
def given_workspace(acceptance_state: dict) -> None:
    assert acceptance_state["repo"].exists()


@when("the operator requests config help via slash command")
def when_request_help_config(acceptance_state: dict, capsys: pytest.CaptureFixture[str]) -> None:
    session_path = acceptance_state["repo"] / "session.md"
    session_path.write_text("## TOAS:USER\n\n/help config\n", encoding="utf-8")
    cwd = Path.cwd()
    try:
        os.chdir(acceptance_state["repo"])
        operator_step_once()
    finally:
        os.chdir(cwd)
    acceptance_state["stdout"] = capsys.readouterr().out


@then("config-focused help guidance should be projected")
def then_config_help_projected(acceptance_state: dict) -> None:
    out = acceptance_state["stdout"]
    assert "config help:" in out
    assert "/config show" in out
    assert "/config values <key>" in out

    events = read_log(str(acceptance_state["events_path"]))
    assert any((event.get("role") == "user" and "/help config" in (event.get("content") or "")) for event in events)
