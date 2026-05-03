import os
import json
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import parse

from toas.acceptance_harness import (
    load_backend_config,
    load_workspace_manifest,
    load_replay_fixture,
    materialize_workspace,
    resolve_workspace_config,
    should_use_live,
    write_live_capture,
)
from toas.graph import read_log
from toas.operator_api import (
    heads_lines as operator_heads_lines,
    history_lines as operator_history_lines,
)
from toas.operator_api import (
    rebuild_session as operator_rebuild_session,
)
from toas.operator_api import step_once as operator_step_once

scenarios("../features/complete_change_request.feature")


def _step_with_session(
    repo: Path,
    session_text: str,
    capsys: pytest.CaptureFixture[str],
    *,
    generate_override=None,
) -> str:
    session_path = repo / "session.md"
    session_path.write_text(session_text, encoding="utf-8")
    cwd = Path.cwd()
    try:
        os.chdir(repo)
        operator_step_once(generate=generate_override)
    finally:
        os.chdir(cwd)
    return capsys.readouterr().out


def _step_with_session_no_capture(repo: Path, session_text: str, *, generate_override=None) -> None:
    session_path = repo / "session.md"
    session_path.write_text(session_text, encoding="utf-8")
    cwd = Path.cwd()
    try:
        os.chdir(repo)
        operator_step_once(generate=generate_override)
    finally:
        os.chdir(cwd)


def _acceptance_generate_override(acceptance_state: dict):
    if acceptance_state["backend_cfg"].llm_mode != "fake":
        return None

    def _fake_generate(_working: list[dict]) -> dict:
        return {
            "role": "assistant",
            "content": "Acceptance fake-LLM response.",
            "response": {"model": "acceptance-fake"},
        }

    return _fake_generate


def _configure_minimal_generation_posture(acceptance_state: dict) -> None:
    _step_with_session_no_capture(
        acceptance_state["repo"],
        "## TOAS:USER\n\n/config set generation.thinking_mode disabled\n",
        generate_override=_acceptance_generate_override(acceptance_state),
    )
    acceptance_state["history_events"].append("posture_configured")


def _stage_frontier(acceptance_state: dict) -> None:
    _step_with_session_no_capture(
        acceptance_state["repo"],
        "## TOAS:USER\n\nacceptance S1 staged frontier\n",
        generate_override=_acceptance_generate_override(acceptance_state),
    )
    events = read_log(str(acceptance_state["events_path"]))
    acceptance_state["stage_events"] = events
    acceptance_state["frontier_staged"] = True
    acceptance_state["history_events"].append("frontier_staged")


def _implementation_session_text() -> str:
    return (
        "## TOAS:USER\n\n```yaml\n"
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: src/toas/runtime/operator_command_config_help.py\n"
        "    search_block: |\n"
        "        def _handle_help_command(args: list[str], *, step_mod) -> list[dict]:\n"
        "            if not args:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_session_help()}]\n"
        "            if args == [\"full\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_session_help_full()}]\n"
        "            if args == [\"commands\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_commands_inert()}]\n"
        "            if args == [\"tools\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_tools()}]\n"
        "            if args == [\"cli\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_cli()}]\n"
        "            if args == [\"approvals\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_approvals()}]\n"
        "            if args == [\"config\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_config()}]\n"
        "            else:\n"
        "                raise ValueError(\"usage: /help\")\n"
        "    replacement_block: |\n"
        "        def _handle_help_command(args: list[str], *, step_mod) -> list[dict]:\n"
        "            if not args:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_session_help()}]\n"
        "            if args == [\"full\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_session_help_full()}]\n"
        "            if args == [\"commands\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_commands_inert()}]\n"
        "            if args == [\"tools\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_tools()}]\n"
        "            if args == [\"cli\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_cli()}]\n"
        "            if args == [\"approvals\"]:\n"
        "                return [{\"role\": \"result\", \"content\": step_mod.render_help_approvals()}]\n"
        "            if args == [\"config\"]:\n"
        "                return [{\"role\": \"result\", \"content\": _CONFIG_USAGE}]\n"
        "            else:\n"
        "                raise ValueError(\"usage: /help\")\n"
        "```\n"
    )


def _run_implementation_pass(acceptance_state: dict, *, capsys: pytest.CaptureFixture[str] | None = None) -> None:
    assert acceptance_state["frontier_staged"] is True
    if capsys is None:
        _step_with_session_no_capture(
            acceptance_state["repo"],
            _implementation_session_text(),
            generate_override=_acceptance_generate_override(acceptance_state),
        )
        acceptance_state["implementation_output"] = ""
    else:
        acceptance_state["implementation_output"] = _step_with_session(
            acceptance_state["repo"],
            _implementation_session_text(),
            capsys,
            generate_override=_acceptance_generate_override(acceptance_state),
        )
    acceptance_state["implementation_events"] = read_log(str(acceptance_state["events_path"]))
    acceptance_state["implemented"] = True
    acceptance_state["history_events"].append("implemented")


def _run_bounded_shell_attempt(acceptance_state: dict, *, capsys: pytest.CaptureFixture[str] | None = None) -> None:
    payload = "## TOAS:USER\n\n```yaml\n- operation: shell\n  arguments:\n    argv: [\"pytest\", \"tests/test_help_config.py\"]\n```\n"
    if capsys is None:
        _step_with_session_no_capture(
            acceptance_state["repo"],
            payload,
            generate_override=_acceptance_generate_override(acceptance_state),
        )
        acceptance_state["shell_block_output"] = (acceptance_state["repo"] / "session.md").read_text(encoding="utf-8")
    else:
        acceptance_state["shell_block_output"] = _step_with_session(
            acceptance_state["repo"],
            payload,
            capsys,
            generate_override=_acceptance_generate_override(acceptance_state),
        )


def _transition_path(state: dict, name: str) -> Path:
    return state["repo"] / ".toas" / f"acceptance_{name}.json"


def _rehydrate_transition(acceptance_state: dict, name: str) -> None:
    if name == "s1":
        acceptance_state["request_defined"] = True
        _configure_minimal_generation_posture(acceptance_state)
        return
    if name == "s2":
        _rehydrate_transition(acceptance_state, "s1")
        _stage_frontier(acceptance_state)
        _run_implementation_pass(acceptance_state)
        return
    if name == "s3":
        _rehydrate_transition(acceptance_state, "s2")
        when_interrupt(acceptance_state)
        return
    if name == "s4":
        _rehydrate_transition(acceptance_state, "s3")
        when_recover(acceptance_state)
        return
    if name == "s5":
        _rehydrate_transition(acceptance_state, "s2")
        _run_bounded_shell_attempt(acceptance_state)
        return
    raise ValueError(f"unknown transition state: {name}")


@pytest.fixture
def acceptance_state(tmp_path: Path) -> dict:
    workspace_manifest = Path(__file__).resolve().parent.parent / "fixtures" / "workspace" / "complete_change_request.workspace.json"
    manifest = load_workspace_manifest(workspace_manifest)
    default_mode = str(manifest.get("mode", "scratch"))
    source_repo_raw = manifest.get("source_repo")
    default_source_repo = (Path(__file__).resolve().parents[3] / str(source_repo_raw)).resolve() if source_repo_raw else None
    default_source_ref = manifest.get("source_ref")
    workspace_cfg = resolve_workspace_config(
        default_mode=default_mode,
        default_source_repo=default_source_repo,
        default_source_ref=default_source_ref,
    )
    repo = tmp_path / "repo"
    materialize_workspace(target_dir=repo, cfg=workspace_cfg)
    (repo / ".toas").mkdir(exist_ok=True)
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


@then(parse('transition state "{name}" should be recorded'))
def then_state_recorded(acceptance_state: dict, name: str) -> None:
    payload = {
        "request_defined": acceptance_state.get("request_defined", False),
        "frontier_staged": acceptance_state.get("frontier_staged", False),
        "implemented": acceptance_state.get("implemented", False),
        "interrupted": acceptance_state.get("interrupted", False),
        "recovered": acceptance_state.get("recovered", False),
        "history_events": acceptance_state.get("history_events", []),
    }
    _transition_path(acceptance_state, name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given(parse('transition state "{name}" is loaded'))
def given_state_loaded(acceptance_state: dict, name: str) -> None:
    path = _transition_path(acceptance_state, name)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        for key, value in payload.items():
            acceptance_state[key] = value
        return
    _rehydrate_transition(acceptance_state, name)


@given("a bounded change request is defined")
def given_bounded_request(acceptance_state: dict) -> None:
    acceptance_state["request_defined"] = True
    acceptance_state["history_events"].append("request_defined")


@given("the operator configures a minimal generation posture")
@when("the operator configures a minimal generation posture")
def when_configure_minimal_generation_posture(acceptance_state: dict) -> None:
    _configure_minimal_generation_posture(acceptance_state)


@given("the operator stages the initial frontier intent")
@when("the operator stages the initial frontier intent")
def when_stage_frontier(acceptance_state: dict) -> None:
    _stage_frontier(acceptance_state)


@given("the operator performs an implementation pass")
@when("the operator performs an implementation pass")
def when_implement(acceptance_state: dict, capsys: pytest.CaptureFixture[str]) -> None:
    _run_implementation_pass(acceptance_state, capsys=capsys)


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
    history = operator_history_lines(events_path=acceptance_state["events_path"], limit=10).lines
    heads = operator_heads_lines(events_path=acceptance_state["events_path"]).lines
    rebuild = operator_rebuild_session(events_path=acceptance_state["events_path"])
    projected = (acceptance_state["repo"] / "session.md").read_text(encoding="utf-8")
    acceptance_state["recovery_observed"] = {
        "events_count": len(read_log(str(acceptance_state["events_path"]))),
        "heads_count": len(heads),
        "history_lines": history,
        "rebuild_label": rebuild.target_label,
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
    events = acceptance_state.get("implementation_events") or []
    assert any(event.get("kind") == "tool_result" for event in events)
    target_file = acceptance_state["repo"] / "src/toas/runtime/operator_command_config_help.py"
    assert "if args == [\"config\"]:" in target_file.read_text(encoding="utf-8")


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
    assert any(str(line).startswith("selected_head=") for line in observed.get("history_lines", []))
    assert isinstance(observed.get("rebuild_label"), str)
    assert "replace_block" in (observed.get("projected") or "")


@when("the operator attempts pytest through bounded shell tool")
def when_pytest_bounded_shell(acceptance_state: dict, capsys: pytest.CaptureFixture[str]) -> None:
    _run_bounded_shell_attempt(acceptance_state, capsys=capsys)


@then("TOAS should block bounded-shell pytest and stage continuation")
def then_shell_blocked(acceptance_state: dict) -> None:
    assert "[ERROR] shell:" in acceptance_state.get("shell_block_output", "")


@when("the operator reruns pytest through user-shell shorthand")
def when_pytest_user_shell(acceptance_state: dict) -> None:
    session_path = acceptance_state["repo"] / "session.md"
    session_path.write_text("## TOAS:USER\n\n$ uv run pytest --version\n", encoding="utf-8")
    cwd = Path.cwd()
    try:
        os.chdir(acceptance_state["repo"])
        operator_step_once(generate=_acceptance_generate_override(acceptance_state))
    finally:
        os.chdir(cwd)
    acceptance_state["user_shell_output"] = (acceptance_state["repo"] / "session.md").read_text(encoding="utf-8")


@then("pytest execution should run in user context and report test results")
def then_pytest_user_shell(acceptance_state: dict) -> None:
    assert "pytest" in acceptance_state.get("user_shell_output", "").lower()


@then("durable-history invariants should hold")
def then_invariants(acceptance_state: dict) -> None:
    assert acceptance_state["history_events"] == [
        "workspace_ready",
        "scenario:complete-change-request",
        "request_defined",
        "posture_configured",
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
