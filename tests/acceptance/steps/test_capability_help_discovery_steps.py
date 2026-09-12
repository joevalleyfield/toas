from __future__ import annotations

import os
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from toas.acceptance_harness import load_workspace_config, materialize_workspace
from toas.operator_api import step_once as operator_step_once

scenarios("../features/capability_help_discovery.feature")


@given("a scratch TOAS workspace for capability help", target_fixture="capability_help_state")
def given_capability_help_workspace(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    (repo / ".toas").mkdir(exist_ok=True)
    (repo / ".toas" / "session.md").write_text("", encoding="utf-8")
    return {"repo": repo, "outputs": {}}


@when("the operator opens capability help")
def when_open_capability_help(capability_help_state: dict, capsys) -> None:
    cwd = Path.cwd()
    try:
        os.chdir(capability_help_state["repo"])
        operator_step_once(control="/help capabilities")
    finally:
        os.chdir(cwd)
    capability_help_state["output"] = capsys.readouterr().out


@then("capability help should explain the capture task thread path")
def then_capability_help_contract(capability_help_state: dict) -> None:
    content = capability_help_state["output"]
    for phrase in (
        "registry describes",
        "configured profile",
        "currently callable",
        "capability_help(topic: \"capture_task_thread\")",
        "arguments.title",
        "arguments.kind",
        "side-thread",
    ):
        assert phrase in content
