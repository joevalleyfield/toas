from types import SimpleNamespace

import pytest

from toas import cli_session_commands
from toas.graph import append_state_step_records, read_log
from toas.runtime.result_nodes import make_result_node
from toas.runtime.state_step import parse_state_turn, render_state_turn


def test_regular_step_routes_typed_state_turn_through_state_runtime(monkeypatch, tmp_path):
    session = tmp_path / "session.md"
    session.write_text("## TOAS:USER\n\nEarlier conversation.")
    events_path = tmp_path / "events.jsonl"
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        resolve_session_path=lambda _events: session,
        read_text_preserve_newlines=lambda path: path.read_text() if path.exists() else "",
        detect_newline_style=lambda _text: "\n",
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
    monkeypatch.setattr(cli_session_commands, "read_log", lambda _path: [])
    cli_session_commands.run_state_seed(format="markdown")
    seeded = parse_state_turn(session.read_text())
    state = dict(seeded["state"])
    state["goal"] = "inspect"
    session.write_text(
        seeded["_transcript_prefix"]
        + render_state_turn(state, observation={"content": "begin"}, format="markdown")
    )
    append_state_step_records(
        str(events_path),
        [
            {"kind": "state_snapshot", "transition_id": "st0", "state": state},
            {
                "kind": "state_observation",
                "transition_id": "st0",
                "observation": {
                    "kind": "toas.compound-observation/1",
                    "operator_observation": {"content": "begin"},
                    "tool_outcomes": [],
                },
            },
        ],
    )
    (tmp_path / "later.txt").write_text("later", encoding="utf-8")
    monkeypatch.setattr(
        cli_session_commands,
        "_prepare_session_transcript",
        lambda **_kwargs: (session, session.read_text(), session.read_text(), "\n"),
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_build_runtime_context",
        lambda **_kwargs: {
            "command_cwd": str(tmp_path),
            "workspace_mode": "strict",
            "workspace_roots": [str(tmp_path)],
        },
    )
    packets = []
    def generate(packet):
        packets.append(packet)
        if len(packets) == 1:
            return {"content": '{"state_patch":{"progress":["started"]},"tool_calls":[{"tool_name":"read_file","args":{"path":"later.txt"}}]}'}
        return {"content": '{"state_patch":{},"tool_calls":[]}'}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(cli_session_commands, "_resolve_runtime_generation_context", lambda **_kwargs: (
        config, {}, SimpleNamespace(generate_state_packet=generate), {}
    ))

    from toas import step as step_mod

    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _working: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda *_args: ())
    cli_session_commands.run_step(session_path=str(session))
    assert "progress:\n  - started" in session.read_text()
    assert "Earlier conversation." in session.read_text()
    cli_session_commands.run_step(session_path=str(session))
    cli_session_commands.run_step(session_path=str(session))
    records = read_log(str(events_path))
    assert [record["kind"] for record in records[2:]] == [
        "state_transition", "state_diff", "state_snapshot", "state_observation", "state_tool_request",
        "state_transition", "state_tool_result", "state_transition",
        "state_transition", "state_diff", "state_snapshot", "state_observation",
    ]
    assert not any("role" in record for record in records)
    assert packets[-1]["observation"]["tool_outcomes"][0]["status"] == "completed"


def test_user_turn_after_state_is_inferred_directly_when_frontier_is_non_executable(monkeypatch, tmp_path):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()
    session.write_text(
        "## TOAS:STATE/1\n\nstate: {goal: inspect, progress: []}\n\n"
        "## TOAS:USER\n\nRead the project manifest.\n"
    )
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
    monkeypatch.setattr(cli_session_commands, "read_log", lambda _path: [])
    monkeypatch.setattr(
        cli_session_commands,
        "_prepare_session_transcript",
        lambda **_kwargs: (session, session.read_text(), session.read_text(), "\n"),
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_build_runtime_context",
        lambda **_kwargs: {
            "command_cwd": str(tmp_path),
            "workspace_mode": "strict",
            "workspace_roots": [str(tmp_path)],
        },
    )
    packets = []

    def generate(packet):
        packets.append(packet)
        return {"content": '{"state_patch":{"goal":"updated by model"},"tool_calls":[]}'}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate_state_packet=generate), {}),
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_state_input_turns",
        lambda **kwargs: (
            kwargs["normalized_transcript"],
            kwargs["parsed_turn"],
            [],
            False,
        ),
    )

    cli_session_commands.run_step(session_path=str(session))

    accepted = parse_state_turn(session.read_text())
    assert accepted["state"] == {"goal": "updated by model", "progress": []}
    assert accepted["observation"]["user_inputs"] == [
        {"content": "Read the project manifest."}
    ]
    assert "## TOAS:USER\n\nRead the project manifest." in session.read_text()

    assert packets[0]["observation"]["user_inputs"] == [
        {"content": "Read the project manifest."}
    ]


def test_appended_user_and_control_intents_use_normal_frontier_and_embed_results(monkeypatch, tmp_path):
    from toas.runtime import step_runtime
    from toas.transcript import parse_transcript

    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()
    transcript = (
        "## TOAS:STATE/1\n\nstate: {goal: inspect}\n\n"
        "## TOAS:USER\n\n/help\n\n"
        "## TOAS:CONTROL\n\n/pwd\n"
    )
    session.write_text(transcript)
    parsed = parse_state_turn(transcript)
    calls = []

    def resolve_frontier(transcript, _log, **_kwargs):
        frontier = parse_transcript(transcript)[-1]
        calls.append((transcript, frontier["role"]))
        return [make_result_node(
            f"result from {frontier['role']}",
            origin_role=frontier["role"],
            origin_kind="slash_command",
        )], []

    deps = SimpleNamespace(
        step_fn=resolve_frontier,
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_build_runtime_context",
        lambda **_kwargs: {
            "head_id": None,
            "lineage": [],
            "log": [],
            "command_cwd": str(tmp_path),
            "workspace_mode": "strict",
            "workspace_roots": [str(tmp_path)],
            "bind_index": 0,
        },
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (object(), {}, SimpleNamespace(generate=lambda _messages: None), {}),
    )
    monkeypatch.setattr(step_runtime, "_frontier_has_callable_intent", lambda **_kwargs: True)
    monkeypatch.setattr(cli_session_commands, "_persist_step_outputs", lambda **_kwargs: None)
    monkeypatch.setattr(
        cli_session_commands,
        "_write_text_with_newline_style",
        lambda *, path, text, **_kwargs: path.write_text(text),
    )

    updated, resolved_turn, _events, intent_resolved = cli_session_commands._resolve_state_input_turns(
        deps=deps,
        events_path=events_path,
        session_path=session,
        session_newline="\n",
        normalized_transcript=transcript,
        parsed_turn=parsed,
    )

    assert intent_resolved is True
    assert [role for _text, role in calls] == ["user", "control"]
    assert "## TOAS:STATE/1" not in calls[0][0]
    turns = resolved_turn["_input_turns"]
    assert len(turns) == 4
    assert turns[0]["role"] == "user" and turns[0]["content"] == "/help"
    assert turns[1]["role"] == "user" and "result from user" in turns[1]["content"]
    assert turns[2]["role"] == "control" and turns[2]["content"] == "/pwd"
    assert turns[3]["role"] == "control" and "result from control" in turns[3]["content"]
    assert "## TOAS:USER\n\n/help\n\n## TOAS:USER\n\n## RESULT" in session.read_text()
    assert "## TOAS:CONTROL\n\n/pwd\n\n## TOAS:CONTROL\n\n## RESULT" in session.read_text()
    assert updated == session.read_text()


def test_resolved_user_intent_does_not_reexecute_on_subsequent_step(monkeypatch, tmp_path):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()
    transcript = (
        "## TOAS:STATE/1\n\nstate: {goal: inspect}\n\n"
        "## TOAS:USER\n\n$ cat AGENTS.md\n\n"
        "## TOAS:USER\n\n## RESULT\n\n[OK] shell: exit=0\nstdout:\nnotes\n"
    )
    session.write_text(transcript)
    parsed = parse_state_turn(transcript)

    def unexpected_step(*_args, **_kwargs):
        raise AssertionError("already resolved user command must not re-execute")

    deps = SimpleNamespace(
        step_fn=unexpected_step,
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_build_runtime_context",
        lambda **_kwargs: {
            "head_id": None,
            "lineage": [],
            "log": [],
            "command_cwd": str(tmp_path),
            "workspace_mode": "strict",
            "workspace_roots": [str(tmp_path)],
        },
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (object(), {}, SimpleNamespace(generate=lambda _messages: None), {}),
    )

    updated, resolved_turn, _events, intent_resolved = cli_session_commands._resolve_state_input_turns(
        deps=deps,
        events_path=events_path,
        session_path=session,
        session_newline="\n",
        normalized_transcript=transcript,
        parsed_turn=parsed,
    )

    assert intent_resolved is False
    assert updated == transcript
    assert len(resolved_turn["_input_turns"]) == 2


def test_plain_user_observation_does_not_enter_conversation_step_runtime(monkeypatch, tmp_path):
    from toas.runtime import step_runtime

    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()
    transcript = (
        "## TOAS:STATE/1\n\nstate: {goal: inspect}\n\n"
        "## TOAS:USER\n\nRead the project manifest.\n"
    )
    session.write_text(transcript)
    parsed = parse_state_turn(transcript)
    config = object()
    monkeypatch.setattr(
        cli_session_commands,
        "_build_runtime_context",
        lambda **_kwargs: {"head_id": None, "lineage": [], "log": []},
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate=lambda _messages: None), {}),
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_build_step_kwargs",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(step_runtime, "_frontier_has_callable_intent", lambda **_kwargs: False)

    def unexpected_conversation_step(*_args, **_kwargs):
        raise AssertionError("plain state observation must not enter conversation inference")

    deps = SimpleNamespace(step_fn=unexpected_conversation_step)
    _updated, _parsed, _events, intent_resolved = cli_session_commands._resolve_state_input_turns(
        deps=deps,
        events_path=events_path,
        session_path=session,
        session_newline="\n",
        normalized_transcript=transcript,
        parsed_turn=parsed,
    )

    assert intent_resolved is False


@pytest.mark.parametrize(
    "payload, expected_status",
    [
        ({"ok": True}, "completed"),
        (None, "completed"),
        ({"ok": False, "summary": "denied"}, "failed"),
        ({"ok": False, "outcome": "cancelled"}, "cancelled"),
        ({"ok": False, "outcome": "indeterminate"}, "indeterminate"),
    ],
)
def test_state_diff_step_executes_pending_plan_through_existing_capability_adapter(
    monkeypatch, tmp_path, payload, expected_status
):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    append_state_step_records(
        str(events_path),
        [
            {
                "kind": "state_snapshot",
                "transition_id": "st0",
                "state": {"goal": "inspect", "progress": []},
            },
            {
                "kind": "state_transition",
                "transition_id": "st1",
                "status": "pending",
                "tool_calls": [{"tool_name": "echo", "args": {"text": "go"}}],
            },
        ],
    )
    deps = SimpleNamespace(apply_newline_style=lambda text, _newline: text)
    monkeypatch.setattr(
        cli_session_commands,
        "_build_runtime_context",
        lambda **_kwargs: {
            "command_cwd": str(tmp_path),
            "workspace_mode": "strict",
            "workspace_roots": [str(tmp_path)],
        },
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: pytest.fail("pending batch execution must not resolve model credentials"),
    )
    from toas import step as step_mod

    calls = []
    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _working: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda *_args: ("echo",))
    monkeypatch.setattr(
        step_mod,
        "_execute_plan",
        lambda plan, **kwargs: calls.append((plan, kwargs)) or [{"payload": payload}],
    )
    cli_session_commands._run_state_step(
        deps=deps,
        events_path=events_path,
        session_path=session,
        normalized_transcript="state diff",
        session_newline="\n",
        events=[],
        parsed_turn={
            "turn_type": "state_diff",
            "state_patch": {"progress": ["read"]},
            "observation": "run",
            "format": "yaml",
        },
    )
    assert calls[0][0] == [{"tool_name": "echo", "args": {"text": "go"}}]
    assert calls[0][1]["shell_allowed_commands"] == ("echo",)
    assert read_log(str(events_path))[-1]["status"] == expected_status


def test_state_diff_requires_a_prior_accepted_snapshot(tmp_path):
    events_path = tmp_path / "events.jsonl"
    with pytest.raises(ValueError, match="no earlier accepted state snapshot"):
        cli_session_commands._run_state_step(
            deps=SimpleNamespace(),
            events_path=events_path,
            session_path=tmp_path / "session.md",
            normalized_transcript="state diff",
            session_newline="\n",
            events=[],
            parsed_turn={"turn_type": "state_diff", "state_patch": {}, "observation": None},
        )


def test_state_seed_creates_blank_goal_and_refuses_overwriting_operator_content(monkeypatch, tmp_path):
    session = tmp_path / "session.md"
    events = tmp_path / "events.jsonl"
    deps = SimpleNamespace(
        resolve_events_path=lambda: events,
        ensure_file=lambda path: path.touch(exist_ok=True),
        resolve_session_path=lambda _records: session,
        read_text_preserve_newlines=lambda path: path.read_text() if path.exists() else "",
        detect_newline_style=lambda _text: "\n",
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
    session.write_text("## TOAS:USER\n\nExisting work")
    cli_session_commands.run_state_seed(format="markdown")
    assert session.read_text().startswith("## TOAS:USER\n\nExisting work\n\n")
    assert parse_state_turn(session.read_text())["state"]["goal"] == ""
    with pytest.raises(ValueError, match="already contains a typed state turn"):
        cli_session_commands.run_state_seed(format="yaml")


def test_cli_seed_wrapper_forwards_format(monkeypatch):
    from toas import cli

    seen = []
    monkeypatch.setattr(cli, "_run_state_seed_impl", lambda **kwargs: seen.append(kwargs))
    cli.run_state_seed(format="markdown")
    assert seen == [{"format": "markdown"}]
