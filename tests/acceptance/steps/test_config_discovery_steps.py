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


@given("a scratch TOAS workspace for endpoint bootstrap", target_fixture="acceptance_state")
def given_endpoint_bootstrap_workspace(tmp_path: Path, monkeypatch) -> dict:
    repo = tmp_path / "repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    (repo / ".toas").mkdir(exist_ok=True)
    (repo / ".toas" / "session.md").write_text("", encoding="utf-8")
    monkeypatch.delenv("TOAS_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("TOAS_LLM_MODEL", raising=False)
    monkeypatch.setattr(
        "toas.llm_harness.fetch_models",
        lambda _settings: {"data": [{"id": "qwen3.6"}, {"id": "llama/3"}]},
    )
    return {"repo": repo, "outputs": []}


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


@when("the operator follows the config generation discovery path")
def when_follow_generation_discovery(acceptance_state: dict, capsys) -> None:
    outputs = []
    for command in ("/help generation", "/help config generation", "/config show generation"):
        _run_control(acceptance_state["repo"], command)
        outputs.append((command, capsys.readouterr().out))
    acceptance_state["generation_outputs"] = outputs


@when("the operator follows the config extraction discovery path")
def when_follow_extraction_discovery(acceptance_state: dict, capsys) -> None:
    outputs = []
    for command in ("/help extraction", "/help config extraction", "/config show extraction"):
        _run_control(acceptance_state["repo"], command)
        outputs.append((command, capsys.readouterr().out))
    acceptance_state["extraction_outputs"] = outputs


@when("the operator follows the endpoint and target authoring path")
def when_follow_endpoint_target_authoring(acceptance_state: dict, capsys) -> None:
    outputs = []
    for command in (
        "/config endpoint add local http://localhost:8080/v1",
        "/config endpoint set local.model qwen3.6",
        "/config target add local-qwen local qwen3.6",
        "/config endpoint set local.models qwen3.6,llama/3",
        "/config target add --all-known local --preview",
        "/config target add --all-known local",
        "/config list models",
        "/config endpoint list",
        "/config target list",
        "/models",
        "/models known local",
        "/model select local-qwen",
        "/model targets",
    ):
        _run_control(acceptance_state["repo"], command)
        outputs.append((command, capsys.readouterr().out))
    acceptance_state["endpoint_target_outputs"] = outputs


@when("the operator follows the endpoint bootstrap path")
def when_follow_endpoint_bootstrap(acceptance_state: dict, capsys) -> None:
    outputs = []
    for command in (
        "/config endpoint bootstrap local http://localhost:8080/v1 --refresh --targets",
        "/config endpoint bootstrap remote http://remote/v1 --refresh --target qwen3.6 --select",
        "/model targets",
    ):
        _run_control(acceptance_state["repo"], command)
        outputs.append((command, capsys.readouterr().out))
    acceptance_state["endpoint_bootstrap_outputs"] = outputs


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


@then("generation discovery should expose paired help and live state")
def then_generation_discovery_contract(acceptance_state: dict) -> None:
    outputs = acceptance_state["generation_outputs"]
    plain = _output(outputs, "/help generation")
    config_help = _output(outputs, "/help config generation")
    live = _output(outputs, "/config show generation")

    assert "help: generation" in plain
    assert "thinking posture" in plain
    assert "/help config generation" in plain
    assert "config help: generation" in config_help
    for key in ("generation.thinking_mode =", "generation.max_tokens =", "generation.max_retries ="):
        assert key in live
    assert "precedence stack" not in live
    assert "config_update" not in live


@then("extraction discovery should expose the non-executing boundary")
def then_extraction_discovery_contract(acceptance_state: dict) -> None:
    outputs = acceptance_state["extraction_outputs"]
    plain = _output(outputs, "/help extraction")
    config_help = _output(outputs, "/help config extraction")
    live = _output(outputs, "/config show extraction")

    assert "help: extraction" in plain
    assert "source order" in plain
    assert "does not execute" in plain
    assert "/help config extraction" in plain
    assert "config help: extraction" in config_help
    for key in ("extraction.yaml_position =", "extraction.intent_arbitration =", "extraction.projection_shape ="):
        assert key in live
    assert "precedence stack" not in live
    assert "config_update" not in live


@then("endpoint and target selection should be discoverable and network-free")
def then_endpoint_target_authoring_contract(acceptance_state: dict) -> None:
    outputs = acceptance_state["endpoint_target_outputs"]
    assert acceptance_state["probe_calls"] == []
    listed_config = _output(outputs, "/config list models")
    assert "llm.model =" in listed_config
    assert "precedence stack" not in listed_config

    endpoints = _output(outputs, "/config endpoint list")
    assert "configured endpoints:" in endpoints
    assert "local: http://localhost:8080/v1" in endpoints

    targets = _output(outputs, "/config target list")
    assert "local-qwen: endpoint=local, model=qwen3.6" in targets
    assert "local-qwen3.6: endpoint=local, model=qwen3.6" in targets
    assert "local-llama-3: endpoint=local, model=llama/3" in targets

    preview = _output(outputs, "/config target add --all-known local --preview")
    assert "planned model targets for endpoint local" in preview
    assert "config_update" not in preview

    models_usage = _output(outputs, "/models")
    assert "ENDPOINT is a configured endpoint name, not a URL." in models_usage
    known = _output(outputs, "/models known local")
    assert "models: qwen3.6, llama/3" in known

    selected = _output(outputs, "/model select local-qwen")
    assert "selected model target: local-qwen" in selected

    target_status = _output(outputs, "/model targets")
    assert "- local-qwen *: endpoint=local, model=qwen3.6, status=ready" in target_status
    assert "active target: local-qwen" in target_status


@then("endpoint bootstrap should report its completed phases")
def then_endpoint_bootstrap_contract(acceptance_state: dict) -> None:
    outputs = acceptance_state["endpoint_bootstrap_outputs"]
    local = _output(outputs, "/config endpoint bootstrap local http://localhost:8080/v1 --refresh --targets")
    assert "endpoint bootstrap complete" in local
    assert "model refresh: 2 known" in local
    assert "target promotion: 2 created" in local
    assert "active selection: unchanged" in local

    remote = _output(outputs, "/config endpoint bootstrap remote http://remote/v1 --refresh --target qwen3.6 --select")
    assert "target promotion: created remote-qwen3.6" in remote
    assert "active selection: remote-qwen3.6" in remote

    targets = _output(outputs, "/model targets")
    assert "- remote-qwen3.6 *: endpoint=remote, model=qwen3.6, status=ready" in targets
    assert "active target: remote-qwen3.6" in targets
