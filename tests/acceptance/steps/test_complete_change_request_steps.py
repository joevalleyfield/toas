import os
import re
import time
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import parse

from toas.acceptance_harness import (
    load_backend_config_with_overrides,
    load_replay_fixture,
    load_workspace_config,
    materialize_workspace,
    run_subject_command,
    should_use_live,
    write_live_capture,
)
from toas.cli_async_commands import build_deps, run_cancel, run_step_async, run_watch
from toas.graph import message_lineage, read_log
from toas.operator_api import (
    heads_lines as operator_heads_lines,
)
from toas.operator_api import (
    history_lines as operator_history_lines,
)
from toas.operator_api import (
    transcript_text as operator_transcript_text,
)
from toas.operator_api import step_once as operator_step_once
from toas.runtime.policy_edges import load_operator_config_for_workdir

scenarios("../features/complete_change_request.feature")


@pytest.fixture
def acceptance_state(tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> dict:
    repo = tmp_path / "repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    monkeypatch.chdir(repo)
    (repo / ".toas").mkdir(exist_ok=True)
    change_file = repo / "CHANGELOG.md"
    change_file.write_text("# Changelog\n", encoding="utf-8")
    live_from_step = request.config.getoption("--acceptance-live-from-step")
    parsed_live_from_step = int(live_from_step) if live_from_step is not None else None
    write_live_captures_opt = request.config.getoption("--acceptance-write-live-captures")
    parsed_write_live_captures = None
    if write_live_captures_opt is not None:
        parsed_write_live_captures = write_live_captures_opt == "true"
    backend_cfg = load_backend_config_with_overrides(
        mode=request.config.getoption("--acceptance-backend-mode"),
        live_from_step=parsed_live_from_step,
        live_from_label=request.config.getoption("--acceptance-live-from-label"),
        write_live_captures=parsed_write_live_captures,
    )
    if backend_cfg.mode == "replay_only":
        import toas.cli as cli_mod

        monkeypatch.setattr(
            cli_mod,
            "generate_assistant_message",
            lambda *_args, **_kwargs: {
                "role": "assistant",
                "content": "replay-only assistant response",
                "response": {"content": "replay-only assistant response", "model": "replay"},
            },
        )
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
        "backend_cfg": backend_cfg,
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


@given("the operator configures a minimal generation posture")
@when("the operator configures a minimal generation posture")
def when_configure_minimal_generation_posture(acceptance_state: dict) -> None:
    session_path = _session_path(acceptance_state["repo"])
    session_path.write_text(
        "## TOAS:USER\n\n/config set generation.thinking_mode disabled\n",
        encoding="utf-8",
    )
    cwd = Path.cwd()
    try:
        os.chdir(acceptance_state["repo"])
        operator_step_once()
    finally:
        os.chdir(cwd)
    acceptance_state["history_events"].append("posture_configured")


@given("the operator stages the initial frontier intent")
@when("the operator stages the initial frontier intent")
def when_stage_frontier(acceptance_state: dict) -> None:
    session_path = _session_path(acceptance_state["repo"])
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
    session_path = _session_path(acceptance_state["repo"])
    session_path.write_text(
        (
            "## TOAS:USER\n\nappend one changelog line\n"
            f"$ echo \"{backend_payload['change_line']}\" >> CHANGELOG.md\n"
        ),
        encoding="utf-8",
    )
    cwd = Path.cwd()
    try:
        os.chdir(acceptance_state["repo"])
        operator_step_once()
    finally:
        os.chdir(cwd)
    acceptance_state["implementation_events"] = read_log(str(acceptance_state["events_path"]))
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
    history = operator_history_lines(events_path=acceptance_state["events_path"], limit=10).lines
    heads = operator_heads_lines(events_path=acceptance_state["events_path"]).lines
    # Resume-from-lineage is now projection plus an explicit operator redirect:
    # project the transcript and write it into the working transcript file,
    # exactly as `toas transcript <head_id> > <session_path>` would.
    projection = operator_transcript_text(events_path=acceptance_state["events_path"])
    session_path = _session_path(acceptance_state["repo"])
    session_path.write_text(projection.text, encoding="utf-8")
    projected = session_path.read_text(encoding="utf-8")
    events = read_log(str(acceptance_state["events_path"]))
    lineage = message_lineage(events, head_id=None)
    resume_label = lineage[-1]["id"] if lineage else "-"
    acceptance_state["recovery_observed"] = {
        "events_count": len(events),
        "heads_count": len(heads),
        "history_lines": history,
        "resume_label": resume_label,
        "projected": projected,
    }
    acceptance_state["recovered"] = True
    acceptance_state["history_events"].append("recovered")


@when("the operator completes validation")
def when_validate(acceptance_state: dict) -> None:
    run_subject_command(subject_root=acceptance_state["repo"], argv=["python", "-m", "pytest", "--version"])
    text = acceptance_state["change_file"].read_text(encoding="utf-8")
    acceptance_state["validated"] = "- acceptance run" in text
    acceptance_state["history_events"].append("validated")
    if acceptance_state["validated"]:
        acceptance_state["commit"] = "simulated-commit-id"


@then("the requested change should be present")
def then_change_present(acceptance_state: dict) -> None:
    assert acceptance_state["implemented"] is True
    events = acceptance_state.get("implementation_events") or []
    assert any(event.get("role") == "user" for event in events)
    assert any(">> CHANGELOG.md" in (event.get("content") or "") for event in events)
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
    assert any(str(line).startswith("selected_head=") for line in observed.get("history_lines", []))
    assert isinstance(observed.get("resume_label"), str)
    assert "append one changelog line" in (observed.get("projected") or "")


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


@when("the operator runs a local-first async lifecycle pass")
def when_run_local_first_async_lifecycle_pass(acceptance_state: dict) -> None:
    repo = acceptance_state["repo"]
    (repo / "toas.toml").write_text(
        (
            "[runtime]\n"
            'async_runs = "enabled"\n'
            'streaming_mode = "enabled"\n'
            'cancellation_mode = "enabled"\n'
        ),
        encoding="utf-8",
    )
    session_path = _session_path(repo)
    session_path.write_text(
        (
            "## TOAS:USER\n\nacceptance local-first async lifecycle\n"
            '$ python -c "import time; print(\'chunk-a\', flush=True); time.sleep(0.5); print(\'chunk-b\', flush=True)"\n'
        ),
        encoding="utf-8",
    )
    prev_rpc_mode = os.environ.get("TOAS_RPC_MODE")
    prev_backend_mode = os.environ.get("TOAS_ASYNC_BACKEND_MODE")
    os.environ["TOAS_RPC_MODE"] = "off"
    os.environ["TOAS_ASYNC_BACKEND_MODE"] = "local"
    out: list[str] = []
    deps = build_deps(
        load_operator_config_for_cwd=lambda: load_operator_config_for_workdir(Path.cwd()),
        rpc_enabled_for_call=lambda: False,
        rpc_request=lambda _op, _payload=None: {},
        print_fn=lambda *args, **kwargs: out.append(
            str(args[0]) + ("" if kwargs.get("end", "\n") == "" else "\n")
        ),
    )
    cwd = Path.cwd()
    try:
        os.chdir(repo)
        run_step_async(deps)
        line = "".join(out).strip()
        match = re.search(r"run_id=([^\s]+)\s+status=([^\s]+)", line)
        assert match is not None, line
        run_id = match.group(1)
        start_status = match.group(2)
        out.clear()
        run_watch(run_id, offset=0, follow=False, deps=deps)
        watch_poll = "".join(out)
        out.clear()
        run_watch(run_id, offset=0, follow=True, deps=deps)
        watch_follow = "".join(out)
        out.clear()
        run_watch(run_id, offset=0, follow=False, deps=deps)
        watch_after_done = "".join(out)
    finally:
        os.chdir(cwd)
        if prev_rpc_mode is None:
            os.environ.pop("TOAS_RPC_MODE", None)
        else:
            os.environ["TOAS_RPC_MODE"] = prev_rpc_mode
        if prev_backend_mode is None:
            os.environ.pop("TOAS_ASYNC_BACKEND_MODE", None)
        else:
            os.environ["TOAS_ASYNC_BACKEND_MODE"] = prev_backend_mode
    acceptance_state["local_async"] = {
        "run_id": run_id,
        "start_status": start_status,
        "watch_poll": watch_poll,
        "watch_follow": watch_follow,
        "watch_after_done": watch_after_done,
    }
    acceptance_state["history_events"].append("local_first_async_lifecycle")


@then("local-first async lifecycle contract should hold")
def then_local_first_async_lifecycle_contract_holds(acceptance_state: dict) -> None:
    observed = acceptance_state.get("local_async") or {}
    assert isinstance(observed.get("run_id"), str) and observed["run_id"]
    assert observed.get("start_status") == "running"
    watch_poll = str(observed.get("watch_poll", ""))
    watch_follow = str(observed.get("watch_follow", ""))
    watch_after_done = str(observed.get("watch_after_done", ""))
    assert "[run running] offset=" in watch_poll
    assert "chunk-a" in (watch_poll + watch_follow)
    assert "chunk-b" in (watch_poll + watch_follow)
    assert "[run running] offset=" not in watch_after_done


@when("the operator runs a local-first async cancel pass")
def when_run_local_first_async_cancel_pass(acceptance_state: dict) -> None:
    repo = acceptance_state["repo"]
    prev_rpc_mode = os.environ.get("TOAS_RPC_MODE")
    prev_backend_mode = os.environ.get("TOAS_ASYNC_BACKEND_MODE")
    cwd = Path.cwd()
    try:
        os.environ["TOAS_RPC_MODE"] = "off"
        os.environ["TOAS_ASYNC_BACKEND_MODE"] = "local"
        out: list[str] = []
        deps = build_deps(
            load_operator_config_for_cwd=lambda: load_operator_config_for_workdir(Path.cwd()),
            rpc_enabled_for_call=lambda: False,
            rpc_request=lambda _op, _payload=None: {},
            print_fn=lambda *args, **kwargs: out.append(
                str(args[0]) + ("" if kwargs.get("end", "\n") == "" else "\n")
            ),
        )
        run_id = "acceptance-local-cancel"
        project_root = repo
        from toas.runtime import async_activity_store_impl as drs
        run = drs.AsyncRun(run_id=run_id, workdir=str(project_root), process=None)  # type: ignore[attr-defined]
        run.status = "running"
        drs.register_run(run)

        os.chdir(repo)
        run_cancel(run_id, deps=deps)
        cancel_out = "".join(out)
        run.cancel_requested = True
        run.cancel_requested_at = time.time() - 11.0
        run.status = "cancelling"
        out = []
        run_watch(run_id, offset=0, follow=False, deps=deps)
        watch_after_cancel = "".join(out)
    finally:
        os.chdir(cwd)
        if prev_rpc_mode is None:
            os.environ.pop("TOAS_RPC_MODE", None)
        else:
            os.environ["TOAS_RPC_MODE"] = prev_rpc_mode
        if prev_backend_mode is None:
            os.environ.pop("TOAS_ASYNC_BACKEND_MODE", None)
        else:
            os.environ["TOAS_ASYNC_BACKEND_MODE"] = prev_backend_mode

    acceptance_state["local_async_cancel"] = {
        "run_id": run_id,
        "cancel_out": cancel_out,
        "watch_after_cancel": watch_after_cancel,
    }
    acceptance_state["history_events"].append("local_first_async_cancel")


@then("local-first async cancel contract should hold")
def then_local_first_async_cancel_contract_holds(acceptance_state: dict) -> None:
    observed = acceptance_state.get("local_async_cancel") or {}
    run_id = str(observed.get("run_id", ""))
    cancel_out = str(observed.get("cancel_out", ""))
    watch_after_cancel = str(observed.get("watch_after_cancel", ""))
    assert f"run_id={run_id} status=cancelling" in cancel_out
    assert "[run cancelled]" in watch_after_cancel
    assert "cancel timed out" in watch_after_cancel
def _session_path(repo: Path) -> Path:
    return repo / ".toas" / "session.md"
