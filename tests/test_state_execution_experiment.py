from __future__ import annotations

import json
import shutil
import sys
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
    link.symlink_to(outside)
    with pytest.raises(ValueError):
        safe_path(root, "link")
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


def test_module_cli_runs_a_pair(tmp_path, capsys):
    result = main(["--output", str(tmp_path / "cli-run")])
    assert result == 0
    assert '"state_only"' in capsys.readouterr().out


def test_module_cli_requires_output(tmp_path):
    with pytest.raises(SystemExit):
        main([])


def test_turn_limits_and_blocked_terminal_are_distinct(tmp_path):
    root = tmp_path / "repo"
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


def test_retry_exhaustion_is_failure(tmp_path):
    root = tmp_path / "repo"
    fixture = create_fixture(root)
    adapter = ScriptedAdapter(["bad"])
    result = run_episode(root, fixture, adapter, mode="state_only", max_turns=1, max_retries=0)
    assert result["outcome"] == "failure"


def test_module_entrypoint_guard_runs(tmp_path, monkeypatch):
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
def test_offline_pair_uses_independent_fixtures_and_real_commits(tmp_path):
    result = run_pair(tmp_path / "run")
    assert result["same_initial_snapshot"] is True
    assert result["same_initial_model_input"] is True
    assert result["results"]["state_only"]["evaluator"]["pass"] is True
    assert result["results"]["history_plus_state"]["evaluator"]["pass"] is True
    assert (tmp_path / "run" / "pair.json").is_file()


@pytest.mark.skipif(shutil.which("jj") is None, reason="real jj fixture requires jj executable")
def test_invalid_response_retried_and_action_failure_is_observed(tmp_path):
    root = tmp_path / "repo"
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
def test_state_only_drops_prior_observation_but_history_arm_keeps_it(tmp_path):
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
def test_empty_continuation_does_not_replay_previous_result(tmp_path):
    root = tmp_path / "repo"
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
def test_premature_finish_fails_independent_repository_checks(tmp_path):
    root = tmp_path / "repo"
    fixture = create_fixture(root)
    adapter = ScriptedAdapter([json.dumps({"state_patch": {}, "action": {"type": "finish"}})])
    result = run_episode(root, fixture, adapter, mode="state_only", max_turns=2)
    assert result["outcome"] == "failure"
    assert result["evaluator"]["pass"] is False


@pytest.mark.skipif(shutil.which("jj") is None, reason="real jj fixture requires jj executable")
def test_wrong_partition_fails_task_boundary_evaluator(tmp_path):
    root = tmp_path / "repo"
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
