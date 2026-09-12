from __future__ import annotations

import os
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from toas.acceptance_harness import load_workspace_config, materialize_workspace
from toas.operator_api import step_once as operator_step_once

scenarios("../features/history_help_discovery.feature")


@given("a scratch TOAS workspace for history help", target_fixture="history_help_state")
def given_history_help_workspace(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    (repo / ".toas").mkdir(exist_ok=True)
    (repo / ".toas" / "session.md").write_text("", encoding="utf-8")
    return {"repo": repo, "outputs": {}}


def _run_history_help(repo: Path, command: str, capsys) -> str:
    cwd = Path.cwd()
    try:
        os.chdir(repo)
        operator_step_once(control=command)
    finally:
        os.chdir(cwd)
    return capsys.readouterr().out


@when("the operator opens history help")
def when_open_history_help(history_help_state: dict, capsys) -> None:
    for command in ("/help history", "/help cli", "/help"):
        history_help_state["outputs"][command] = _run_history_help(history_help_state["repo"], command, capsys)


@then("history help should distinguish the durable-state projections")
def then_history_help_contract(history_help_state: dict) -> None:
    outputs = history_help_state["outputs"]
    focused = outputs["/help history"]
    for phrase in (
        "find branch tips",
        "read a bounded root-to-head lineage",
        "inspect history topology",
        "reconstruct transcript-shaped context",
        "audit model-visible input",
    ):
        assert phrase in focused
    assert "/help history" in outputs["/help cli"]
    assert "/help history" in outputs["/help"]
