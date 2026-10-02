import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from toas import cli_session_commands
from toas.config import OperatorConfig
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
            return {
                "content": '{"state_patch":{"progress":["started"]},"tool_calls":[{"tool_name":"read_file","args":{"path":"later.txt"}}]}'
            }
        return {"content": '{"state_patch":{},"tool_calls":[]}'}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate_state_packet=generate), {}),
    )

    from toas import step as step_mod

    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _working: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda *_args: ())

    # Both preview modes exercise the typed-state preview route without advancing it.
    base_text = session.read_text()
    session.write_text(
        base_text
        + (
            "\n\n## TOAS:USER\n\nPlease inspect the current state.\n\n"
            "## TOAS:USER\n\n## RESULT\n\nA prior result.\n"
        )
    )
    cli_session_commands.run_step(session_path=str(session), preview=True)
    assert '"phase": "infer"' in capsys.readouterr().out
    with monkeypatch.context() as m:
        m.setattr(
            cli_session_commands,
            "_resolve_state_input_turns",
            lambda **kwargs: (kwargs["normalized_transcript"], kwargs["input_turns"], [], True),
        )
        cli_session_commands.run_step(session_path=str(session))
        capsys.readouterr()
    session.write_text(base_text)

    # Step 1: infer
    session.write_text(base_text.rstrip("\n"))
    initial_text = session.read_text()
    cli_session_commands.run_step(session_path=str(session))
    assert session.read_text() == initial_text  # disk is not mutated by run_step
    out1 = capsys.readouterr().out
    assert "progress:\n  - started" in out1
    session.write_text(session.read_text() + out1)  # simulate >> session.md
    assert "Earlier conversation." in session.read_text()

    cli_session_commands.run_step(session_path=str(session), preview=True)
    assert '"phase": "execute_batch"' in capsys.readouterr().out
    session.write_text(session.read_text().rstrip("\n"))

    # Step 2: batch execution
    before_step2 = session.read_text()
    projected = []
    cli_session_commands.run_step(session_path=str(session), on_projection_nodes=projected.extend)
    assert session.read_text() == before_step2
    out2 = capsys.readouterr().out
    assert projected
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
        "state_transition",
        "state_diff",
        "state_snapshot",
        "state_observation",
        "state_tool_request",
        "state_transition",
        "state_tool_result",
        "state_transition",
        "state_transition",
        "state_diff",
        "state_snapshot",
        "state_observation",
    ]
    message_roles = [record["role"] for record in records if "role" in record]
    assert "state" in message_roles
    assert packets[-1]["observation"]["tool_outcomes"][0]["status"] == "completed"
    monkeypatch.setattr(cli_session_commands, "write_llm_call_record", lambda *_a, **_k: None)
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (
            config,
            {},
            SimpleNamespace(
                generate_state_packet=lambda _packet: {
                    "content": '{"state_patch":{},"tool_calls":[]}',
                    "_llm_call": {"requested_model": "test"},
                }
            ),
            {},
        ),
    )
    cli_session_commands.run_step(session_path=str(session), preview_response=True)
    assert capsys.readouterr().out.startswith("{")


def test_state_step_cli_truncated_tool_result_in_transcript_takes_precedence(
    monkeypatch, tmp_path, capsys
):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()
    session.write_text("## TOAS:STATE/1\n\nstate: {goal: inspect, progress: []}\n")
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
            return {
                "content": '{"state_patch":{"progress":["reading"]},"tool_calls":[{"tool_name":"read_file","args":{"path":"huge.txt"}}]}'
            }
        return {"content": '{"state_patch":{},"tool_calls":[]}'}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate_state_packet=generate), {}),
    )

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
    truncated_transcript = transcript_before_truncation.replace(
        "line 5", "[TRUNCATED AFTER LINE 4]"
    )
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


def test_state_step_cli_deleted_tool_result_in_transcript_is_not_resurrected(
    monkeypatch, tmp_path, capsys
):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    events_path.touch()
    session.write_text("## TOAS:STATE/1\n\nstate: {goal: inspect, progress: []}\n")
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
            return {
                "content": '{"state_patch":{"progress":["reading"]},"tool_calls":[{"tool_name":"read_file","args":{"path":"data.txt"}}]}'
            }
        return {"content": '{"state_patch":{},"tool_calls":[]}'}

    config = SimpleNamespace(shell=SimpleNamespace(assistant_timeout_s=5))
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (config, {}, SimpleNamespace(generate_state_packet=generate), {}),
    )

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


def test_user_turn_after_state_is_inferred_directly_when_frontier_is_non_executable(
    monkeypatch, tmp_path, capsys
):
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

    assert packets[0]["observation"]["user_inputs"] == [{"content": "Read the project manifest."}]


def test_appended_user_and_control_intents_use_normal_frontier_and_embed_results(
    monkeypatch, tmp_path
):
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
        return [
            make_result_node(
                f"result from {frontier['role']}",
                origin_role=frontier["role"],
                origin_kind="slash_command",
            )
        ], []

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

    updated, resolved_input_turns, _events, intent_resolved = (
        cli_session_commands._resolve_state_input_turns(
            deps=deps,
            events_path=events_path,
            session_path=session,
            session_newline="\n",
            normalized_transcript=transcript,
        )
    )

    assert intent_resolved is True
    assert [role for _text, role in calls] == ["user", "control"]
    assert "## TOAS:STATE/1" in calls[0][0]
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

    updated, resolved_input_turns, _events, intent_resolved = (
        cli_session_commands._resolve_state_input_turns(
            deps=deps,
            events_path=events_path,
            session_path=session,
            session_newline="\n",
            normalized_transcript=transcript,
        )
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
        "## TOAS:STATE/1\n\nstate: {goal: inspect}\n\n## TOAS:USER\n\nRead the project manifest.\n"
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
    _updated, _resolved_inputs, _events, intent_resolved = (
        cli_session_commands._resolve_state_input_turns(
            deps=deps,
            events_path=events_path,
            session_path=session,
            session_newline="\n",
            normalized_transcript=transcript,
        )
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

    initial_transcript = "## TOAS:STATE/1\n\nstate:\n  goal: check tasks\n  progress: []\n"
    session.write_text(initial_transcript)
    append_state_step_records(
        str(events_path),
        [
            {
                "kind": "state_snapshot",
                "transition_id": "st0",
                "state": {"goal": "check tasks", "progress": []},
            },
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
                "content": json.dumps(
                    {
                        "state_patch": {"progress": ["found task"]},
                        "tool_calls": [{"tool_name": "read_file", "args": {"path": "task.txt"}}],
                    }
                )
            }
        return {
            "content": json.dumps(
                {
                    "state_patch": {"progress": ["found task", "read task"]},
                    "tool_calls": [],
                }
            )
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


def test_state_step_materializes_state_turns_and_participates_in_heads_and_project_transcript(
    monkeypatch, tmp_path, capsys
):
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
            "content": json.dumps(
                {
                    "state_patch": {"progress": ["reading"]},
                    "tool_calls": [],
                }
            )
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
    write_message_events(
        str(events_path),
        [
            {"id": "n1", "parent": None, "role": "user", "content": "start"},
            {
                "id": "n2",
                "parent": "n1",
                "role": "state",
                "content": "state: {goal: A, count: 1}",
                "metadata": {"marker": "TOAS:STATE/1"},
            },
            {
                "id": "n3",
                "parent": "n1",
                "role": "state",
                "content": "state: {goal: B, count: 10}",
                "metadata": {"marker": "TOAS:STATE/1"},
            },
        ],
    )
    append_state_step_records(
        str(events_path),
        [
            {
                "kind": "state_snapshot",
                "transition_id": "st_a",
                "state": {"goal": "A", "count": 1},
                "message_id": "n2",
            },
            {
                "kind": "state_snapshot",
                "transition_id": "st_b",
                "state": {"goal": "B", "count": 10},
                "message_id": "n3",
            },
        ],
    )

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


def test_state_branching_from_prior_state_creates_dag_branch_without_mutation(
    monkeypatch, tmp_path, capsys
):
    session = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    session.write_text(
        "## TOAS:USER\n\nstart\n\n## TOAS:STATE/1\n\nstate:\n  goal: original\n  progress: []\n"
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
        return {
            "content": json.dumps({"state_patch": {"progress": [f"step_{goal}"]}, "tool_calls": []})
        }

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
        "## TOAS:USER\n\nstart\n\n## TOAS:STATE/1\n\nstate:\n  goal: alternative\n  progress: []\n"
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
    session.write_text("## TOAS:STATE/1\n\nstate:\n  goal: inspect\n  progress: []\n")
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
                    "content": json.dumps(
                        {
                            "state_patch": {"progress": ["inspecting"]},
                            "tool_calls": [
                                {"tool_name": "get_structure", "args": {"path": str(tmp_path)}}
                            ],
                        }
                    )
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
    session.write_text("## TOAS:STATE/1\n\nstate:\n  goal: inspect\n  progress: []\n")
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
                    "content": json.dumps(
                        {
                            "state_patch": {"progress": ["inspecting"]},
                            "tool_calls": [
                                {"tool_name": "read_file", "args": {"path": "good.txt"}},
                                {"tool_name": "get_structure", "args": {"path": str(tmp_path)}},
                            ],
                        }
                    )
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


def test_state_input_resolution_no_inputs_and_callable_without_results(monkeypatch, tmp_path):
    events = tmp_path / "events.jsonl"
    events.touch()
    deps = SimpleNamespace(step_fn=lambda *_args, **_kwargs: ([], []))
    empty = cli_session_commands._resolve_state_input_turns(
        deps=deps,
        events_path=events,
        session_path=tmp_path / "session.md",
        session_newline="\n",
        normalized_transcript="## TOAS:STATE/1\n\nstate: {}\n",
        prefix_turns=[],
        state_turn={},
        input_turns=[],
    )
    assert empty[1:] == ([], [], False)
    monkeypatch.setattr(
        cli_session_commands,
        "_build_runtime_context",
        lambda **_kwargs: {
            "events": [],
            "log": [],
            "head_id": None,
            "lineage": [],
        },
    )
    monkeypatch.setattr(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        lambda **_kwargs: (object(), {}, object(), {}),
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_kwargs", lambda **_kwargs: {})
    from toas.runtime import step_runtime

    monkeypatch.setattr(step_runtime, "_frontier_has_callable_intent", lambda **_kwargs: True)
    resolved = cli_session_commands._resolve_state_input_turns(
        deps=deps,
        events_path=events,
        session_path=tmp_path / "session.md",
        session_newline="\n",
        normalized_transcript="## TOAS:STATE/1\n\nstate: {}\n",
        prefix_turns=[],
        state_turn={},
        input_turns=[{"role": "user", "content": "read the file"}],
    )
    assert resolved[1] == [{"role": "user", "content": "read the file"}]
    assert resolved[3] is True


def test_state_cli_execute_batch_without_result_nodes_uses_status_fallback(
    monkeypatch, tmp_path, capsys
):
    from toas.runtime import state_step
    from toas.transcript import parse_transcript

    events = tmp_path / "events.jsonl"
    events.touch()
    transcript = "## TOAS:STATE/1\n\nstate: {goal: inspect}"
    turns = parse_transcript(transcript)
    monkeypatch.setattr(
        cli_session_commands,
        "_build_runtime_context",
        lambda **_kwargs: {
            "command_cwd": str(tmp_path),
            "workspace_mode": "strict",
            "workspace_roots": [str(tmp_path)],
            "log": [],
            "head_id": None,
            "lineage": [],
        },
    )
    monkeypatch.setattr(
        state_step,
        "step_state",
        lambda **_kwargs: {
            "phase": "execute_batch",
            "outcomes": [],
            "status": "completed",
        },
    )
    cli_session_commands._run_state_step(
        deps=SimpleNamespace(),
        events_path=events,
        session_path=tmp_path / "session.md",
        normalized_transcript=transcript,
        session_newline="\n",
        events=[],
        turns=turns,
        state_index=0,
        parsed_turn=parse_state_turn(turns[0]),
    )
    assert "[COMPLETED] batch execution completed" in capsys.readouterr().out


def test_preview_rejects_ordinary_transcript_without_state_turn(monkeypatch, tmp_path):
    session = tmp_path / "session.md"
    session.write_text("## TOAS:USER\n\nhello")
    events = tmp_path / "events.jsonl"
    deps = SimpleNamespace(
        resolve_events_path=lambda: events,
        ensure_file=lambda path: path.touch(exist_ok=True),
        resolve_session_path=lambda _events: session,
        read_text_preserve_newlines=lambda path: path.read_text(),
        detect_newline_style=lambda _text: "\n",
        apply_newline_style=lambda text, _newline: text,
    )
    monkeypatch.setattr(cli_session_commands, "_build_step_cli_deps", lambda: deps)
    monkeypatch.setattr(cli_session_commands, "read_log", lambda _path: [])
    with pytest.raises(SystemExit, match="requires a typed state turn"):
        cli_session_commands.run_step(preview=True)


def test_state_preview_skips_result_turns_and_refuses_unresolved_intent(
    monkeypatch, tmp_path, capsys
):
    from toas.runtime import step_runtime

    state_turn = {"role": "state", "marker": "## TOAS:STATE/1", "content": "state: {}"}
    turns = [
        state_turn,
        {"role": "user", "content": "## RESULT\n\nold result"},
        {"role": "user", "content": "prose with attached result"},
        {"role": "user", "content": "## RESULT\n\nnew result"},
        {"role": "user", "content": "$ echo maybe"},
    ]
    monkeypatch.setattr(step_runtime, "_frontier_has_callable_intent", lambda **_kwargs: True)
    cli_session_commands._run_state_step(
        deps=SimpleNamespace(),
        events_path=tmp_path / "events.jsonl",
        session_path=tmp_path / "session.md",
        normalized_transcript="",
        session_newline="\n",
        events=[],
        turns=turns,
        state_index=0,
        parsed_turn={"turn_type": "state", "state": {}, "observation": None},
        preview=True,
    )
    assert '"phase": "resolve_user_intent"' in capsys.readouterr().out


def test_state_user_command_durable_lineage_and_subsequent_inference(monkeypatch, tmp_path, capsys):
    import os
    from unittest.mock import patch

    from toas.graph import list_heads, message_lineage

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        session = tmp_path / "session.md"
        events_path = tmp_path / ".toas" / "events.jsonl"
        session.write_text(
            "## TOAS:STATE/1\n\n"
            "state:\n  goal: inspect repo\n  progress: []\n\n"
            "## TOAS:USER\n\n"
            "Note the current branch.\n\n"
            "## TOAS:USER\n\n"
            "$ echo active-feature\n"
        )

        # Step 1: execute user command
        cli_session_commands.run_step(session_path=str(session))
        step1_out = capsys.readouterr().out
        assert "active-feature" in step1_out
        assert "## RESULT" in step1_out

        events1 = read_log(str(events_path))
        heads1 = list_heads(events1)
        assert len(heads1) == 1
        user_head_id = heads1[0]["id"]
        assert heads1[0]["role"] == "user"

        lineage1 = message_lineage(events1)
        assert len(lineage1) == 3
        assert lineage1[0]["role"] == "state"
        assert lineage1[1]["role"] == "user"
        assert lineage1[1]["content"] == "Note the current branch."
        assert lineage1[1]["parent"] == lineage1[0]["id"]
        assert lineage1[2]["role"] == "user"
        assert lineage1[2]["content"] == "$ echo active-feature"
        assert lineage1[2]["parent"] == lineage1[1]["id"]
        assert lineage1[2]["id"] == user_head_id

        # Tool request and result records should be present and stitched
        tool_requests = [e for e in events1 if e.get("kind") == "tool_request"]
        tool_results = [e for e in events1 if e.get("kind") == "tool_result"]
        assert len(tool_requests) == 1
        assert len(tool_results) == 1

        # Now simulate session.md update with embedded result
        session.write_text(
            session.read_text()
            + "\n\n## TOAS:USER\n\n## RESULT\n\n[OK] shell: exit=0\nstdout:\n```text toas-output kind=stdout source=tool.shell potency=inert\nactive-feature\n```\n"
        )

        # Step 2: preview should be eligible for inference
        cli_session_commands.run_step(session_path=str(session), preview=True)
        preview_out = capsys.readouterr().out
        assert '"phase": "infer"' in preview_out
        preview_data = json.loads(preview_out)
        req_packet = json.loads(preview_data["request_messages"][0]["content"])
        # Both user inputs and embedded result enter the compound observation
        assert req_packet["observation"]["user_inputs"] == [
            {"content": "Note the current branch."},
            {"content": "$ echo active-feature"},
        ]
        assert any(
            "active-feature" in node.get("content", "")
            for outcome in req_packet["observation"].get("tool_outcomes", [])
            for node in outcome.get("result", [])
        )

        # Step 3: full inference step advancing to STATE/2
        class MockRunner:
            def generate_state_packet(self, packet):
                return {
                    "content": json.dumps(
                        {
                            "state_patch": {"progress": ["identified active-feature"]},
                            "tool_calls": [],
                        }
                    )
                }

        from toas.config import OperatorConfig

        config = OperatorConfig()
        with patch.object(
            cli_session_commands,
            "_resolve_runtime_generation_context",
            return_value=(config, {}, MockRunner(), {}),
        ):
            cli_session_commands.run_step(session_path=str(session))

        step3_out = capsys.readouterr().out
        assert "## TOAS:STATE/2" in step3_out

        events2 = read_log(str(events_path))
        heads2 = list_heads(events2)
        assert len(heads2) == 1
        assert heads2[0]["role"] == "state"
        assert heads2[0]["metadata"].get("marker") == "## TOAS:STATE/2"
        assert heads2[0]["parent"] == user_head_id

        lineage2 = message_lineage(events2)
        assert len(lineage2) == 4
        assert [m["role"] for m in lineage2] == ["state", "user", "user", "state"]
        assert lineage2[3]["id"] == heads2[0]["id"]
    finally:
        os.chdir(old_cwd)


def test_state_turn_pending_tools_execute_at_frontier(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / ".toas" / "events.jsonl"
    session.write_text(
        "## TOAS:STATE/1\n\n"
        "state:\n  goal: run tools\n"
        "pending_tools:\n"
        "  - tool_name: shell\n"
        "    args:\n"
        "      command: echo frontier-tool-executed\n"
    )
    monkeypatch.chdir(tmp_path)
    from toas import cli
    from toas.graph import read_log

    # Stepping on frontier state turn with pending_tools executes the batch
    cli.run_step(session_path=str(session))
    out = capsys.readouterr().out
    assert "frontier-tool-executed" in out

    records = read_log(str(events_path))
    results = [r for r in records if r.get("kind") == "state_tool_result"]
    assert len(results) == 1
    assert results[0]["status"] == "completed"


def test_state_turn_tools_outside_frontier_do_not_execute(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / ".toas" / "events.jsonl"
    session.write_text(
        "## TOAS:STATE/1\n\n"
        "state:\n  goal: step 1\n"
        "pending_tools:\n"
        "  - tool_name: shell\n"
        "    args:\n"
        "      command: echo historical-tool\n\n"
        "## TOAS:USER\n\n## RESULT\n\n[COMPLETED] tool 0\n\n"
        "## TOAS:STATE/2\n\n"
        "state:\n  goal: step 2\n"
    )
    monkeypatch.chdir(tmp_path)
    from toas import cli
    from toas.graph import read_log

    class MockRunner:
        def generate_state_packet(self, packet):
            assert packet["state"]["goal"] == "step 2"
            return {"content": json.dumps({"state_patch": {"step": "done"}, "tool_calls": []})}

    with patch.object(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        return_value=(OperatorConfig(), {}, MockRunner(), {}),
    ):
        cli.run_step(session_path=str(session))

    out = capsys.readouterr().out
    # Historical tool in STATE/1 must NOT have executed
    assert "historical-tool" not in out
    assert "## TOAS:STATE/3" in out

    records = read_log(str(events_path))
    results = [r for r in records if r.get("kind") == "state_tool_result"]
    assert len(results) == 0


def test_state_turn_run_command_parity(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    session.write_text(
        "## TOAS:STATE/1\n\n"
        "state:\n  goal: test run parity\n"
        "pending_tools:\n"
        "  - tool_name: shell\n"
        "    args:\n"
        "      command: echo run-parity-success\n\n"
        "## TOAS:USER\n\n"
        "/run\n"
    )
    monkeypatch.chdir(tmp_path)
    from toas import cli

    # Step 1: /run resolves pending_tools from STATE/1 and executes them
    cli.run_step(session_path=str(session))
    out1 = capsys.readouterr().out
    assert "run-parity-success" in out1
    assert "## RESULT" in out1
    session.write_text(session.read_text() + "\n\n" + out1)

    # Step 2: Next step infers STATE/2 incorporating the run result
    class MockRunner:
        def generate_state_packet(self, packet):
            obs = packet["observation"]
            assert any("run-parity-success" in str(x) for x in obs.get("tool_outcomes", []))
            return {"content": json.dumps({"state_patch": {"observed": True}, "tool_calls": []})}

    with patch.object(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        return_value=(OperatorConfig(), {}, MockRunner(), {}),
    ):
        cli.run_step(session_path=str(session))

    out2 = capsys.readouterr().out
    assert "## TOAS:STATE/2" in out2
    assert "observed: true" in out2


def test_state_turn_branching_seeds_snapshot_and_isolates_diff(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / ".toas" / "events.jsonl"
    session.write_text("## TOAS:STATE/1\n\nstate:\n  goal: branch-A\n  val: 10\n")
    monkeypatch.chdir(tmp_path)
    from toas import cli
    from toas.graph import list_heads, read_log

    call_count = 0

    def generate(packet):
        nonlocal call_count
        call_count += 1
        return {
            "content": json.dumps(
                {"state_patch": {"val": packet["state"]["val"] + 1}, "tool_calls": []}
            )
        }

    runner = SimpleNamespace(generate_state_packet=generate)
    with patch.object(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        return_value=(OperatorConfig(), {}, runner, {}),
    ):
        # Step 1 on Branch A: infers STATE/2
        cli.run_step(session_path=str(session))
        out1 = capsys.readouterr().out
        session.write_text(session.read_text() + "\n\n" + out1)

    events1 = read_log(str(events_path))
    heads1 = list_heads(events1)
    assert len(heads1) == 1
    branch_a_head = heads1[0]["id"]

    # Now simulate user editing session.md back to an alternative STATE/1:
    session.write_text("## TOAS:STATE/1\n\nstate:\n  goal: branch-B\n  val: 100\n")
    with patch.object(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        return_value=(OperatorConfig(), {}, runner, {}),
    ):
        # Step 2 on Branch B: infers STATE/2 from branch-B base
        cli.run_step(session_path=str(session))
        out2 = capsys.readouterr().out
        assert "val: 101" in out2
        session.write_text(session.read_text() + "\n\n" + out2)

    events2 = read_log(str(events_path))
    heads2 = list_heads(events2)
    assert len(heads2) == 2
    assert branch_a_head in {h["id"] for h in heads2}

    # Verify snapshots: both branch A's state and branch B's state have dedicated snapshots
    snapshots = [r for r in events2 if r.get("kind") == "state_snapshot"]
    branch_b_snapshots = [s for s in snapshots if s.get("state", {}).get("goal") == "branch-B"]
    assert len(branch_b_snapshots) >= 1
    seed_b = next(s for s in branch_b_snapshots if s.get("transition_id", "").startswith("seed_"))
    assert seed_b["state"]["val"] == 100

    # Now test a STATE-DIFF on Branch B: it must diff relative to Branch B's snapshot!
    session.write_text(
        "## TOAS:STATE/1\n\n"
        "state:\n  goal: branch-B\n  val: 100\n\n"
        "## TOAS:STATE-DIFF/2\n\n"
        "```yaml\n"
        "state_patch:\n"
        "  val: 200\n"
        "```\n"
    )
    captured = {}

    def generate_diff(packet):
        captured.update(packet)
        return {"content": json.dumps({"state_patch": {}, "tool_calls": []})}

    with patch.object(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        return_value=(
            OperatorConfig(),
            {},
            SimpleNamespace(generate_state_packet=generate_diff),
            {},
        ),
    ):
        cli.run_step(session_path=str(session))

    assert captured["state"]["goal"] == "branch-B"
    assert captured["state"]["val"] == 200


def test_state_proposal_overtake_and_cancellation(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    # Seed session with an inferred state turn that has a pending tool transition in events
    append_state_step_records(
        str(events_path),
        [
            {
                "kind": "state_snapshot",
                "transition_id": "st0",
                "state": {"goal": "test"},
                "message_id": "m1",
            },
            {
                "kind": "state_transition",
                "transition_id": "st1",
                "status": "pending",
                "tool_calls": [{"tool_name": "shell", "args": {"command": "echo stale-proposal"}}],
                "message_id": "m1",
            },
        ],
    )
    # Operator explicitly empties pending_tools in session.md
    session.write_text("## TOAS:STATE/1\n\nstate:\n  goal: test\npending_tools: []\n")
    monkeypatch.chdir(tmp_path)
    from toas import cli
    from toas.graph import read_log

    class MockRunner:
        def generate_state_packet(self, packet):
            return {"content": json.dumps({"state_patch": {"cancelled": True}, "tool_calls": []})}

    with patch.object(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        return_value=(OperatorConfig(), {}, MockRunner(), {}),
    ):
        cli.run_step(session_path=str(session))

    out = capsys.readouterr().out
    # Stale proposal must NOT have executed
    assert "stale-proposal" not in out
    assert "## TOAS:STATE/2" in out

    records = read_log(str(events_path))
    # The pending transition st1 was marked cancelled
    cancelled_records = [
        r
        for r in records
        if r.get("kind") == "state_transition"
        and r.get("transition_id") == "st1"
        and r.get("status") == "cancelled"
    ]
    assert len(cancelled_records) == 1


def test_state_intermediate_user_turn_edit_branches_dag(monkeypatch, tmp_path, capsys):
    session = tmp_path / "session.md"
    events_path = tmp_path / ".toas" / "events.jsonl"
    session.write_text(
        "## TOAS:STATE/1\n\nstate:\n  goal: original\n\n"
        "## TOAS:USER\n\n$ echo turn-A\n\n"
        "## RESULT\n\nturn-A\n\n"
        "## TOAS:STATE/2\n\nstate:\n  goal: advanced\n"
    )
    monkeypatch.chdir(tmp_path)
    from toas import cli
    from toas.graph import list_heads, read_log

    class MockRunner:
        def generate_state_packet(self, packet):
            return {"content": json.dumps({"state_patch": {"step": "next"}, "tool_calls": []})}

    with patch.object(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        return_value=(OperatorConfig(), {}, MockRunner(), {}),
    ):
        # Step 1: establish initial lineage
        cli.run_step(session_path=str(session))
        capsys.readouterr()

    events1 = read_log(str(events_path))
    heads1 = list_heads(events1)
    assert len(heads1) == 1
    head_a = heads1[0]["id"]

    # Now edit intermediate user turn to branch history at STATE/1:
    session.write_text(
        "## TOAS:STATE/1\n\nstate:\n  goal: original\n\n## TOAS:USER\n\n$ echo turn-B\n"
    )
    deltas = []
    # Step 2: resolves user turn-B and executes it
    cli_session_commands.run_step(session_path=str(session), on_projection_delta=deltas.append)
    out2 = capsys.readouterr().out
    assert "turn-B" in out2
    session.write_text(session.read_text() + "\n" + deltas[-1])

    # Step 3: next state step infers STATE/2 on Branch B
    class MockRunnerB:
        def generate_state_packet(self, packet):
            obs = packet["observation"]
            assert any("turn-B" in str(x) for x in obs.get("tool_outcomes", []))
            return {"content": json.dumps({"state_patch": {"branch": "B"}, "tool_calls": []})}

    with patch.object(
        cli_session_commands,
        "_resolve_runtime_generation_context",
        return_value=(OperatorConfig(), {}, MockRunnerB(), {}),
    ):
        cli_session_commands.run_step(session_path=str(session), on_projection_delta=deltas.append)
        assert any("branch: B" in d for d in deltas)

    events2 = read_log(str(events_path))
    heads2 = list_heads(events2)
    assert len(heads2) == 2
    head_ids = {h["id"] for h in heads2}
    assert head_a in head_ids
