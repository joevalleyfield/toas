import json
from types import SimpleNamespace

import pytest

from toas.config import OperatorConfig
from toas.graph import (
    append_state_step_records,
    branch_policy_provenance,
    read_log,
    state_step_records,
)
from toas.llm import Settings
from toas.operator_api import step_state_once
from toas.runtime.model_invocation_contracts import resolve_model_invocation
from toas.runtime.state_step import (
    ToolOutcomeError,
    _compound_observation,
    _log_tool_failure,
    _merge_patch,
    _normalize_tool_call_aliases,
    _operator_observation,
    _parse_state_response,
    _reconcile_tool_outcomes,
    _sanitize_projected_tool_outcomes,
    _user_input_observations,
    _user_observation_inputs,
    _user_result_observations,
    build_state_step_packet,
    condense_inert_blocks,
    expand_inert_blocks,
    find_lineage_state_snapshot,
    initial_state,
    is_state_turn_marker,
    materialize_state_turns,
    observation_with_user_turns,
    parse_state_turn,
    partition_state_transcript,
    reconcile_state_lineage,
    render_state_turn,
    seed_state_turn,
    state_delta,
    state_records,
    step_state,
    transcript_observation_with_tool_outcomes,
    user_state_edit_needed,
)
from toas.runtime.step_generation_runtime import GenerationRunner


@pytest.mark.parametrize("format", ["yaml", "markdown"])
def test_state_turn_round_trips_normalized_state_and_observation(format):
    state = {"goal": "inspect", "notes": {"constraints": ["local"]}}
    observation = {"kind": "user_input", "content": "start"}
    rendered = render_state_turn(state, observation=observation, format=format)
    parsed = parse_state_turn(rendered)
    assert parsed["state"] == state
    assert parsed["observation"] == observation


def test_partition_selects_latest_state_turn_and_preserves_surrounding_conversation():
    transcript = (
        "## TOAS:USER\n\nEarlier.\n\n"
        + render_state_turn({"goal": "old"})
        + "\n## TOAS:STATE/1\n\nstate: {goal: current}\n\n"
        + "## TOAS:USER\n\nLater conversation.\n"
    )
    prefix_turns, state_turn, suffix_turns = partition_state_transcript(transcript)
    parsed = parse_state_turn(state_turn)
    assert parsed["state"] == {"goal": "current"}
    assert prefix_turns[0]["content"] == "Earlier."
    assert suffix_turns[0]["content"] == "Later conversation."


def test_partition_collects_trailing_user_and_control_turns():
    transcript = (
        "## TOAS:STATE/1\n\nstate: {goal: inspect}\n\n"
        "## TOAS:USER\n\nRead the manifest.\n\n"
        "## TOAS:CONTROL\n\n/queue approve q1\n"
    )

    _prefix, state_turn, suffix_turns = partition_state_transcript(transcript)
    parsed = parse_state_turn(state_turn)
    input_turns = [turn for turn in suffix_turns if turn.get("role") in {"user", "control"}]
    observation = observation_with_user_turns(parsed.get("observation"), input_turns)

    assert input_turns == [
        {"role": "user", "content": "Read the manifest."},
        {"role": "control", "content": "/queue approve q1"},
    ]
    assert observation["user_inputs"] == [{"content": "Read the manifest."}]
    assert "/queue approve q1" not in str(observation)


def test_control_results_are_observed_without_projecting_control_text():
    observation = observation_with_user_turns(
        {"kind": "toas.compound-observation/1", "operator_observation": "existing note",
         "control_results": [{"content": "prior result"}]},
        [
            {"role": "user", "content": "Inspect this."},
            {
                "role": "control",
                "content": "/pwd\n\n## RESULT\n\n/work/project",
            },
        ],
    )

    assert observation["user_inputs"] == [{"content": "Inspect this."}]
    assert observation["control_results"] == [
        {"content": "prior result"},
        {"content": "/work/project", "source": "control"}
    ]
    assert "/pwd" not in json.dumps(observation)


def test_state_diff_turn_round_trips(format="markdown"):
    patch = {"progress": ["read source"]}
    assert (
        parse_state_turn(render_state_turn({}, state_patch=patch, format=format))["state_patch"]
        == patch
    )


def test_seed_leaves_goal_open_for_operator_edit():
    state = initial_state()
    assert state["goal"] == ""
    assert parse_state_turn(seed_state_turn(format="markdown"))["state"] == state


def test_operator_api_route_and_explicit_model_packet_boundary(tmp_path):
    result = step_state_once(
        events_path=tmp_path / "events.jsonl",
        state={"goal": "inspect"},
        observation="start",
        generate=lambda _packet: {"content": '{"state_patch":{},"tool_calls":[]}'},
        execute_call=lambda _call: pytest.fail("inference must not execute tools"),
    )
    assert result["phase"] == "infer"
    path = tmp_path / "invocation-events.jsonl"
    path.write_text("", encoding="utf-8")
    request = [{"role": "user", "content": '{"state":{"goal":"x"}}'}]
    invocation = resolve_model_invocation(
        working=[],
        request_messages=request,
        operator_config=OperatorConfig(),
        base_settings=Settings(llm_base_url="http://model", llm_model="base"),
        settings_sources={"model": "default", "endpoint": "default", "api_key": "default", "transport": "default"},
        policy=type("Policy", (), {"extra_body": {}})(),
        events_path=path,
        project_messages=lambda _working: pytest.fail("state packet must bypass conversation projection"),
    )
    assert invocation.messages == request


def test_graph_state_writer_rejects_non_state_record_and_projection_skips_malformed_payload(tmp_path):
    path = tmp_path / "events.jsonl"
    with pytest.raises(ValueError, match="unsupported record kind"):
        append_state_step_records(str(path), [{"kind": "assistant", "role": "assistant", "content": "bad"}])
    projected = branch_policy_provenance(
        [
            {"id": "m1", "role": "user", "content": "hi"},
            {"kind": "config_override", "related_to": "m1", "payload": []},
        ],
        head_id="m1",
    )
    assert projected["domains"] == {}
    with pytest.raises(ValueError, match="invalid tool outcome status"):
        ToolOutcomeError("retry", "must not retry")


def test_inference_accepts_patch_and_records_pending_calls_without_execution(tmp_path):
    events = tmp_path / "events.jsonl"
    observed = []
    packet_seen = []

    def generate(packet):
        packet_seen.append(packet)
        return {
            "content": json.dumps(
                {
                    "state_patch": {"notes": {"done": True}},
                    "tool_calls": [
                        {"tool_name": "echo", "args": {"text": "one"}},
                        {"tool_name": "echo", "args": {"text": "two"}},
                    ],
                }
            )
        }

    result = step_state(
        events_path=events,
        state={"goal": "inspect", "notes": {}},
        observation={"kind": "compound", "parts": ["latest"]},
        generate=generate,
        execute_call=lambda call: observed.append(call),
    )
    assert result["phase"] == "infer"
    assert result["state"] == {"goal": "inspect", "notes": {"done": True}}
    assert result["status"] == "pending"
    assert observed == []
    assert packet_seen[0]["observation"] == {
        "operator_observation": {"kind": "compound", "parts": ["latest"]},
        "tool_outcomes": [],
    }
    assert packet_seen[0]["tools"]["available"]
    assert [r["kind"] for r in read_log(str(events))] == [
        "state_transition",
        "state_diff",
        "state_snapshot",
        "state_observation",
        "state_tool_request",
    ]
    assert not any("role" in r for r in read_log(str(events)))


def test_next_step_executes_pending_batch_once_and_records_provenance(tmp_path):
    events = tmp_path / "events.jsonl"
    state = {"goal": "inspect"}
    response = {
        "content": json.dumps(
            {
                "state_patch": {"progress": ["started"]},
                "tool_calls": [
                    {"tool_name": "echo", "args": {"text": "one"}},
                    {"tool_name": "echo", "args": {"text": "two"}},
                ],
            }
        )
    }
    step_state(
        events_path=events,
        state=state,
        observation="first",
        generate=lambda _p: response,
        execute_call=lambda _c: None,
    )
    executed = []
    result = step_state(
        events_path=events,
        state={"goal": "operator edit"},
        observation="user edit",
        generate=lambda _p: pytest.fail("pending batch must run before inference"),
        execute_call=lambda call: executed.append(call["args"]["text"]) or {"ok": True},
    )
    assert result["status"] == "completed"
    assert executed == ["one", "two"]
    assert all(
        r["transition_id"] == result["transition_id"]
        for r in state_step_records(str(events))
        if r["kind"] == "state_tool_result"
    )
    packet_seen = []
    followup = step_state(
        events_path=events,
        state=state,
        observation="second",
        generate=lambda p: (
            packet_seen.append(p) or {"content": '{"state_patch":{},"tool_calls":[]}'}
        ),
        execute_call=lambda _c: None,
    )
    assert followup["phase"] == "infer"
    assert len(packet_seen[0]["observation"]["tool_outcomes"]) == 2
    assert executed == ["one", "two"]


def test_invalid_response_preserves_request_and_response_evidence(tmp_path):
    events = tmp_path / "events.jsonl"
    with pytest.raises(ValueError, match="invalid state-step JSON"):
        step_state(
            events_path=events,
            state={"goal": "keep"},
            observation={"source": "operator", "text": "inspect"},
            generate=lambda _p: {"content": "not json"},
            execute_call=lambda _c: None,
        )
    transition = next(record for record in read_log(str(events)) if record.get("kind") == "state_transition")
    assert transition["kind"] == "state_transition"
    assert transition["status"] == "failed"
    assert transition["state_before"] == {"goal": "keep"}
    assert transition["request_packet"]["state"] == {"goal": "keep"}
    assert transition["request_packet"]["observation"]["operator_observation"] == {
        "source": "operator",
        "text": "inspect",
    }
    assert transition["response_content"] == "not json"
    assert "response preview='not json'" in transition["error"]


def test_running_batch_is_marked_indeterminate_and_never_retried(tmp_path):
    events = tmp_path / "events.jsonl"
    append_state_step_records(
        str(events),
        [
            {
                "kind": "state_transition",
                "transition_id": "st_crash",
                "status": "running",
                "tool_calls": [{"tool_name": "shell"}],
            }
        ],
    )
    calls = []
    result = step_state(
        events_path=events,
        state={},
        observation=None,
        generate=lambda _p: pytest.fail("must not infer while outcome is unknown"),
        execute_call=lambda call: calls.append(call),
    )
    assert result["status"] == "indeterminate"
    assert calls == []
    assert state_step_records(str(events))[-1]["status"] == "indeterminate"


def test_parser_rejects_invalid_turns_and_renderer_rejects_unknown_format():
    for text, message in [
        ("ordinary transcript", "must begin"),
        ("## TOAS:STATE/1\n\n{invalid: yaml: [", "invalid YAML"),
        ("## TOAS:STATE/1\n\n- item", "mapping"),
        ("## TOAS:STATE/1\n\nobservation: hi", "state mapping"),
        ("## TOAS:STATE-DIFF/1\n\nstate: {}", "state_patch mapping"),
    ]:
        with pytest.raises(ValueError, match=message):
            parse_state_turn(text)
    with pytest.raises(ValueError, match="format"):
        render_state_turn({}, format="toml")


@pytest.mark.parametrize(
    "content, message",
    [
        (None, "must contain JSON text"),
        ("[]", "must be a JSON object"),
        ('{"state_patch": [], "tool_calls": []}', "requires an object"),
        ('{"state_patch": {}, "tool_calls": [1]}', "requires an object"),
        ('{"state_patch": {}, "tool_calls": [], "outcome": "wait"}', "must be 'continue'"),
        (
            '{"state_patch": {}, "tool_calls": [{}], "outcome": "complete"}',
            "cannot request tool calls",
        ),
    ],
)
def test_invalid_response_variants_are_rejected_with_diagnostic_history(tmp_path, content, message):
    events = tmp_path / "events.jsonl"
    answer = content if content is None else {"content": content, "_llm_call": {"requested_model": "test"}}
    with pytest.raises(ValueError, match=message):
        step_state(
            events_path=events,
            state={},
            observation=None,
            generate=lambda _p: answer,
            execute_call=lambda _c: None,
        )
    transition = next(record for record in read_log(str(events)) if record.get("kind") == "state_transition")
    assert transition["status"] == "failed"
    assert transition["failure_phase"] == "response_validation"
    assert "request_packet" in transition


def test_sparse_patch_deletes_keys_and_records_model_call_evidence(tmp_path):
    events = tmp_path / "events.jsonl"
    result = step_state(
        events_path=events,
        state={"keep": 1, "remove": 2},
        observation=None,
        generate=lambda _p: {
            "content": '{"state_patch":{"remove":null},"tool_calls":[]}',
            "_llm_call": {"requested_model": "model-a", "response_model": "model-b"},
        },
        execute_call=lambda _c: None,
    )
    transition = state_step_records(str(events))[0]
    assert result["state"] == {"keep": 1}
    assert transition["model_call"] == {"requested_model": "model-a", "response_model": "model-b"}
    assert state_records(events) == state_step_records(str(events))
    llm_calls = [r for r in read_log(str(events)) if r.get("kind") == "llm_call"]
    assert len(llm_calls) == 1
    assert llm_calls[0]["payload"]["requested_model"] == "model-a"
    assert llm_calls[0]["payload"]["transition_id"] == transition["transition_id"]


def test_terminal_outcome_prevents_implicit_followup_inference(tmp_path):
    events = tmp_path / "events.jsonl"
    result = step_state(
        events_path=events,
        state={"goal": "finish"},
        observation="done",
        generate=lambda _p: {"content": '{"state_patch":{},"tool_calls":[],"outcome":"complete"}'},
        execute_call=lambda _c: None,
    )
    assert result["outcome"] == "complete"
    next_result = step_state(
        events_path=events,
        state={"goal": "finish"},
        observation="still done",
        generate=lambda _p: pytest.fail("terminal outcome must stop inference"),
        execute_call=lambda _c: None,
    )
    assert next_result["phase"] == "terminal"
    edited = step_state(
        events_path=events,
        state={"goal": "new goal"},
        observation="restart from edited horizon",
        generate=lambda _p: {"content": '{"state_patch":{},"tool_calls":[]}'},
        execute_call=lambda _c: None,
    )
    assert edited["phase"] == "infer"


def test_failed_tool_call_is_recorded_and_later_calls_are_not_started(tmp_path):
    events = tmp_path / "events.jsonl"
    step_state(
        events_path=events,
        state={},
        observation=None,
        generate=lambda _p: {
            "content": (
                '{"state_patch":{},"tool_calls":['
                '{"tool_name":"read_file","args":{"path":"first.txt"}},'
                '{"tool_name":"read_file","args":{"path":"second.txt"}}]}'
            )
        },
        execute_call=lambda _c: None,
    )
    calls = []

    def fail(call):
        calls.append(call)
        raise RuntimeError("denied")

    result = step_state(
        events_path=events, state={}, observation=None, generate=lambda _p: None, execute_call=fail
    )
    assert result["status"] == "failed"
    assert len(calls) == 1
    assert state_step_records(str(events))[-2]["error"] == "denied"


def test_step_state_tool_failure_retains_tool_name_traceback_and_logs(tmp_path):
    events = tmp_path / ".toas" / "events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    step_state(
        events_path=events,
        state={},
        observation=None,
        generate=lambda _p: {
            "content": '{"state_patch":{},"tool_calls":[{"tool_name":"get_structure","args":{"path":"."}}]}'
        },
        execute_call=lambda _c: None,
    )

    def fail_with_syntax_error(call):
        raise SyntaxError("invalid syntax in test.py", ("test.py", 3, 1, "bad syntax"))

    result = step_state(
        events_path=events, state={}, observation=None, generate=lambda _p: None, execute_call=fail_with_syntax_error
    )
    assert result["status"] == "failed"
    outcomes = result["outcomes"]
    assert len(outcomes) == 1
    assert outcomes[0]["tool_name"] == "get_structure"
    assert "test.py" in outcomes[0]["error"]
    assert "Traceback" in outcomes[0]["traceback"]

    records = state_step_records(str(events))
    tool_result_record = [r for r in records if r.get("kind") == "state_tool_result"][0]
    assert tool_result_record["tool_name"] == "get_structure"
    assert "test.py" in tool_result_record["error"]
    assert "Traceback" in tool_result_record["traceback"]

    error_log_file = tmp_path / ".toas" / "error.log"
    assert error_log_file.exists()
    logged_lines = error_log_file.read_text(encoding="utf-8").strip().splitlines()
    assert any("tool_execution_failed" in line and "get_structure" in line for line in logged_lines)


def test_state_step_small_helpers_cover_sparse_and_observation_edges(tmp_path):
    from toas.runtime import state_step as module

    assert _parse_state_response('```json\n{"ok": true}\n```') == {"ok": True}
    with pytest.raises(ValueError, match="missing callable name"):
        _normalize_tool_call_aliases([{"args": {}}])
    assert state_delta(
        {"gone": 1, "same": {"x": 1, "y": 2}, "changed": [1]},
        {"same": {"x": 3}, "changed": [2], "new": True},
    ) == {"changed": [2], "gone": None, "new": True, "same": {"x": 3, "y": None}}
    assert _merge_patch({"nested": {"keep": 1}}, {"nested": {"drop": None}}) == {
        "nested": {"keep": 1}
    }
    assert _operator_observation({"kind": "toas.compound-observation/1", "operator_observation": "note"}) == "note"
    compound = {"kind": "toas.compound-observation/1", "user_inputs": [{"content": "x"}, 7]}
    assert _user_observation_inputs(compound) == [{"content": "x"}]
    assert _user_observation_inputs("plain") == []
    assert transcript_observation_with_tool_outcomes(
        {"kind": "toas.compound-observation/1", "operator_observation": "note",
         "user_inputs": [{"content": "prompt"}], "control_results": [{"content": "result"}]},
        [{"status": "completed"}],
    ) == {
        "kind": "toas.compound-observation/1", "operator_observation": "note",
        "tool_outcomes": [{"status": "completed"}], "user_inputs": [{"content": "prompt"}],
        "control_results": [{"content": "result"}],
    }
    assert transcript_observation_with_tool_outcomes("plain", []) == {
        "kind": "toas.compound-observation/1", "operator_observation": "plain", "tool_outcomes": []
    }
    fenced = '```text block_id=ib_x\nbody\n```'
    ref = '```text block_id=ib_x\n(ref: ib_x)\n```'
    assert condense_inert_blocks(ref) == ref
    assert expand_inert_blocks('```text block_id=ib_missing\n(ref: ib_missing)\n```', {}) .endswith('```')
    assert expand_inert_blocks('```text lines=1-2 block_id=ib_x\n(ref: ib_x)\n```', {"ib_x": "body"}).endswith('(ref: ib_x)\n```')
    records = [{"payload": {"stdout": fenced}, "content": '```text block_id=ib_y\nother\n```'}]
    assert module.extract_inert_blocks_by_id(records) == {"ib_x": "body", "ib_y": "other"}
    assert module.extract_inert_blocks_by_id(fenced) == {"ib_x": "body"}
    _log_tool_failure(path=tmp_path / "events.jsonl", transition_id="t", index=0,
                      tool_name="shell", call={}, status="failed", error="x", traceback=None)


def test_user_state_edit_detection_compares_snapshot_and_observation(tmp_path):
    events = tmp_path / "events.jsonl"
    assert user_state_edit_needed(events_path=events, state={"goal": "new"}, observation=None,
                                  has_user_tool_calls=False)
    append_state_step_records(str(events), [
        {"kind": "state_snapshot", "state": {"goal": "same"}},
        {"kind": "state_observation", "observation": {"kind": "toas.compound-observation/1",
                                                           "operator_observation": "old"}},
    ])
    assert not user_state_edit_needed(events_path=events, state={"goal": "same"}, observation="old",
                                     has_user_tool_calls=False)
    assert user_state_edit_needed(events_path=events, state={"goal": "same"}, observation="old",
                                  has_user_tool_calls=True)
    assert user_state_edit_needed(events_path=events, state={"goal": "same"}, observation="new",
                                  has_user_tool_calls=False)


def test_state_step_user_batch_consolidation_and_idempotency(tmp_path):
    events = tmp_path / "events.jsonl"
    calls = []
    result = step_state(
        events_path=events, state={"goal": "new"}, observation="look",
        user_tool_calls=[{"tool_name": "echo", "args": {"text": "hi"}}],
        user_turn_digest="user-turn-1", generate=lambda _: pytest.fail("user intent does not infer"),
        execute_call=lambda _: None,
        execute_user_call=lambda call: calls.append(call) or [{"role": "result", "content": "hi"}],
    )
    assert result["phase"] == "consolidate_user" and result["status"] == "completed"
    assert calls[0]["tool_name"] == "echo"
    repeated = step_state(
        events_path=events, state={"goal": "new"}, observation="edited",
        user_turn_digest="user-turn-1", generate=lambda _: pytest.fail("digest replay must not execute"),
        execute_call=lambda _: pytest.fail("digest replay must not execute"),
    )
    assert repeated["transition_id"] == result["transition_id"]
    assert repeated["observation"]["operator_observation"] == "look"


def test_user_batch_observation_projects_user_inputs(tmp_path):
    events = tmp_path / "events.jsonl"
    result = step_state(
        events_path=events, state={},
        observation={"kind": "toas.compound-observation/1", "operator_observation": "note",
                     "user_inputs": [{"content": "follow this"}]},
        user_turn_digest="with-input", generate=lambda _: None, execute_call=lambda _: None,
    )
    assert result["observation"]["user_inputs"] == [{"content": "follow this"}]


@pytest.mark.parametrize("failure_kind", ["payload", "typed", "exception", "unavailable"])
def test_state_step_user_batch_records_failure_and_stops(failure_kind, tmp_path):
    events = tmp_path / "events.jsonl"
    def execute(_call):
        if failure_kind == "payload":
            return [{"payload": {"ok": False, "outcome": "unexpected", "summary": "stopped",
                                 "tool_name": "shell", "traceback": "trace"}}]
        if failure_kind == "typed":
            raise ToolOutcomeError("indeterminate", "unknown", tool_name="python", traceback="tb")
        raise RuntimeError("denied")
    result = step_state(
        events_path=events, state={}, observation=None,
        user_tool_calls=[{"tool_name": "echo", "args": {}}, {"tool_name": "echo", "args": {}}],
        user_turn_digest="digest", generate=lambda _: None, execute_call=lambda _: None,
        execute_user_call=None if failure_kind == "unavailable" else execute,
    )
    assert result["status"] in {"cancelled", "indeterminate", "failed"}
    assert len(result["outcomes"]) == 1
    assert [r for r in state_step_records(str(events)) if r["kind"] == "state_tool_result"]


def test_state_step_preview_and_pending_batch_error_paths(tmp_path):
    from toas.runtime.state_step import preview_state_request
    events = tmp_path / "events.jsonl"
    assert preview_state_request(events_path=events, state={}, observation=None)["phase"] == "infer"
    step_state(events_path=events, state={}, observation=None,
               generate=lambda _: {"content": '```json\n{"state_patch":{},"tool_calls":[{"tool_name":"echo","args":{}}]}\n```'},
               execute_call=lambda _: None, message_id="message-id")
    preview = preview_state_request(events_path=events, state={}, observation=None)
    assert preview["phase"] == "execute_batch"
    err = step_state(events_path=events, state={}, observation=None, generate=lambda _: None,
                     execute_call=lambda _: (_ for _ in ()).throw(
                         ToolOutcomeError("cancelled", "stopped", tool_name="echo", traceback="tb")))
    assert err["status"] == "cancelled"
    assert preview_state_request(events_path=events, state={}, observation=None)["phase"] == "infer"


def test_state_step_user_running_recovery_and_pending_running_recovery(tmp_path):
    events = tmp_path / "events.jsonl"
    append_state_step_records(str(events), [{"kind": "state_transition", "transition_id": "u",
        "source": "user", "user_turn_digest": "d", "status": "running", "state_after": {},
        "observation": {}, "tool_calls": [{"tool_name": "echo"}]}])
    recovered = step_state(events_path=events, state={}, observation="new", user_turn_digest="d",
        generate=lambda _: None, execute_call=lambda _: None)
    assert recovered["status"] == "indeterminate"
    append_state_step_records(str(events), [{"kind": "state_transition", "transition_id": "m",
        "source": "model", "status": "running", "tool_calls": [{"tool_name": "echo"}]}])
    no_retry = step_state(events_path=events, state={}, observation=None, generate=lambda _: None,
                          execute_call=lambda _: pytest.fail("running batch must not retry"))
    assert no_retry["status"] == "indeterminate"


def test_user_recovery_uses_prior_failures_and_builds_missing_observation(tmp_path):
    events = tmp_path / "events.jsonl"
    append_state_step_records(str(events), [
        {"kind": "state_transition", "transition_id": "u1", "source": "user",
         "user_turn_digest": "failed", "status": "running", "state_after": {},
         "tool_calls": [{"tool_name": "echo"}]},
        {"kind": "state_tool_result", "transition_id": "u1", "status": "cancelled", "error": "stop"},
        {"kind": "state_transition", "transition_id": "u2", "source": "user",
         "user_turn_digest": "done", "status": "completed", "state_after": {},
         "observation": "carried note", "tool_calls": []},
        {"kind": "state_transition", "transition_id": "u3", "source": "user",
         "user_turn_digest": "all-done", "status": "running", "state_after": {},
         "tool_calls": [{"tool_name": "echo"}]},
        {"kind": "state_tool_result", "transition_id": "u3", "status": "completed"},
    ])
    failed = step_state(events_path=events, state={}, observation=None, user_turn_digest="failed",
        generate=lambda _: None, execute_call=lambda _: None)
    assert failed["status"] == "cancelled"
    done = step_state(events_path=events, state={}, observation="fallback", user_turn_digest="done",
        generate=lambda _: None, execute_call=lambda _: None)
    assert done["observation"]["operator_observation"] == "fallback"
    completed = step_state(events_path=events, state={}, observation=None, user_turn_digest="all-done",
        generate=lambda _: None, execute_call=lambda _: None)
    assert completed["status"] == "completed"


def test_state_parser_error_shapes_and_renderer_user_calls():
    for content, message in (
        ("instructions: 1\nstate: {}", "instructions must be a string"),
        ("user_tool_calls: [1]\nstate: {}", "user_tool_calls must be an array"),
        ("pending_tools: [1]\nstate: {}", "pending_tools must be an array"),
        ("tool_calls: [1]\nstate: {}", "tool_calls must be an array"),
    ):
        with pytest.raises(ValueError, match=message):
            parse_state_turn("## TOAS:STATE/1\n\n" + content)
    parsed = parse_state_turn(render_state_turn(
        {}, user_tool_calls=[{"tool_name": "echo"}], pending_tools=[{"tool_name": "read_file"}]
    ))
    assert parsed["user_tool_calls"] == [{"tool_name": "echo"}]
    assert parsed["pending_tools"] == parsed["tool_calls"] == [{"tool_name": "read_file"}]


def test_state_outcome_reconciliation_handles_dict_scalar_and_unmatched_results():
    prior = [
        {"index": 9, "result": {"role": "result", "content": "old", "payload": {"secret": 1}}},
        {"index": 10, "result": "scalar"},
    ]
    result = _reconcile_tool_outcomes(prior, ["one", "two", "extra"])
    assert result[0]["index"] == 0
    assert result[0]["result"] == [{"role": "result", "content": "one"}]
    assert result[1]["result"] == [{"role": "result", "content": "two", "projection_lane": "user"}]
    assert result[2]["source"] == "user" and result[2]["result"][0]["content"] == "extra"
    assert _reconcile_tool_outcomes([{"result": [None, {}, {}]}], ["only"])[0]["result"] == [
        {"role": "result", "content": "only", "projection_lane": "user"}
    ]
    assert _sanitize_projected_tool_outcomes([{"result": ["kept", {"content": "x", "payload": {"internal": 1}}]}]) == [
        {"result": ["kept", {"content": "x"}]}
    ]


def test_compound_observation_reconciles_transcript_and_prior_records(tmp_path):
    events = tmp_path / "events.jsonl"
    append_state_step_records(str(events), [
        {"kind": "state_transition", "transition_id": "t", "status": "failed",
         "tool_calls": [{"tool_name": "echo"}]},
        {"kind": "state_tool_result", "transition_id": "t", "status": "failed",
         "result": [{"role": "result", "content": "old"}]},
    ])
    observation = _compound_observation(
        state_records(str(events)), {"kind": "toas.compound-observation/1", "operator_observation": "operator",
                                    "user_inputs": [{"content": "prompt"}]}, session_text=(
            "## TOAS:STATE/1\n\nstate: {}\n\n## TOAS:USER\n\nnew prompt\n\n## RESULT\n\nnew result"
        ),
    )
    assert observation["operator_observation"] == "operator"
    assert observation["user_inputs"] == [{"content": "prompt"}]
    assert observation["tool_outcomes"][0]["result"][0]["content"] == "new result"
    assert _compound_observation([], {"kind": "toas.compound-observation/1", "operator_observation": "x"})["operator_observation"] == "x"


def test_compound_observation_prefers_prior_user_outcome_and_covers_fallback_sources():
    from toas.runtime.state_step import _compound_observation
    user_history = [
        {"kind": "state_transition", "transition_id": "u", "source": "user", "status": "completed"},
        {"kind": "state_observation", "transition_id": "u", "observation": {"source": "prior"}},
    ]
    assert _compound_observation(user_history, "ignored")["source"] == "prior"
    prior_outcome = [{"kind": "state_transition", "transition_id": "m", "status": "failed"},
                     {"kind": "state_tool_result", "transition_id": "m", "status": "failed"}]
    assert _compound_observation(prior_outcome, {"user_results": ["result"]})["tool_outcomes"][0]["status"] == "failed"
    assert _compound_observation([], {"tool_outcomes": [{"status": "kept"}]})["tool_outcomes"][0]["status"] == "kept"
    assert _compound_observation([], {"control_results": [{"content": "control"}]})["control_results"] == [
        {"content": "control"}
    ]
    assert _compound_observation([], "plain", session_text="not a state transcript")["tool_outcomes"] == []
    assert _compound_observation([], {"tool_outcomes": [{"status": "kept"}]},
                                 session_text="## TOAS:STATE/1\n\nstate: {}")["tool_outcomes"] == [
        {"status": "kept"}
    ]


def test_preview_terminal_and_invalid_tool_call_evidence(tmp_path):
    from toas.runtime.state_step import preview_state_request
    events = tmp_path / "events.jsonl"
    step_state(events_path=events, state={"goal": "done"}, observation=None,
        generate=lambda _: {"content": '{"state_patch":{},"tool_calls":[],"outcome":"complete"}'},
        execute_call=lambda _: None)
    assert preview_state_request(events_path=events, state={"goal": "done"}, observation=None)["phase"] == "terminal"
    with pytest.raises(ValueError, match="missing callable name"):
        step_state(events_path=events, state={"goal": "next"}, observation=None,
            generate=lambda _: {"content": '{"state_patch":{},"tool_calls":[{"args":{}}]}'},
            execute_call=lambda _: None)
    invalid = read_log(str(events))[-1]
    assert invalid["failure_phase"] == "response_validation"


def test_log_tool_failure_swallows_logging_errors_and_state_lineage_empty_paths(monkeypatch, tmp_path):
    from toas.runtime import async_activity_store_impl
    monkeypatch.setattr(async_activity_store_impl, "error_log", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk")))
    _log_tool_failure(path=tmp_path / "events.jsonl", transition_id="t", index=0,
                      tool_name="echo", call={}, status="failed", error="x", traceback="tb")
    assert materialize_state_turns(events_path=tmp_path / "events.jsonl", unmaterialized_turns=[], parent_id=None) == []



def test_generation_runner_resolves_and_executes_explicit_state_packet(monkeypatch, tmp_path):
    from toas.runtime import step_generation_runtime

    runner = GenerationRunner.__new__(GenerationRunner)
    runner.deps = SimpleNamespace(
        project_llm_input_from_messages=lambda _messages: pytest.fail(
            "conversation projection must be skipped"
        ),
        resolve_selected_endpoint=lambda _working: None,
        resolve_selected_model=lambda _working: None,
        resolve_secret=lambda **_kwargs: "secret",
    )
    runner.operator_config = object()
    runner.base_settings = object()
    runner.settings_sources = {"test": "test"}
    runner.policy = object()
    runner.events_path = tmp_path / "events.jsonl"
    runner.llm_stream_mode = None
    captured = {}
    monkeypatch.setattr(
        step_generation_runtime,
        "resolve_model_invocation",
        lambda **kwargs: captured.update(kwargs) or "plan",
    )
    assert runner.prepare_state_request({"state": {"goal": "x"}}) == "plan"
    assert captured["working"] == []
    assert json.loads(captured["request_messages"][0]["content"]) == {"state": {"goal": "x"}}

    monkeypatch.setattr(GenerationRunner, "prepare_state_request", lambda _self, _packet: "plan")
    monkeypatch.setattr(GenerationRunner, "execute_with_retry", lambda _self, _plan: "result")
    monkeypatch.setattr(
        GenerationRunner,
        "build_artifacts",
        lambda _self, _plan, _result: {"content": "answer"},
    )
    assert runner.generate_state_packet({"state": {}}) == {"content": "answer"}


def test_state_turn_parses_and_renders_state_ordinal():
    assert is_state_turn_marker("## TOAS:STATE/1")
    assert is_state_turn_marker("## TOAS:STATE/42")
    assert is_state_turn_marker("## TOAS:STATE-DIFF/3")
    assert not is_state_turn_marker("## TOAS:USER")

    rendered = render_state_turn({"goal": "step 3"}, state_number=3)
    assert rendered.startswith("## TOAS:STATE/3\n")
    parsed = parse_state_turn(rendered)
    assert parsed["state_number"] == 3
    assert parsed["state"] == {"goal": "step 3"}

    diff_rendered = render_state_turn({}, state_patch={"goal": "patched"}, state_number=4)
    assert diff_rendered.startswith("## TOAS:STATE-DIFF/4\n")
    parsed_diff = parse_state_turn(diff_rendered)
    assert parsed_diff["state_number"] == 4
    assert parsed_diff["state_patch"] == {"goal": "patched"}


def test_state_turn_renders_and_parses_pending_tools():
    tools = [{"tool_name": "get_structure", "args": {"path": "tasks/open"}}]
    rendered = render_state_turn({"goal": "explore"}, pending_tools=tools, state_number=2)
    assert "pending_tools:" in rendered
    assert "get_structure" in rendered
    parsed = parse_state_turn(rendered)
    assert parsed["pending_tools"] == tools
    assert parsed["tool_calls"] == tools

    # Empty tools are omitted
    rendered_empty = render_state_turn({"goal": "explore"}, pending_tools=[], state_number=2)
    assert "pending_tools:" not in rendered_empty


def test_condense_and_expand_inert_blocks_with_block_id():
    full_output = (
        "## RESULT\n\n"
        "[OK] shell: exit=0\n"
        "stdout:\n"
        '````markdown toas-output kind=file source="cat file.txt" potency=inert path=file.txt block_id=ib_1234567890abcdef\n'
        "first line\n"
        "second line\n"
        "````"
    )
    condensed = condense_inert_blocks(full_output)
    assert "(ref: ib_1234567890abcdef)" in condensed
    assert "first line" not in condensed

    # Expanding restores original content
    blocks_by_id = {"ib_1234567890abcdef": "first line\nsecond line"}
    expanded = expand_inert_blocks(condensed, blocks_by_id)
    assert expanded == full_output


def test_build_state_step_packet_expands_condensed_inert_references(tmp_path):
    events = tmp_path / "events.jsonl"
    events.touch()
    session_text = (
        "## TOAS:USER\n\n"
        "## RESULT\n\n"
        "[OK] shell: exit=0\n"
        '````markdown toas-output kind=file source="cat doc.txt" potency=inert path=doc.txt block_id=ib_testblock123456\n'
        "Line A\n"
        "Line B\n"
        "````\n\n"
        "## TOAS:STATE/1\n\nstate: {goal: read}\n"
    )
    obs = {
        "kind": "toas.compound-observation/1",
        "user_inputs": [
            {
                "content": (
                    "## RESULT\n\n"
                    "[OK] shell: exit=0\n"
                    '````markdown toas-output kind=file source="cat doc.txt" potency=inert path=doc.txt block_id=ib_testblock123456\n'
                    "(ref: ib_testblock123456)\n"
                    "````"
                )
            }
        ],
    }
    packet = build_state_step_packet(
        events_path=events,
        state={"goal": "read"},
        observation=obs,
        session_text=session_text,
    )
    projected_content = packet["observation"]["user_inputs"][0]["content"]
    assert "Line A" in projected_content
    assert "Line B" in projected_content
    assert "(ref: ib_testblock123456)" not in projected_content


def test_reconcile_state_lineage_and_materialize(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.touch()

    transcript_turns = [
        {"role": "user", "content": "hello"},
        {"role": "state", "content": "state: {goal: step1}"},
    ]

    # Empty history: everything up to state_index=1 is unmaterialized
    recon = reconcile_state_lineage(
        events=[],
        transcript_turns=transcript_turns,
        state_index=1,
    )
    assert recon.lcp == 0
    assert recon.best_head_id is None
    assert len(recon.unmaterialized_turns) == 2
    assert recon.parent_id is None

    # Materialize them
    materialized = materialize_state_turns(
        events_path=events_path,
        unmaterialized_turns=recon.unmaterialized_turns,
        parent_id=recon.parent_id,
    )
    assert len(materialized) == 2
    assert materialized[0]["role"] == "user"
    assert materialized[1]["role"] == "state"
    assert materialized[1]["parent"] == materialized[0]["id"]

    # Reconcile again with the newly written events: 100% LCP match
    from toas.graph import read_log
    new_events = read_log(str(events_path))
    recon2 = reconcile_state_lineage(
        events=new_events,
        transcript_turns=transcript_turns,
        state_index=1,
    )
    assert recon2.lcp == 2
    assert recon2.unmaterialized_turns == []
    assert recon2.parent_id == materialized[1]["id"]


def test_find_lineage_state_snapshot_respects_branch_lineage(tmp_path):
    events_path = tmp_path / "events.jsonl"
    from toas.graph import append_state_step_records

    # Branch A: state_snapshot st_a linked to message n1
    # Branch B: state_snapshot st_b linked to message n2 (appended later)
    records = [
        {"kind": "state_snapshot", "transition_id": "st_a", "state": {"goal": "branch_a"}, "message_id": "n1"},
        {"kind": "state_snapshot", "transition_id": "st_b", "state": {"goal": "branch_b"}, "message_id": "n2"},
    ]
    append_state_step_records(str(events_path), records)

    # Lineage specifying branch A must find branch A's snapshot, not branch B
    lineage_a = [{"id": "n1", "role": "state", "content": "state: {goal: branch_a}"}]
    snap = find_lineage_state_snapshot(
        events_path=events_path,
        lineage=lineage_a,
    )
    assert snap is not None
    assert snap["state"] == {"goal": "branch_a"}


def test_user_result_and_input_observations_separation():
    turns = [
        {"role": "user", "content": "Here is my request.\n\n## RESULT\n\noutput block 1"},
        {"role": "user", "content": "## RESULT\n\noutput block 2\n\n## RESULT\n\noutput block 3"},
        {"role": "user", "content": "Just a user message."},
    ]
    inputs = _user_input_observations(turns)
    results = _user_result_observations(turns)

    assert inputs == [
        {"content": "Here is my request."},
        {"content": "Just a user message."},
    ]
    assert results == [
        "output block 1",
        "output block 2",
        "output block 3",
    ]


def test_reconcile_tool_outcomes_truncation_and_deletion():
    prior_outcomes = [
        {
            "index": 0,
            "status": "completed",
            "result": [{"role": "result", "content": "original 5000 lines", "projection_lane": "user"}],
            "source": "model",
        },
        {
            "index": 1,
            "status": "completed",
            "result": [{"role": "result", "content": "second tool result", "projection_lane": "user"}],
            "source": "model",
        },
    ]

    # Truncate first result, keep second
    reconciled = _reconcile_tool_outcomes(prior_outcomes, ["[TRUNCATED]", "second tool result"])
    assert len(reconciled) == 2
    assert reconciled[0]["result"][0]["content"] == "[TRUNCATED]"
    assert reconciled[0]["status"] == "completed"
    assert reconciled[1]["result"][0]["content"] == "second tool result"

    # Delete second result (only 1 result in transcript)
    reconciled_deleted_second = _reconcile_tool_outcomes(prior_outcomes, ["[TRUNCATED]"])
    assert len(reconciled_deleted_second) == 1
    assert reconciled_deleted_second[0]["result"][0]["content"] == "[TRUNCATED]"

    # Delete all results
    assert _reconcile_tool_outcomes(prior_outcomes, []) == []


def test_build_state_step_packet_transcript_supremacy_over_history(tmp_path):
    events = tmp_path / "events.jsonl"
    events.touch()
    # Write completed transition and tool result in events.jsonl
    append_state_step_records(
        str(events),
        [
            {"kind": "state_transition", "transition_id": "st_test1", "status": "completed", "source": "model"},
            {
                "kind": "state_tool_result",
                "transition_id": "st_test1",
                "index": 0,
                "status": "completed",
                "result": [{"role": "result", "content": "untruncated original 1000 lines", "projection_lane": "user"}],
                "source": "model",
            },
        ],
    )

    # 1. Transcript has truncated result
    session_text_truncated = (
        "## TOAS:STATE/1\n\nstate: {goal: test}\n\n"
        "## TOAS:USER\n\n## RESULT\n\n[TRUNCATED BY OPERATOR]\n"
    )
    packet_truncated = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
        session_text=session_text_truncated,
    )
    outcomes = packet_truncated["observation"]["tool_outcomes"]
    assert len(outcomes) == 1
    assert outcomes[0]["result"][0]["content"] == "[TRUNCATED BY OPERATOR]"
    assert "1000 lines" not in outcomes[0]["result"][0]["content"]

    # 2. Transcript has deleted result (no RESULT blocks after STATE)
    session_text_deleted = (
        "## TOAS:STATE/1\n\nstate: {goal: test}\n\n"
        "## TOAS:USER\n\nI removed the tool output.\n"
    )
    packet_deleted = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
        session_text=session_text_deleted,
    )
    assert packet_deleted["observation"]["tool_outcomes"] == []

    # 3. Fallback when session_text is None (programmatic test mode)
    packet_fallback = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
        session_text=None,
    )
    fallback_outcomes = packet_fallback["observation"]["tool_outcomes"]
    assert len(fallback_outcomes) == 1
    assert fallback_outcomes[0]["result"][0]["content"] == "untruncated original 1000 lines"


def test_build_state_step_packet_inert_blocks_prefer_session_text(tmp_path):
    events = tmp_path / "events.jsonl"
    events.touch()
    # Write old inert block in events.jsonl
    append_state_step_records(
        str(events),
        [
            {
                "kind": "state_tool_result",
                "transition_id": "st_old",
                "index": 0,
                "status": "completed",
                "result": [
                    {
                        "role": "result",
                        "content": (
                            '````markdown toas-output kind=file block_id=ib_mod123\n'
                            'OLD 5000 LINES\n'
                            '````'
                        ),
                        "projection_lane": "user",
                    }
                ],
            }
        ],
    )

    # In session_text, the operator modified the inert block body
    session_text = (
        "## TOAS:STATE/1\n\nstate: {goal: test}\n\n"
        "## TOAS:USER\n\n"
        "## RESULT\n\n"
        '````markdown toas-output kind=file block_id=ib_mod123\n'
        'EDITED 2 LINES\n'
        '````\n'
    )
    packet = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
        session_text=session_text,
    )
    outcomes = packet["observation"]["tool_outcomes"]
    assert len(outcomes) == 1
    content = outcomes[0]["result"][0]["content"]
    assert "EDITED 2 LINES" in content
    assert "OLD 5000 LINES" not in content


def test_build_state_step_packet_strips_internal_payload_from_result_nodes(tmp_path):
    events = tmp_path / "events.jsonl"
    events.touch()
    # Write a tool result with a large internal payload into events.jsonl
    raw_payload = {"structure": [{"symbol": f"sym_{i}"} for i in range(500)], "ok": True}
    append_state_step_records(
        str(events),
        [
            {"kind": "state_transition", "transition_id": "st_p1", "status": "completed", "source": "model"},
            {
                "kind": "state_tool_result",
                "transition_id": "st_p1",
                "index": 0,
                "status": "completed",
                "result": [
                    {
                        "role": "result",
                        "content": "Rendered summary text.",
                        "projection_lane": "user",
                        "origin_role": "tool",
                        "origin_kind": "tool",
                        "payload": raw_payload,
                    }
                ],
                "source": "model",
            },
        ],
    )

    # 1. Direct packet build without transcript (fallback)
    packet_direct = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
    )
    node_direct = packet_direct["observation"]["tool_outcomes"][0]["result"][0]
    assert "payload" not in node_direct
    assert node_direct["content"] == "Rendered summary text."
    assert node_direct["role"] == "result"
    assert node_direct["projection_lane"] == "user"

    # 2. Packet build with operator-truncated transcript
    session_text = (
        "## TOAS:STATE/1\n\nstate: {goal: test}\n\n"
        "## TOAS:USER\n\n## RESULT\n\nTruncated operator text.\n"
    )
    packet_transcript = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
        session_text=session_text,
    )
    node_transcript = packet_transcript["observation"]["tool_outcomes"][0]["result"][0]
    assert "payload" not in node_transcript
    assert node_transcript["content"] == "Truncated operator text."

    # 3. Durable records in events.jsonl still retain the full payload
    records = read_log(str(events))
    tool_results = [r for r in records if r.get("kind") == "state_tool_result"]
    assert len(tool_results) == 1
    assert "payload" in tool_results[0]["result"][0]
    assert len(tool_results[0]["result"][0]["payload"]["structure"]) == 500

def test_spilled_tool_result_in_state_step_packet_projection(tmp_path):
    events = tmp_path / "events.jsonl"
    preview_body = "\n".join(f"symbol_{i}" for i in range(1, 31))
    spilled_content = (
        "[OK] get_structure: found 100 symbols\n"
        "Output exceeded threshold (10 KB, 100 lines); spilled to `.toas/scratch/ib_12345.txt`.\n\n"
        '```text toas-output kind=result block_id=ib_12345 path=".toas/scratch/ib_12345.txt" lines=1..30 of 100\n'
        f"{preview_body}\n"
        "```\n"
        '[70 lines remaining. Inspect with `read_file`, `grep`, or script via path=".toas/scratch/ib_12345.txt"]'
    )
    raw_payload = {"tool_name": "get_structure", "ok": True, "symbols": [f"symbol_{i}" for i in range(1, 101)]}

    append_state_step_records(
        str(events),
        [
            {"kind": "state_transition", "transition_id": "st_spill", "status": "completed", "source": "model"},
            {
                "kind": "state_tool_result",
                "transition_id": "st_spill",
                "index": 0,
                "status": "completed",
                "result": [
                    {
                        "role": "result",
                        "content": spilled_content,
                        "projection_lane": "user",
                        "origin_role": "tool",
                        "origin_kind": "tool",
                        "payload": raw_payload,
                    }
                ],
                "source": "model",
            },
        ],
    )

    # 1. Direct packet build without transcript preserves bounded preview without re-expansion
    packet_direct = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
    )
    node_direct = packet_direct["observation"]["tool_outcomes"][0]["result"][0]
    assert "payload" not in node_direct
    assert node_direct["content"] == spilled_content
    assert "lines=1..30 of 100" in node_direct["content"]
    assert "symbol_31" not in node_direct["content"]

    # 2. Transcript with spilled preview preserves bounded preview in packet
    session_text = (
        "## TOAS:STATE/1\n\nstate: {goal: test}\n\n"
        f"## TOAS:USER\n\n## RESULT\n\n{spilled_content}\n"
    )
    packet_transcript = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
        session_text=session_text,
    )
    node_transcript = packet_transcript["observation"]["tool_outcomes"][0]["result"][0]
    assert "payload" not in node_transcript
    assert node_transcript["content"] == spilled_content
    assert "symbol_31" not in node_transcript["content"]

    # 3. Operator edits to the preview are authoritative
    edited_session_text = (
        "## TOAS:STATE/1\n\nstate: {goal: test}\n\n"
        "## TOAS:USER\n\n## RESULT\n\n[OK] get_structure: manually narrowed to symbol_1\n"
    )
    packet_edited = build_state_step_packet(
        events_path=events,
        state={"goal": "test"},
        observation=None,
        session_text=edited_session_text,
    )
    node_edited = packet_edited["observation"]["tool_outcomes"][0]["result"][0]
    assert node_edited["content"] == "[OK] get_structure: manually narrowed to symbol_1"
