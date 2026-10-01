import json
from types import SimpleNamespace

import pytest

from toas import cli_session_commands
from toas.graph import append_state_step_records, read_log
from toas.runtime.result_nodes import make_result_node
from toas.runtime.state_step import parse_state_turn, partition_state_transcript, render_state_turn
from toas.transcript import render_transcript


def test_regular_step_routes_typed_state_turn_through_state_runtime(monkeypatch, tmp_path, capsys):
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
    seed_out = capsys.readouterr().out
    session.write_text(session.read_text() + "\n\n" + seed_out)
    seeded = parse_state_turn(session.read_text())
    state = dict(seeded["state"])
    state["goal"] = "inspect"
    prefix_turns, _state_turn, _suffix = partition_state_transcript(session.read_text())
    prefix = (render_transcript(prefix_turns, spaced=True) + "\n\n") if prefix_turns else ""
    session.write_text(
        prefix + render_state_turn(state, observation={"content": "begin"}, format="markdown")
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

    # Step 1: infer
    initial_text = session.read_text()
    cli_session_commands.run_step(session_path=str(session))
    assert session.read_text() == initial_text  # disk is not mutated by run_step
    out1 = capsys.readouterr().out
    assert "progress:\n  - started" in out1
    session.write_text(session.read_text() + out1)  # simulate >> session.md
    assert "Earlier conversation." in session.read_text()

    # Step 2: batch execution
    before_step2 = session.read_text()
    cli_session_commands.run_step(session_path=str(session))
    assert session.read_text() == before_step2
    out2 = capsys.readouterr().out
    session.write_text(session.read_text() + out2)

    # Step 3: next infer
    before_step3 = session.read_text()
    cli_session_commands.run_step(session_path=str(session))
    assert session.read_text() == before_step3
    out3 = capsys.readouterr().out
    session.write_text(session.read_text() + out3)
    records = read_log(str(events_path))
    state_kinds = [record["kind"] for record in records if "kind" in record]
    assert state_kinds[2:] == [
        "state_transition", "state_diff", "state_snapshot", "state_observation", "state_tool_request",
        "state_transition", "state_tool_result", "state_transition",
        "state_transition", "state_diff", "state_snapshot", "state_observation",
    ]
    message_roles = [record["role"] for record in records if "role" in record]
    assert "state" in message_roles
    assert packets[-1]["observation"]["tool_outcomes"][0]["status"] == "completed"


def test_state_step_cli_truncated_tool_result_in_transcript_takes_precedence(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()
    session.write_text(
        "## TOAS:STATE/1\n\nstate: {goal: inspect, progress: []}\n"
    )
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
    (tmp_path / "huge.txt").write_text("line 1\nline 2\nline 3\nline 4\nline 5", encoding="utf-8")
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
            return {"content": '{"state_patch":{"progress":["reading"]},"tool_calls":[{"tool_name":"read_file","args":{"path":"huge.txt"}}]}'}
        return {"content": '{"state_patch":{},"tool_calls":[]}'}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(cli_session_commands, "_resolve_runtime_generation_context", lambda **_kwargs: (
        config, {}, SimpleNamespace(generate_state_packet=generate), {}
    ))

    # Step 1: infer
    cli_session_commands.run_step(session_path=str(session))
    out1 = capsys.readouterr().out
    session.write_text(session.read_text() + out1)

    # Step 2: batch execution
    cli_session_commands.run_step(session_path=str(session))
    out2 = capsys.readouterr().out
    assert "line 1" in out2
    session.write_text(session.read_text() + out2)

    # Operator truncates the result in session.md
    transcript_before_truncation = session.read_text()
    assert "line 5" in transcript_before_truncation
    truncated_transcript = transcript_before_truncation.replace("line 5", "[TRUNCATED AFTER LINE 4]")
    session.write_text(truncated_transcript)

    # Step 3: next infer
    cli_session_commands.run_step(session_path=str(session))
    _out3 = capsys.readouterr().out

    # Verify inference packet received operator's truncated result
    step3_packet = packets[-1]
    outcome = step3_packet["observation"]["tool_outcomes"][0]
    assert outcome["status"] == "completed"
    outcome_content = outcome["result"][0]["content"]
    assert "[TRUNCATED AFTER LINE 4]" in outcome_content
    assert "line 5" not in outcome_content

    # Verify durable history in events.jsonl still retains untruncated result
    records = read_log(str(events_path))
    tool_results = [r for r in records if r.get("kind") == "state_tool_result"]
    assert len(tool_results) == 1
    assert "line 5" in tool_results[0]["result"][0]["content"]


def test_state_step_cli_deleted_tool_result_in_transcript_is_not_resurrected(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()
    session.write_text(
        "## TOAS:STATE/1\n\nstate: {goal: inspect, progress: []}\n"
    )
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
    (tmp_path / "data.txt").write_text("some data", encoding="utf-8")
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
            return {"content": '{"state_patch":{"progress":["reading"]},"tool_calls":[{"tool_name":"read_file","args":{"path":"data.txt"}}]}'}
        return {"content": '{"state_patch":{},"tool_calls":[]}'}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(cli_session_commands, "_resolve_runtime_generation_context", lambda **_kwargs: (
        config, {}, SimpleNamespace(generate_state_packet=generate), {}
    ))

    # Step 1: infer
    cli_session_commands.run_step(session_path=str(session))
    out1 = capsys.readouterr().out
    session.write_text(session.read_text() + out1)

    # Step 2: batch execution
    cli_session_commands.run_step(session_path=str(session))
    out2 = capsys.readouterr().out
    assert "some data" in out2
    session.write_text(session.read_text() + out2)

    # Operator deletes the batch execution result from session.md completely
    session.write_text(session.read_text().split("## TOAS:USER")[0])

    # Step 3: next infer
    cli_session_commands.run_step(session_path=str(session))
    _out3 = capsys.readouterr().out

    # Verify inference packet has empty tool_outcomes (no resurrection from events.jsonl)
    step3_packet = packets[-1]
    assert step3_packet["observation"]["tool_outcomes"] == []


def test_user_turn_after_state_is_inferred_directly_when_frontier_is_non_executable(monkeypatch, tmp_path, capsys):
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
            kwargs.get("input_turns", []),
            [],
            False,
        ),
    )

    initial_text = session.read_text()
    cli_session_commands.run_step(session_path=str(session))
    assert session.read_text() == initial_text  # disk unmodified

    out = capsys.readouterr().out
    combined = initial_text + out
    accepted = parse_state_turn(combined)
    assert accepted["state"] == {"goal": "updated by model", "progress": []}
    assert accepted.get("observation") is None
    assert "## TOAS:USER\n\nRead the project manifest." in combined

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
    _ = parse_state_turn(transcript)
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

    updated, resolved_input_turns, _events, intent_resolved = cli_session_commands._resolve_state_input_turns(
        deps=deps,
        events_path=events_path,
        session_path=session,
        session_newline="\n",
        normalized_transcript=transcript,
    )

    assert intent_resolved is True
    assert [role for _text, role in calls] == ["user", "control"]
    assert "## TOAS:STATE/1" not in calls[0][0]
    turns = resolved_input_turns
    assert len(turns) == 4
    assert turns[0]["role"] == "user" and turns[0]["content"] == "/help"
    assert turns[1]["role"] == "user" and "result from user" in turns[1]["content"]
    assert turns[2]["role"] == "control" and turns[2]["content"] == "/pwd"
    assert turns[3]["role"] == "control" and "result from control" in turns[3]["content"]
    assert session.read_text() == transcript  # session file on disk is not mutated
    assert "## TOAS:USER\n\n/help\n\n## TOAS:USER\n\n## RESULT" in updated
    assert "## TOAS:CONTROL\n\n/pwd\n\n## TOAS:CONTROL\n\n## RESULT" in updated


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
    _ = parse_state_turn(transcript)

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

    updated, resolved_input_turns, _events, intent_resolved = cli_session_commands._resolve_state_input_turns(
        deps=deps,
        events_path=events_path,
        session_path=session,
        session_newline="\n",
        normalized_transcript=transcript,
    )

    assert intent_resolved is False
    assert updated == transcript
    assert len(resolved_input_turns) == 2


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
    _updated, _resolved_inputs, _events, intent_resolved = cli_session_commands._resolve_state_input_turns(
        deps=deps,
        events_path=events_path,
        session_path=session,
        session_newline="\n",
        normalized_transcript=transcript,
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
        normalized_transcript="## TOAS:STATE-DIFF/1\n\n```yaml\nstate_patch:\n  progress:\n    - read\nobservation: run\n```\n",
        session_newline="\n",
        events=[],
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
            normalized_transcript="## TOAS:STATE-DIFF/1\n\n```yaml\nstate_patch: {}\n```\n",
            session_newline="\n",
            events=[],
        )


def test_state_seed_emits_to_stdout_with_blank_goal_and_instructions(capsys):
    cli_session_commands.run_state_seed(format="markdown")
    out_md = capsys.readouterr().out
    assert out_md.startswith("## TOAS:STATE/1\n\n```yaml\n")
    parsed_md = parse_state_turn(out_md)
    assert parsed_md["state"]["goal"] == ""
    assert "instructions" in parsed_md

    cli_session_commands.run_state_seed(format="yaml")
    out_yaml = capsys.readouterr().out
    assert out_yaml.startswith("## TOAS:STATE/1\n\ninstructions:")
    parsed_yaml = parse_state_turn(out_yaml)
    assert parsed_yaml["state"]["goal"] == ""
    assert "instructions" in parsed_yaml


def test_cli_seed_wrapper_forwards_format(monkeypatch):
    from toas import cli

    seen = []
    monkeypatch.setattr(cli, "_run_state_seed_impl", lambda **kwargs: seen.append(kwargs))
    cli.run_state_seed(format="markdown")
    assert seen == [{"format": "markdown"}]


def test_state_step_progresses_ordinal_and_preserves_unfolding_history(monkeypatch, tmp_path):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()

    initial_transcript = (
        "## TOAS:STATE/1\n\n"
        "state:\n"
        "  goal: check tasks\n"
        "  progress: []\n"
    )
    session.write_text(initial_transcript)
    append_state_step_records(
        str(events_path),
        [
            {"kind": "state_snapshot", "transition_id": "st0", "state": {"goal": "check tasks", "progress": []}},
        ],
    )
    (tmp_path / "task.txt").write_text("task content", encoding="utf-8")

    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
    monkeypatch.setattr(cli_session_commands, "read_log", lambda _path: read_log(str(events_path)))
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

    call_count = 0

    def generate(packet):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "content": json.dumps({
                    "state_patch": {"progress": ["found task"]},
                    "tool_calls": [{"tool_name": "read_file", "args": {"path": "task.txt"}}],
                })
            }
        return {
            "content": json.dumps({
                "state_patch": {"progress": ["found task", "read task"]},
                "tool_calls": [],
            })
        }

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate_state_packet=generate), {}),
    )

    from toas import step as step_mod

    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _working: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda *_args: ())

    deltas = []

    # Step 1: Infer -> streams STATE/2; disk is not mutated
    cli_session_commands.run_step(session_path=str(session), on_projection_delta=deltas.append)
    assert session.read_text() == initial_transcript  # disk is not mutated
    assert any("## TOAS:STATE/2" in d for d in deltas)
    session.write_text(session.read_text() + deltas[-1])  # editor sink applies delta to buffer
    session_after_step1 = session.read_text()
    assert "## TOAS:STATE/1" in session_after_step1
    assert "## TOAS:STATE/2" in session_after_step1
    assert "pending_tools:" in session_after_step1
    assert "read_file" in session_after_step1
    assert "observation:" not in session_after_step1

    # Step 2: Execute batch -> streams result block without rewriting STATE/2; disk is not mutated
    before_step2 = session.read_text()
    cli_session_commands.run_step(session_path=str(session), on_projection_delta=deltas.append)
    assert session.read_text() == before_step2  # disk is not mutated
    assert any("## RESULT" in d for d in deltas)
    session.write_text(session.read_text() + deltas[-1])  # editor sink applies delta to buffer
    session_after_step2 = session.read_text()
    assert "## TOAS:STATE/1" in session_after_step2
    assert "## TOAS:STATE/2" in session_after_step2
    assert "## TOAS:USER\n\n## RESULT" in session_after_step2
    assert "task content" in session_after_step2

    # Step 3: Infer next -> streams STATE/3 while keeping RESULT block intact; disk is not mutated
    before_step3 = session.read_text()
    cli_session_commands.run_step(session_path=str(session), on_projection_delta=deltas.append)
    assert session.read_text() == before_step3  # disk is not mutated
    assert any("## TOAS:STATE/3" in d for d in deltas)
    session.write_text(session.read_text() + deltas[-1])  # editor sink applies delta to buffer
    session_after_step3 = session.read_text()
    assert "## TOAS:STATE/1" in session_after_step3
    assert "## TOAS:STATE/2" in session_after_step3
    assert "## TOAS:USER\n\n## RESULT" in session_after_step3
    assert "task content" in session_after_step3
    assert "## TOAS:STATE/3" in session_after_step3
    parsed3 = parse_state_turn(session_after_step3)
    assert parsed3["state_number"] == 3
    assert parsed3["state"]["progress"] == ["found task", "read task"]


def test_state_step_materializes_state_turns_and_participates_in_heads_and_project_transcript(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    session.write_text(
        "## TOAS:USER\n\nHello there\n\n"
        "## TOAS:STATE/1\n\nstate:\n  goal: research\n  progress: []\n"
    )
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        resolve_session_path=lambda _events: session,
        read_text_preserve_newlines=lambda path: path.read_text() if path.exists() else "",
        detect_newline_style=lambda _text: "\n",
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
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

    def generate(packet):
        return {
            "content": json.dumps({
                "state_patch": {"progress": ["reading"]},
                "tool_calls": [],
            })
        }

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate_state_packet=generate), {}),
    )

    cli_session_commands.run_step(session_path=str(session))
    out = capsys.readouterr().out
    session.write_text(session.read_text() + "\n\n" + out)

    records = read_log(str(events_path))
    message_events = [r for r in records if "role" in r]
    assert len(message_events) == 3
    assert message_events[0]["id"] == "n1"
    assert message_events[0]["role"] == "user"
    assert message_events[0]["parent"] is None
    assert message_events[0]["content"] == "Hello there"

    assert message_events[1]["id"] == "n2"
    assert message_events[1]["role"] == "state"
    assert message_events[1]["parent"] == "n1"

    assert message_events[2]["id"] == "n3"
    assert message_events[2]["role"] == "state"
    assert message_events[2]["parent"] == "n2"

    from toas.graph import list_heads, project_transcript
    heads = list_heads(records)
    assert len(heads) == 1
    assert heads[0]["id"] == "n3"

    projected = project_transcript(records, head_id="n3")
    assert "## TOAS:USER\n\nHello there" in projected
    assert "## TOAS:STATE/1" in projected
    assert "## TOAS:STATE/2" in projected

    from toas.graph_message_edges import project_llm_input_from_messages
    llm_input = project_llm_input_from_messages(message_events)
    # State turns are excluded from conversational LLM inputs
    assert [m["role"] for m in llm_input] == ["user"]
    assert llm_input[0]["content"] == "Hello there"


def test_state_diff_resolves_base_snapshot_from_branch_lineage(monkeypatch, tmp_path):
    from toas.graph import append_state_step_records, write_message_events
    events_path = tmp_path / "events.jsonl"
    events_path.touch()

    # Pre-populate DAG in events.jsonl:
    # Root n1 (user)
    # Branch A: n2 (state, goal: A, count: 1)
    # Branch B: n3 (state, goal: B, count: 10) diverging from n1
    write_message_events(str(events_path), [
        {"id": "n1", "parent": None, "role": "user", "content": "start"},
        {"id": "n2", "parent": "n1", "role": "state", "content": "state: {goal: A, count: 1}", "metadata": {"marker": "TOAS:STATE/1"}},
        {"id": "n3", "parent": "n1", "role": "state", "content": "state: {goal: B, count: 10}", "metadata": {"marker": "TOAS:STATE/1"}},
    ])
    append_state_step_records(str(events_path), [
        {"kind": "state_snapshot", "transition_id": "st_a", "state": {"goal": "A", "count": 1}, "message_id": "n2"},
        {"kind": "state_snapshot", "transition_id": "st_b", "state": {"goal": "B", "count": 10}, "message_id": "n3"},
    ])

    session = tmp_path / "session.md"
    session.write_text(
        "## TOAS:USER\n\nstart\n\n"
        "## TOAS:STATE/1\n\nstate: {goal: A, count: 1}\n\n"
        "## TOAS:STATE-DIFF/2\n\nstate_patch:\n  count: 2\n"
    )
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        resolve_session_path=lambda _events: session,
        read_text_preserve_newlines=lambda path: path.read_text() if path.exists() else "",
        detect_newline_style=lambda _text: "\n",
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
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

    captured_packet = {}
    def generate(packet):
        captured_packet.update(packet)
        return {"content": json.dumps({"state_patch": {}, "tool_calls": []})}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate_state_packet=generate), {}),
    )

    cli_session_commands.run_step(session_path=str(session))

    # Base snapshot was resolved from Branch A (n2: {"goal": "A", "count": 1}), NOT Branch B (n3: {"goal": "B", "count": 10})
    assert captured_packet["state"] == {"goal": "A", "count": 2}


def test_state_branching_from_prior_state_creates_dag_branch_without_mutation(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    session.write_text(
        "## TOAS:USER\n\nstart\n\n"
        "## TOAS:STATE/1\n\nstate:\n  goal: original\n  progress: []\n"
    )
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        resolve_session_path=lambda _events: session,
        read_text_preserve_newlines=lambda path: path.read_text() if path.exists() else "",
        detect_newline_style=lambda _text: "\n",
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
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

    call_index = 0
    def generate(packet):
        nonlocal call_index
        call_index += 1
        goal = packet["state"]["goal"]
        return {"content": json.dumps({"state_patch": {"progress": [f"step_{goal}"]}, "tool_calls": []})}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate_state_packet=generate), {}),
    )

    # Step 1 on Branch A
    cli_session_commands.run_step(session_path=str(session))
    out1 = capsys.readouterr().out
    session.write_text(session.read_text() + "\n\n" + out1)

    from toas.graph import list_heads, project_transcript
    heads1 = list_heads(read_log(str(events_path)))
    assert len(heads1) == 1
    branch_a_head = heads1[0]["id"]

    # Now simulate user editing session.md back to STATE/1 with an alternative goal:
    session.write_text(
        "## TOAS:USER\n\nstart\n\n"
        "## TOAS:STATE/1\n\nstate:\n  goal: alternative\n  progress: []\n"
    )

    # Step 2 on Branch B
    cli_session_commands.run_step(session_path=str(session))
    out2 = capsys.readouterr().out
    session.write_text(session.read_text() + "\n\n" + out2)

    records = read_log(str(events_path))
    heads2 = list_heads(records)
    assert len(heads2) == 2
    head_ids = {h["id"] for h in heads2}
    assert branch_a_head in head_ids
    branch_b_head = (head_ids - {branch_a_head}).pop()

    # Project Branch A: intact and unchanged
    proj_a = project_transcript(records, head_id=branch_a_head)
    assert "goal: original" in proj_a
    assert "step_original" in proj_a

    # Project Branch B: has alternative branch content
    proj_b = project_transcript(records, head_id=branch_b_head)
    assert "goal: alternative" in proj_b
    assert "step_alternative" in proj_b


def test_state_step_cli_renders_failed_tool_with_name_and_detail(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    session.write_text(
        "## TOAS:STATE/1\n\n"
        "state:\n  goal: inspect\n  progress: []\n"
    )
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
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
    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (
            config,
            {},
            SimpleNamespace(
                generate_state_packet=lambda _p: {
                    "content": json.dumps({
                        "state_patch": {"progress": ["inspecting"]},
                        "tool_calls": [{"tool_name": "get_structure", "args": {"path": str(tmp_path)}}],
                    })
                }
            ),
            {},
        ),
    )

    bad_py = tmp_path / "broken.py"
    bad_py.write_text("def syntax_err(\n", encoding="utf-8")

    # Step 1: infer
    cli_session_commands.run_step(session_path=str(session))
    out1 = capsys.readouterr().out
    session.write_text(session.read_text() + out1)

    # Step 2: batch execution
    cli_session_commands.run_step(session_path=str(session))
    out2 = capsys.readouterr().out
    assert "[FAILED] tool 0 (get_structure):" in out2
    assert "broken.py" in out2


def test_state_step_cli_renders_partial_success_with_failure_lines(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    session.write_text(
        "## TOAS:STATE/1\n\n"
        "state:\n  goal: inspect\n  progress: []\n"
    )
    deps = SimpleNamespace(
        resolve_events_path=lambda: events_path,
        ensure_file=lambda path: path.touch(exist_ok=True),
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
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
    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    good_file = tmp_path / "good.txt"
    good_file.write_text("good content", encoding="utf-8")
    bad_py = tmp_path / "broken.py"
    bad_py.write_text("def syntax_err(\n", encoding="utf-8")

    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (
            config,
            {},
            SimpleNamespace(
                generate_state_packet=lambda _p: {
                    "content": json.dumps({
                        "state_patch": {"progress": ["inspecting"]},
                        "tool_calls": [
                            {"tool_name": "read_file", "args": {"path": "good.txt"}},
                            {"tool_name": "get_structure", "args": {"path": str(tmp_path)}},
                        ],
                    })
                }
            ),
            {},
        ),
    )

    # Step 1: infer
    cli_session_commands.run_step(session_path=str(session))
    out1 = capsys.readouterr().out
    session.write_text(session.read_text() + out1)

    # Step 2: batch execution
    cli_session_commands.run_step(session_path=str(session))
    out2 = capsys.readouterr().out
    assert "good content" in out2
    assert "[FAILED] tool 1 (get_structure):" in out2
    assert "broken.py" in out2





