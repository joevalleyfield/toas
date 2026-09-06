from __future__ import annotations

import os
import re
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from toas.acceptance_harness import load_workspace_config, materialize_workspace
from toas.operator_api import step_once as operator_step_once

scenarios("../features/config_discovery.feature")


@given("a scratch TOAS workspace for config discovery", target_fixture="acceptance_state")
def given_config_workspace(tmp_path: Path, monkeypatch) -> dict:
    repo = tmp_path / "repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    (repo / ".toas").mkdir(exist_ok=True)
    (repo / ".toas" / "session.md").write_text("", encoding="utf-8")
    monkeypatch.delenv("TOAS_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("TOAS_LLM_MODEL", raising=False)
    probe_calls: list[tuple[tuple, dict]] = []

    def record_probe(*args, **kwargs):
        probe_calls.append((args, kwargs))
        raise AssertionError("config discovery must not probe an endpoint")

    monkeypatch.setattr("toas.llm_harness._request_json", record_probe)
    return {"repo": repo, "outputs": [], "probe_calls": probe_calls}


def _run_control(repo: Path, command: str) -> str:
    cwd = Path.cwd()
    try:
        os.chdir(repo)
        operator_step_once(control=command)
    finally:
        os.chdir(cwd)
    # operator_step_once writes its projection to stdout; the caller captures it.
    return command


@when("the operator follows the config models discovery path")
def when_follow_config_discovery(acceptance_state: dict, capsys) -> None:
    outputs = []
    for command in (
        "/help config models",
        "/config show models",
        "/config show models --sources",
        "/config show --sources models",
        "/help config sources",
        "/help config provenance",
    ):
        _run_control(acceptance_state["repo"], command)
        outputs.append((command, capsys.readouterr().out))
    acceptance_state["outputs"] = outputs


def _output(outputs: list[tuple[str, str]], command: str) -> str:
    return next(text for name, text in outputs if name == command)


def _normalize_block_ids(text: str) -> str:
    return re.sub(r"block_id=\S+", "block_id=<normalized>", text)


@then("config discovery should expose compact effective state and sources")
def then_config_discovery_contract(acceptance_state: dict) -> None:
    outputs = acceptance_state["outputs"]
    assert acceptance_state["probe_calls"] == []
    help_models = _output(outputs, "/help config models")
    assert "config help: models" in help_models
    assert "/config show models" in help_models

    show_models = _output(outputs, "/config show models")
    for key in ("llm.model =", "llm.models =", "llm.backends =", "llm.base_url =", "backend.mode ="):
        assert key in show_models
    assert "llm.model = qwen3.5-35b-a3b" in show_models
    assert "llm.base_url = http://localhost:8080/v1" in show_models
    assert "precedence stack" not in show_models
    assert "Quick edits:" not in show_models
    assert "config_update" not in show_models

    with_sources = _output(outputs, "/config show models --sources")
    sources_first = _output(outputs, "/config show --sources models")
    assert _normalize_block_ids(with_sources) == _normalize_block_ids(sources_first)
    assert "[source=default]" in with_sources

    sources_help = _output(outputs, "/help config sources")
    provenance_help = _output(outputs, "/help config provenance")
    assert _normalize_block_ids(sources_help) == _normalize_block_ids(provenance_help)
    assert "winning source only" in sources_help
    assert "/config show <topic> --sources" in sources_help
