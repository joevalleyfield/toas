from __future__ import annotations

from pathlib import Path

from toas import cli
from toas.graph import read_log
from toas.runtime import step_generation_runtime as sgr


def _setup_workspace(tmp_path: Path, session_content: str = "## TOAS:USER\n\nHello\n") -> Path:
    toas_dir = tmp_path / ".toas"
    toas_dir.mkdir(parents=True, exist_ok=True)
    session_file = toas_dir / "session.md"
    session_file.write_text(session_content, encoding="utf-8")
    config_file = toas_dir / "toas.toml"
    config_file.write_text(
        '[endpoint.default]\n'
        'provider = "openai-compatible"\n'
        'base_url = "http://localhost:8000/v1"\n'
        'api_key = "test-key"\n'
        '[model]\n'
        'default = "test-model"\n'
        '[shell]\n'
        'allowed_commands = ["echo", "ls"]\n',
        encoding="utf-8",
    )
    return toas_dir


def test_bounded_step_single_step_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_workspace(tmp_path)

    call_count = 0

    def fake_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "role": "assistant",
            "content": "Hi there! How can I help?",
            "response": {"content": "Hi there! How can I help?", "model": "test-model"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    outcome = cli.run_step()
    assert call_count == 1
    assert outcome.completed is True
    assert outcome.turns_executed == 1
    assert outcome.quiescent is True
    assert outcome.stop_reason == "quiescent"

    events = read_log(str(tmp_path / ".toas" / "events.jsonl"))
    msg_events = [e for e in events if e.get("role") in {"user", "assistant"}]
    assert len(msg_events) == 2
    assert msg_events[0]["content"] == "Hello"
    assert msg_events[1]["content"] == "Hi there! How can I help?"


def test_bounded_step_quiescent_early_stop(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_workspace(tmp_path)

    call_count = 0

    def fake_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "role": "assistant",
            "content": "Text only answer.",
            "response": {"content": "Text only answer.", "model": "test-model"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    # Request max 5 turns, but assistant immediately yields with text only
    outcome = cli.run_step(max_turns=5)
    assert call_count == 1
    assert outcome.completed is True
    assert outcome.turns_executed == 1
    assert outcome.quiescent is True
    assert outcome.stop_reason == "quiescent"


def test_bounded_step_multi_turn_chaining(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_workspace(tmp_path)

    call_count = 0

    def fake_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Turn 1: tool call
            content = "```yaml\n- tool_name: echo\n  args:\n    text: hello_bounded\n```"
            return {
                "role": "assistant",
                "content": content,
                "response": {"content": content, "model": "test-model"},
            }
        # Turn 3: final answer after observing tool result from Turn 2
        return {
            "role": "assistant",
            "content": "The command returned hello_bounded successfully.",
            "response": {"content": "The command returned hello_bounded successfully.", "model": "test-model"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    outcome = cli.run_step(max_turns=5)
    # Turn 1: assistant tool call
    # Turn 2: tool execution (no LLM call)
    # Turn 3: assistant final text
    assert call_count == 2
    assert outcome.completed is True
    assert outcome.turns_executed == 3
    assert outcome.quiescent is True
    assert outcome.stop_reason == "quiescent"

    events = read_log(str(tmp_path / ".toas" / "events.jsonl"))
    kinds = [e.get("kind") or e.get("role") for e in events]
    assert "user" in kinds
    assert "assistant" in kinds
    assert "tool_request" in kinds
    assert "tool_result" in kinds


def test_bounded_step_safety_cap(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_workspace(tmp_path)

    def fake_generate(messages, **kwargs):
        content = "```yaml\n- tool_name: echo\n  args:\n    text: repeat\n```"
        return {
            "role": "assistant",
            "content": content,
            "response": {"content": content, "model": "test-model"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    # Model generates tool call every turn; halt after 3 turns
    outcome = cli.run_step(max_turns=3)
    assert outcome.completed is True
    assert outcome.turns_executed == 3
    assert outcome.stop_reason == "turn_limit"


def test_bounded_step_durable_parity(monkeypatch, tmp_path):
    # Run multi-step in workspace A
    ws_multi = tmp_path / "multi"
    ws_multi.mkdir()
    _setup_workspace(ws_multi)

    # Run single-step in workspace B
    ws_single = tmp_path / "single"
    ws_single.mkdir()
    _setup_workspace(ws_single)

    def fake_generate(messages, **kwargs):
        # If last message is a tool result, produce final text
        last = messages[-1]["content"] if messages else ""
        if "hello_parity" in last or "RESULT" in last or "[OK]" in last:
            return {
                "role": "assistant",
                "content": "Done with parity.",
                "response": {"content": "Done with parity.", "model": "test-model"},
            }
        content = "```yaml\n- tool_name: echo\n  args:\n    text: hello_parity\n```"
        return {
            "role": "assistant",
            "content": content,
            "response": {"content": content, "model": "test-model"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    # Run multi-step
    monkeypatch.chdir(ws_multi)
    outcome_multi = cli.run_step(max_turns=5)
    assert outcome_multi.turns_executed == 3

    # Run single steps in ws_single, updating session.md as a user would with `>> session.md`
    monkeypatch.chdir(ws_single)
    o1 = cli.run_step()
    assert o1.turns_executed == 1
    (ws_single / ".toas" / "session.md").write_text(o1.transcript, encoding="utf-8")
    o2 = cli.run_step()
    assert o2.turns_executed == 1
    (ws_single / ".toas" / "session.md").write_text(o2.transcript, encoding="utf-8")
    o3 = cli.run_step()
    assert o3.turns_executed == 1
    (ws_single / ".toas" / "session.md").write_text(o3.transcript, encoding="utf-8")

    events_multi = read_log(str(ws_multi / ".toas" / "events.jsonl"))
    events_single = read_log(str(ws_single / ".toas" / "events.jsonl"))

    kinds_multi = [e.get("kind") or e.get("role") for e in events_multi]
    kinds_single = [e.get("kind") or e.get("role") for e in events_single]
    assert kinds_multi == kinds_single


def test_bounded_step_slash_command_in_transcript(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_workspace(tmp_path, session_content="## TOAS:USER\n\n/step 3\nRun task\n")

    call_count = 0

    def fake_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Model should receive "Run task", not "/step 3"
            assert "/step" not in messages[-1]["content"]
            assert "Run task" in messages[-1]["content"]
            content = "```yaml\n- tool_name: echo\n  args:\n    text: from_slash\n```"
            return {
                "role": "assistant",
                "content": content,
                "response": {"content": content, "model": "test-model"},
            }
        return {
            "role": "assistant",
            "content": "All finished.",
            "response": {"content": "All finished.", "model": "test-model"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    # Bare cli.run_step() with no CLI count; /step 3 in transcript should set budget to 3
    outcome = cli.run_step()
    assert outcome.completed is True
    assert outcome.turns_executed == 3
    assert outcome.quiescent is True
    assert outcome.stop_reason == "quiescent"


def test_bounded_step_cli_precedence_over_transcript(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_workspace(tmp_path, session_content="## TOAS:USER\n\n/step 10\nRun infinite tool\n")

    def fake_generate(messages, **kwargs):
        content = "```yaml\n- tool_name: echo\n  args:\n    text: loop\n```"
        return {
            "role": "assistant",
            "content": content,
            "response": {"content": content, "model": "test-model"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    # Transcript specifies /step 10, but CLI specifies max_turns=2
    # CLI count takes unconditional precedence!
    outcome = cli.run_step(max_turns=2)
    assert outcome.completed is True
    assert outcome.turns_executed == 2
    assert outcome.stop_reason == "turn_limit"


def test_bounded_step_operator_command_dispatch(tmp_path):
    from toas.config import OperatorConfig
    from toas.runtime.operator_commands import execute_operator_command

    config = OperatorConfig()
    nodes = execute_operator_command(
        "step",
        ["5"],
        execute=lambda *a, **k: None,
        events=[],
        working=[{"role": "user", "content": "/step 5"}],
        transcript="",
        command_cwd=str(tmp_path),
        previous_command_cwd=None,
        workspace_mode="free",
        workspace_roots=[str(tmp_path)],
        config=config,
    )
    assert len(nodes) == 1
    assert "[STEP] budget: 5" in nodes[0]["content"]

    # Invalid count returns usage
    nodes_err = execute_operator_command(
        "step",
        ["abc"],
        execute=lambda *a, **k: None,
        events=[],
        working=[{"role": "user", "content": "/step abc"}],
        transcript="",
        command_cwd=str(tmp_path),
        previous_command_cwd=None,
        workspace_mode="free",
        workspace_roots=[str(tmp_path)],
        config=config,
    )
    assert len(nodes_err) == 1
    assert "usage: /step [N]" in nodes_err[0]["content"]


def test_bounded_step_user_consequence_continues_to_assistant(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "off")
    _setup_workspace(tmp_path, session_content="## TOAS:USER\n\n$ echo hello_user\n")

    call_count = 0

    def fake_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "role": "assistant",
            "content": "I see the output hello_user.",
            "response": {"content": "I see the output hello_user.", "model": "test-model"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    outcome = cli.run_step(max_turns=3)
    assert call_count == 1
    assert outcome.completed is True
    assert outcome.turns_executed == 2
    assert outcome.quiescent is True
    assert outcome.stop_reason == "quiescent"
