from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from toas.experiments.state_execution import (
    INITIAL_STATE,
    SOURCE_ROOT,
    LiveAdapter,
    ScriptedAdapter,
    Settings,
    _run,
    act,
    apply_patch,
    create_fixture,
    evaluate,
    main,
    parse_proposal,
    run_episode,
    run_pair,
    safe_path,
)


@pytest.fixture
def short_tmp_path():
    """jj appends long hashes; pytest's descriptive directory names exceed MAX_PATH."""
    with tempfile.TemporaryDirectory(prefix="sx-") as directory:
        yield Path(directory)


def test_patch_recursive_merge_replacement_and_null_delete():
    base = {**INITIAL_STATE, "obsolete": "remove me"}
    result = apply_patch(
        base, {"notes": {"constraints": ["new"]}, "progress": ["one"], "obsolete": None}
    )
    assert result["goal"] == INITIAL_STATE["goal"]
    assert "obsolete" not in result
    with pytest.raises(ValueError, match="state_patch must be an object"):
        apply_patch(INITIAL_STATE, None)
    with pytest.raises(ValueError, match="keys must be strings"):
        apply_patch(INITIAL_STATE, {1: "invalid"})


def test_patch_nested_notes_array_replace_and_unmentioned_survive():
    result = apply_patch(INITIAL_STATE, {"notes": {"constraints": ["new"]}, "progress": ["one"]})
    assert result["notes"]["constraints"] == ["new"]
    assert result["notes"]["accepted_decisions"] == []
    assert result["progress"] == ["one"]


def test_patch_rejects_missing_required_field_and_invalid_notes():
    with pytest.raises(ValueError):
        apply_patch(INITIAL_STATE, {"notes": None})
    with pytest.raises(ValueError):
        apply_patch(INITIAL_STATE, {"notes": {"constraints": "bad"}})
    with pytest.raises(ValueError, match="invalid field types"):
        apply_patch(INITIAL_STATE, {"progress": "bad"})


def test_parse_proposal_fences_and_plan_validation():
    assert parse_proposal('```json\n{"state_patch":{},"action":{"type":"continue"}}\n```')["action"]["type"] == "continue"
    assert parse_proposal('{"state_patch":{},"action":{"type":"plan","steps":[{"type":"inspect"}]}}')["action"]["type"] == "plan"
    for payload in (
        '{"state_patch":{},"action":null}',
        '{"state_patch":{},"action":{"type":"plan","steps":[]}}',
        '{"state_patch":{},"action":{"type":"plan","steps":[{"type":"shell"}]}}',
        '{"state_patch":{},"action":{"type":"unknown"}}',
    ):
        with pytest.raises(ValueError):
            parse_proposal(payload)


def test_script_action_is_reviewed_and_runs_in_fixture_environment(tmp_path):
    import toas.experiments.state_execution as experiment

    root = tmp_path / "fixture"
    root.mkdir()
    (root / "note.txt").write_text("before", encoding="utf-8")
    env = experiment._script_env(root)
    assert Path(env["HOME"]).is_dir() and Path(env["TMPDIR"]).is_dir()
    action = {"type": "script", "language": "python", "snippet": "print('ok')"}
    records = []
    with pytest.raises(PermissionError, match="No script reviewer"):
        act(root, action, timeout=3, review_records=records)
    assert records[-1]["approved"] is False
    approved = act(root, action, timeout=3, review_script=lambda *_: (True, "approved"), review_records=records)
    assert json.loads(approved)["stdout"] == "ok\n"
    with pytest.raises(PermissionError, match="rejected"):
        act(root, action, timeout=3, review_script=lambda *_: (False, "rejected"))
    with pytest.raises(ValueError, match="requires language"):
        act(root, {"type": "script", "language": "ruby", "snippet": ""}, timeout=3,
            review_script=lambda *_: (True, "ok"))
    with pytest.raises(RuntimeError, match="script exited 2"):
        act(root, {"type": "script", "language": "python", "snippet": "raise SystemExit(2)"},
            timeout=3, review_script=lambda *_: (True, "ok"))
    with pytest.raises(ValueError, match="cwd must be a relative path"):
        act(root, {"type": "script", "language": "python", "snippet": "pass", "cwd": 3},
            timeout=3, review_script=lambda *_: (True, "ok"))
    with pytest.raises(ValueError, match="fixture directory"):
        act(root, {"type": "script", "language": "python", "snippet": "pass", "cwd": "missing"},
            timeout=3, review_script=lambda *_: (True, "ok"))


def test_action_read_write_path_and_shell_script_variants(tmp_path):
    root = tmp_path / "fixture"
    root.mkdir()
    target = root / "note.txt"
    target.write_text("before", encoding="utf-8")
    assert act(root, {"type": "read", "path": "note.txt"}, timeout=3) == "before"
    assert act(root, {"type": "write", "path": "note.txt", "text": "after"}, timeout=3).startswith("Updated")
    assert act(root, {"type": "script", "language": "bash", "command": "printf ok"}, timeout=3,
               review_script=lambda *_: (True, "ok"))
    with pytest.raises(ValueError, match="write requires"):
        act(root, {"type": "write", "path": "note.txt"}, timeout=3)


def test_bash_runtime_selection_is_explicit_and_requires_bash_by_default(tmp_path, monkeypatch):
    import toas.experiments.state_execution as experiment

    monkeypatch.setattr(experiment, "configured_shell_runtime", lambda _root: ("/opt/own/bash", "-c"))
    assert experiment._bash_command(tmp_path, "echo hi") == ["/opt/own/bash", "-c", "echo hi"]
    monkeypatch.setattr(experiment, "configured_shell_runtime", lambda _root: ())
    monkeypatch.setattr(experiment.sys, "platform", "linux")
    monkeypatch.setattr(experiment.shutil, "which", lambda _name: "/bin/bash")
    assert experiment._bash_command(tmp_path, "echo hi") == ["/bin/bash", "-c", "echo hi"]
    monkeypatch.setattr(experiment.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="Bash runtime unavailable"):
        experiment._bash_command(tmp_path, "echo hi")
    monkeypatch.setattr(experiment.sys, "platform", "win32")
    monkeypatch.setattr(experiment, "shell_launcher_argv", lambda *a, **k: ["cmd.exe", "/c", "echo hi"])
    with pytest.raises(RuntimeError, match="Bash runtime unavailable"):
        experiment._bash_command(tmp_path, "echo hi")
    monkeypatch.setattr(experiment, "shell_launcher_argv", lambda *a, **k: ["C:/Git/bin/bash.exe", "-lc", "echo hi"])
    assert experiment._bash_command(tmp_path, "echo hi") == ["C:/Git/bin/bash.exe", "-lc", "echo hi"]
    monkeypatch.setattr(experiment, "shell_launcher_argv", lambda *a, **k: ["bash", "-lc", "echo hi"])
    monkeypatch.setattr(experiment.shutil, "which", lambda _name: "C:/Git/bin/bash.exe")
    assert experiment._bash_command(tmp_path, "echo hi") == ["C:/Git/bin/bash.exe", "-lc", "echo hi"]


def test_windows_fixture_long_path_has_actionable_diagnostic(tmp_path, monkeypatch):
    import toas.experiments.state_execution as experiment

    monkeypatch.setattr(experiment.sys, "platform", "win32")
    with pytest.raises(ValueError, match="shorter --output"):
        create_fixture(tmp_path / ("long" * 45))


def test_proposal_requires_one_bounded_action():
    assert (
        parse_proposal('{"state_patch":{},"action":{"type":"continue"}}')["action"]["type"]
        == "continue"
    )
    with pytest.raises(ValueError):
        parse_proposal('{"state_patch":{},"action":{"type":"shell"}}')
    with pytest.raises(ValueError):
        parse_proposal('{"state_patch":{},"action":{"type":"finish"},"reasoning":"secret"}')
    with pytest.raises(ValueError, match="not JSON"):
        parse_proposal("not json")


def test_scripted_adapter_reports_exhaustion():
    adapter = ScriptedAdapter([])
    with pytest.raises(RuntimeError, match="script exhausted"):
        adapter.call([], params={})


def test_live_adapter_passes_user_only_body_without_conversation_reuse():
    sent = {}

    def fake_transport(messages, *, settings, extra_body, max_tokens):
        sent.update(
            messages=messages, settings=settings, extra_body=extra_body, max_tokens=max_tokens
        )
        return {"content": "{}", "usage": None}

    adapter = LiveAdapter(settings=object(), completion=fake_transport)
    messages = [{"role": "user", "content": "procedure/state/observation"}]
    adapter.call(messages, params={"max_tokens": 23})
    assert sent["messages"] == messages
    assert sent["max_tokens"] == 23
    assert sent["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert "conversation_id" not in sent and "previous_response_id" not in sent


def test_live_adapter_exposes_configured_model():
    adapter = LiveAdapter(settings=Settings(llm_model="test-model"))
    assert adapter.model == "test-model"
    assert adapter.manifest["model"] == "test-model"
    assert "llm_api_key" not in adapter.manifest


def test_path_traversal_and_symlink_cannot_escape_fixture(tmp_path):
    root = tmp_path / "fixture"
    root.mkdir()
    outside = tmp_path / "secret"
    outside.write_text("secret")
    with pytest.raises(ValueError):
        safe_path(root, "../secret")
    link = root / "link"
    try:
        link.symlink_to(outside)
        escaped = "link"
    except OSError as exc:
        if os.name != "nt" or exc.winerror != 1314:
            raise
        # Junctions test the same resolved-path boundary without symlink privileges.
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret").write_text("secret")
        subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside_dir)],
                       check=True, capture_output=True, timeout=5)
        escaped = "link/secret"
    with pytest.raises(ValueError):
        safe_path(root, escaped)
    from toas.experiments.state_execution import act

    with pytest.raises(ValueError):
        act(root, {"type": "read", "path": "controller-only.json"}, timeout=1)


def test_fixture_and_output_roots_reject_toas_checkout(tmp_path):
    with pytest.raises(ValueError, match="outside the TOAS source checkout"):
        create_fixture(SOURCE_ROOT / "experiment-fixture")
    with pytest.raises(ValueError, match="outside the TOAS source checkout"):
        run_pair(SOURCE_ROOT / "experiment-output")


def test_bounded_action_rejects_unrecognized_action(tmp_path):
    with pytest.raises(ValueError, match="unsupported action"):
        act(tmp_path, {"type": "arbitrary_shell"}, timeout=1)
    with pytest.raises(ValueError, match="read requires"):
        act(tmp_path, {"type": "read"}, timeout=1)
    with pytest.raises(ValueError, match="write requires"):
        act(tmp_path, {"type": "write", "path": "x", "content": None}, timeout=1)
    with pytest.raises(ValueError, match="write target"):
        act(tmp_path, {"type": "write", "path": "missing", "content": "x"}, timeout=1)
    with pytest.raises(ValueError, match="commit requires"):
        act(tmp_path, {"type": "commit", "paths": [], "description": "x"}, timeout=1)


def test_missing_jj_has_clear_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setattr("toas.experiments.state_execution.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="jj executable is required"):
        _run(tmp_path, ["jj", "status"])


def test_module_cli_runs_a_pair(short_tmp_path, capsys):
    tmp_path = short_tmp_path
    result = main(["--output", str(tmp_path / "cli-run")])
    assert result == 0
    assert '"state_only"' in capsys.readouterr().out


def test_module_cli_requires_output(tmp_path):
    with pytest.raises(SystemExit):
        main([])


def test_turn_limits_and_blocked_terminal_are_distinct(short_tmp_path):
    root = short_tmp_path / "repo"
    fixture = create_fixture(root)
    adapter = ScriptedAdapter([json.dumps({"state_patch": {}, "action": {"type": "finish"}})])
    limited = run_episode(root, fixture, adapter, mode="state_only", max_turns=2, state_limit=1)
    assert limited["outcome"] == "budget_exhausted"
    observation_limited = run_episode(
        root, fixture, ScriptedAdapter([]), mode="state_only", max_turns=2, observation_limit=1
    )
    assert observation_limited["outcome"] == "budget_exhausted"
    adapter = ScriptedAdapter([json.dumps({"state_patch": {}, "action": {"type": "blocked"}})])
    blocked = run_episode(root, fixture, adapter, mode="state_only", max_turns=1)
    assert blocked["outcome"] == "blocked"


def test_retry_exhaustion_is_failure(short_tmp_path):
    root = short_tmp_path / "repo"
    fixture = create_fixture(root)
    adapter = ScriptedAdapter(["bad"])
    result = run_episode(root, fixture, adapter, mode="state_only", max_turns=1, max_retries=0)
    assert result["outcome"] == "failure"


def test_module_entrypoint_guard_runs(short_tmp_path, monkeypatch):
    tmp_path = short_tmp_path
    monkeypatch.setattr(sys, "argv", ["state_execution", "--output", str(tmp_path / "guard-run")])
    module_path = Path(__file__).resolve().parents[1] / "src/toas/experiments/state_execution.py"
    scope = {
        "__name__": "__main__",
        "__file__": str(module_path),
        "__package__": "toas.experiments",
    }
    with pytest.raises(SystemExit) as exit_info:
        exec(compile(module_path.read_text(encoding="utf-8"), str(module_path), "exec"), scope)
    assert exit_info.value.code == 0


@pytest.mark.skipif(shutil.which("jj") is None, reason="real jj fixture requires jj executable")
def test_offline_pair_uses_independent_fixtures_and_real_commits(short_tmp_path):
    tmp_path = short_tmp_path
    result = run_pair(tmp_path / "run")
    assert result["same_initial_snapshot"] is True
    assert result["same_initial_model_input"] is True
    assert result["results"]["state_only"]["evaluator"]["pass"] is True, result["results"]["state_only"]["evaluator"]["checks"]
    assert result["results"]["history_plus_state"]["evaluator"]["pass"] is True
    assert (tmp_path / "run" / "pair.json").is_file()


@pytest.mark.skipif(shutil.which("jj") is None, reason="real jj fixture requires jj executable")
def test_invalid_response_retried_and_action_failure_is_observed(short_tmp_path):
    root = short_tmp_path / "repo"
    fixture = create_fixture(root)
    adapter = ScriptedAdapter(
        [
            '{"wrong":true}',
            json.dumps({"state_patch": {}, "action": {"type": "read", "path": "../outside"}}),
            json.dumps({"state_patch": {}, "action": {"type": "finish"}}),
        ]
    )
    result = run_episode(root, fixture, adapter, mode="state_only", max_turns=3, max_retries=1)
    assert result["invalid_proposals"] == 1
    assert "Corrective observation" in adapter.captured[1]["messages"][0]["content"]
    assert "Tool 1 (read) failed" in adapter.captured[2]["messages"][0]["content"]
    assert result["captures"][1]["action_error"].startswith("ValueError: path escapes fixture root")
    assert result["captures"][1]["action_duration_ms"] >= 0


@pytest.mark.skipif(shutil.which("jj") is None, reason="real jj fixture requires jj executable")
def test_state_only_drops_prior_observation_but_history_arm_keeps_it(short_tmp_path):
    tmp_path = short_tmp_path
    roots = []
    for mode in ("state_only", "history_plus_state"):
        root = tmp_path / mode
        fixture = create_fixture(root)
        fixture["controller_secret"] = "CONTROLLER_ONLY_EVALUATOR_SENTINEL"
        (root / "prior.txt").write_text("OBSERVATION_SENTINEL_42", encoding="utf-8")
        adapter = ScriptedAdapter(
            [
                json.dumps({"state_patch": {}, "action": {"type": "read", "path": "prior.txt"}}),
                json.dumps({"state_patch": {}, "action": {"type": "continue"}}),
                json.dumps({"state_patch": {}, "action": {"type": "finish"}}),
            ]
        )
        run_episode(root, fixture, adapter, mode=mode, max_turns=3)
        later = adapter.captured[2]["messages"][0]["content"]
        roots.append(later)
        assert "CONTROLLER_ONLY_EVALUATOR_SENTINEL" not in str(adapter.captured)
    assert "OBSERVATION_SENTINEL_42" not in roots[0]
    assert "OBSERVATION_SENTINEL_42" in roots[1]


@pytest.mark.skipif(shutil.which("jj") is None, reason="real jj fixture requires jj executable")
def test_empty_continuation_does_not_replay_previous_result(short_tmp_path):
    root = short_tmp_path / "repo"
    fixture = create_fixture(root)
    adapter = ScriptedAdapter(
        [
            json.dumps({"state_patch": {}, "action": {"type": "inspect"}}),
            json.dumps({"state_patch": {}, "action": {"type": "continue"}}),
            json.dumps({"state_patch": {}, "action": {"type": "finish"}}),
        ]
    )
    run_episode(root, fixture, adapter, mode="state_only", max_turns=3)
    packet = json.loads(adapter.captured[2]["messages"][0]["content"])
    assert packet["latest_observation"] == "Tool 1 (continue) result:\n"
    assert "Working copy changes:" not in packet["latest_observation"]


@pytest.mark.skipif(shutil.which("jj") is None, reason="real jj fixture requires jj executable")
def test_premature_finish_fails_independent_repository_checks(short_tmp_path):
    root = short_tmp_path / "repo"
    fixture = create_fixture(root)
    adapter = ScriptedAdapter([json.dumps({"state_patch": {}, "action": {"type": "finish"}})])
    result = run_episode(root, fixture, adapter, mode="state_only", max_turns=2)
    assert result["outcome"] == "failure"
    assert result["evaluator"]["pass"] is False


@pytest.mark.skipif(shutil.which("jj") is None, reason="real jj fixture requires jj executable")
def test_wrong_partition_fails_task_boundary_evaluator(short_tmp_path):
    root = short_tmp_path / "repo"
    fixture = create_fixture(root)
    from toas.experiments.state_execution import act

    act(
        root,
        {
            "type": "commit",
            "paths": ["docs/guide.md"],
            "description": "docs(guide): incomplete task commit",
        },
        timeout=5,
    )
    result = evaluate(root, fixture)
    assert result["checks"]["documentation_task_in_its_commit"] is False
    assert result["checks"]["working_copy_clean"] is False
