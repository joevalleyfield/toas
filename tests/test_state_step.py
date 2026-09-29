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
    initial_state,
    observation_with_user_turns,
    parse_state_turn,
    render_state_turn,
    seed_state_turn,
    state_records,
    step_state,
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


def test_parser_selects_latest_state_turn_and_preserves_surrounding_conversation():
    transcript = (
        "## TOAS:USER\n\nEarlier.\n\n"
        + render_state_turn({"goal": "old"})
        + "\n## TOAS:STATE/1\n\nstate: {goal: current}\n\n"
        + "## TOAS:USER\n\nLater conversation.\n"
    )
    parsed = parse_state_turn(transcript)
    assert parsed["state"] == {"goal": "current"}
    assert parsed["_transcript_prefix"].startswith("## TOAS:USER")
    assert parsed["_transcript_suffix"].strip().startswith("## TOAS:USER")


def test_state_turn_collects_trailing_user_and_control_turns():
    transcript = (
        "## TOAS:STATE/1\n\nstate: {goal: inspect}\n\n"
        "## TOAS:USER\n\nRead the manifest.\n\n"
        "## TOAS:CONTROL\n\n/queue approve q1\n"
    )

    parsed = parse_state_turn(transcript)
    observation = observation_with_user_turns(parsed.get("observation"), parsed["_input_turns"])

    assert parsed["_input_turns"] == [
        {"role": "user", "content": "Read the manifest."},
        {"role": "control", "content": "/queue approve q1"},
    ]
    assert observation["user_inputs"] == [{"content": "Read the manifest."}]
    assert "/queue approve q1" not in str(observation)


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
    [transition] = read_log(str(events))
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
    answer = content if content is None else {"content": content}
    with pytest.raises(ValueError, match=message):
        step_state(
            events_path=events,
            state={},
            observation=None,
            generate=lambda _p: answer,
            execute_call=lambda _c: None,
        )
    [transition] = read_log(str(events))
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
