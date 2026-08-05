from __future__ import annotations

import pytest

from toas.config import OperatorConfig
from toas.graph import active_compaction_projection, read_log
from toas.runtime.session_step_edges import (
    _apply_compaction_updates,
    apply_result_side_effects,
    extract_operator_command_tail,
    persist_messages_and_llm_calls,
    redact_secret_lines,
    split_append_nodes,
    stitch_frontier_records,
)
from toas.runtime.step_context_runtime import build_runtime_context


def test_split_append_nodes_filters_and_sanitizes():
    append_set = [
        {"role": "user", "content": "/config secret set llm_api_key abc123", "metadata": {}},
        {"role": "assistant", "content": "x", "metadata": {"transient_projection": "frontier_flip"}},
        {"role": "result", "content": "ok"},
    ]

    _messages, persisted, results = split_append_nodes(
        append_set,
        sanitize_secret_command_content=lambda s: s.replace("abc123", "[REDACTED]"),
        is_transient_projection_node=lambda n: n.get("metadata", {}).get("transient_projection") is not None,
    )

    assert len(results) == 1
    assert persisted == [{"role": "user", "content": "/config secret set llm_api_key [REDACTED]", "metadata": {}}]


def test_persist_messages_and_llm_calls_writes_records(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    written = {"llm_calls": 0}

    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_message_events",
        lambda _p, nodes: [{"id": "n1", **n} for n in nodes],
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_llm_call_record",
        lambda *_args, **_kwargs: written.__setitem__("llm_calls", written["llm_calls"] + 1),
    )
    nodes = [{"role": "assistant", "content": "x", "_llm_call": {"request_messages": [], "requested_model": "m"}}]
    out = persist_messages_and_llm_calls(events_path, nodes)
    assert out[0]["id"] == "n1"
    assert written["llm_calls"] == 1


def test_stitch_frontier_records_writes_command_and_replay_tool_records(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    operator_config = OperatorConfig()
    calls = {"tool_request": 0, "tool_result": 0, "command_request": 0, "command_result": 0}

    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_command_request_record",
        lambda *_args, **_kwargs: calls.__setitem__("command_request", calls["command_request"] + 1) or {"payload": {"id": "r1"}},
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_command_result_record",
        lambda *_args, **_kwargs: calls.__setitem__("command_result", calls["command_result"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_tool_request_record",
        lambda *_args, **_kwargs: calls.__setitem__("tool_request", calls["tool_request"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_tool_result_record",
        lambda *_args, **_kwargs: calls.__setitem__("tool_result", calls["tool_result"] + 1),
    )

    materialized = [{"id": "n1", "role": "user", "content": "/pwd"}]
    result_nodes = [
        {"role": "result", "content": "done", "payload": {"content": "done"}},
        {
            "role": "result",
            "content": "replay",
            "replay_execution": {"target_message_index": 1, "request_plan": [{"tool_name": "echo_block", "args": {"content": "x"}}]},
        },
    ]
    lineage = [{"id": "n_target"}]
    prefix = stitch_frontier_records(
        events_path=events_path,
        materialized=materialized,
        operator_config=operator_config,
        result_nodes=result_nodes,
        head_id="n1",
        lineage=lineage,
        extract_operator_command_tail=lambda _content: ("pwd", []),
    )

    assert prefix == []
    assert calls["command_request"] == 1
    assert calls["command_result"] == 2
    assert calls["tool_request"] == 1
    assert calls["tool_result"] == 1


def test_stitch_frontier_records_does_not_add_empty_user_prefix_for_tool_results(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_tool_request_record",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_tool_result_record",
        lambda *_args, **_kwargs: None,
    )

    prefix = stitch_frontier_records(
        events_path=events_path,
        materialized=[{"id": "n1", "role": "user", "content": "please run this\n```yaml\n- tool_name: echo\n```"}],
        operator_config=OperatorConfig(),
        result_nodes=[{"role": "result", "content": "ran echo"}],
        head_id="n1",
        lineage=[{"id": "n1"}],
        extract_operator_command_tail=lambda _content: None,
    )

    assert prefix == []


def test_stitch_frontier_records_keeps_results_on_request_before_adopted_recovery(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    writes = {"request": [], "results": []}
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_tool_request_record",
        lambda _path, **kwargs: writes["request"].append(kwargs),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_tool_result_record",
        lambda _path, **kwargs: writes["results"].append(kwargs),
    )
    original = "```yaml\n- tool_name: echo\n  args:\n    text: done\n- tool_name: missing\n  args: {}\n- tool_name: echo\n  args:\n    text: later\n```"
    recovery = "Retry failed operation (edit directly, then step):\n\n```yaml\n- tool_name: missing\n  args: {}\n```"

    stitch_frontier_records(
        events_path=events_path,
        materialized=[
            {"id": "n1", "role": "user", "content": original, "provenance": {"source": "user_authored"}},
            {"id": "n2", "role": "user", "content": recovery, "provenance": {"source": "adopted"}},
        ],
        operator_config=OperatorConfig(),
        result_nodes=[
            {"role": "result", "content": "done", "payload": {"tool_name": "echo", "ok": True}},
            {"role": "result", "content": "failed", "payload": {"tool_name": "missing", "ok": False}},
        ],
        head_id="n2",
        lineage=[],
        extract_operator_command_tail=lambda _content: None,
    )

    assert writes["request"] == [
        {
            "message_id": "n1",
            "plan": [
                {"tool_name": "echo", "args": {"text": "done"}},
                {"tool_name": "missing", "args": {}},
                {"tool_name": "echo", "args": {"text": "later"}},
            ],
        }
    ]
    assert [item["message_id"] for item in writes["results"]] == ["n1", "n1"]


def test_apply_result_side_effects_updates_secret_and_session(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    session_path = tmp_path / "session.md"
    runtime_secrets: dict[str, str] = {}
    writes = {"queue": 0, "lens": 0, "intent": 0, "coordination": 0, "context": 0, "workspace": 0, "config": 0}

    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_execution_queue_record",
        lambda *_args, **_kwargs: writes.__setitem__("queue", writes["queue"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_lens_artifact_record",
        lambda *_args, **_kwargs: writes.__setitem__("lens", writes["lens"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_intent_record",
        lambda *_args, **_kwargs: writes.__setitem__("intent", writes["intent"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_coordination_state_record",
        lambda *_args, **_kwargs: writes.__setitem__("coordination", writes["coordination"] + 1),
    )

    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_command_context_record",
        lambda *_args, **_kwargs: writes.__setitem__("context", writes["context"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_workspace_scope_record",
        lambda *_args, **_kwargs: writes.__setitem__("workspace", writes["workspace"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_config_override_record",
        lambda *_args, **_kwargs: writes.__setitem__("config", writes["config"] + 1),
    )

    result_nodes = [
        {"role": "result", "content": "x", "queue_update": {"id": "q1", "status": "blocked", "next_index": 1}},
        {
            "role": "result",
            "content": "x",
            "lens_update": {
                "action": "set",
                "title": "repo-state",
                "distillation": "tests green",
                "source_pointers": ["n1"],
                "use_when": "planning",
            },
        },
        {
            "role": "result",
            "content": "x",
            "intent_update": {"intent_id": "i1", "title": "stabilize", "status": "active"},
        },
        {"role": "result", "content": "x", "coordination_state_update": {"id": "cs-1"}},
        {"role": "result", "content": "x", "context_update": {"cwd": str(tmp_path), "previous_cwd": str(tmp_path)}},
        {"role": "result", "content": "x", "workspace_update": {"mode": "strict", "roots": [str(tmp_path)]}},
        {"role": "result", "content": "x", "secret_update": {"key": "llm_api_key", "action": "set", "value": "k1"}},
        {"role": "result", "content": "x", "config_update": {"runtime": {"streaming_mode": "enabled"}}},
        {"role": "result", "content": "x", "session_update": {"transcript": "## TOAS:USER\n\nhi\n"}},
    ]

    apply_result_side_effects(
        events_path=events_path,
        result_nodes=result_nodes,
        operator_config=OperatorConfig(),
        session_path=session_path,
        session_newline="\n",
        runtime_secrets=runtime_secrets,
        serialize_operator_config_toml=lambda _cfg: "[llm]\nmodel='x'\n",
        write_text_with_newline_style=lambda *, path, text, newline, apply_newline_style_fn: path.write_text(
            apply_newline_style_fn(text, newline), encoding="utf-8"
        ),
        apply_newline_style=lambda text, _nl: text,
    )

    assert runtime_secrets["llm_api_key"] == "k1"
    assert writes == {"queue": 1, "lens": 1, "intent": 1, "coordination": 1, "context": 1, "workspace": 1, "config": 1}
    assert session_path.read_text(encoding="utf-8") == "## TOAS:USER\n\nhi\n"


def test_compaction_side_effect_persists_projection_message_evidence_and_bind(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        '{"id":"n1","parent":"n0","role":"user","content":"source","metadata":{}}\n',
        encoding="utf-8",
    )
    session_path = tmp_path / "session.md"
    original_transcript = "## TOAS:USER\n\nsource\n\n## TOAS:USER\n\n/compact\n"
    session_path.write_text(original_transcript, encoding="utf-8")
    handoff = "# Handoff Summary\n\n## Current Objective\nResume."
    projected_transcript = f"{original_transcript}\n## TOAS:ASSISTANT\n\n{handoff}\n"
    result_nodes = [
        {
            "role": "result",
            "content": handoff,
            "compaction_update": {
                "content": handoff,
                "source_message_ids": ["n1"],
                "source_head_id": "n1",
                "prompt_ref": "compaction/handoff_v1",
                "model_call": {
                    "request_messages": [{"role": "user", "content": "source"}],
                    "requested_model": "test-model",
                    "response_content": handoff,
                },
            },
        }
    ]

    apply_result_side_effects(
        events_path=events_path,
        result_nodes=result_nodes,
        operator_config=OperatorConfig(),
        session_path=session_path,
        session_newline="\n",
        runtime_secrets={},
        serialize_operator_config_toml=lambda _cfg: "",
        write_text_with_newline_style=lambda *, path, text, newline, apply_newline_style_fn: path.write_text(
            apply_newline_style_fn(text, newline), encoding="utf-8"
        ),
        apply_newline_style=lambda text, _nl: text,
    )

    events = read_log(str(events_path))
    projection_message = next(event for event in events if event.get("provenance", {}).get("source") == "llm_compaction")
    assert projection_message["role"] == "assistant"
    projection = active_compaction_projection(events)
    assert projection is not None
    assert projection["payload"] == {
        "projection_message_id": projection_message["id"],
        "source_message_ids": ["n1"],
        "prompt_ref": "compaction/handoff_v1",
        "selected": True,
        "source_head_id": "n1",
    }
    llm_call = next(event for event in events if event.get("kind") == "llm_call")
    assert llm_call["payload"]["message_id"] == projection_message["id"]
    assert session_path.read_text(encoding="utf-8") == original_transcript
    runtime = build_runtime_context(events=events, normalized_transcript=projected_transcript)
    assert runtime["bind_index"] == 0


def test_compaction_side_effect_ignores_invalid_or_unmaterialized_updates(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    invalid = [
        {"compaction_update": None},
        {"compaction_update": {"content": None, "prompt_ref": "p", "source_message_ids": []}},
        {"compaction_update": {"content": "x", "prompt_ref": "", "source_message_ids": []}},
        {"compaction_update": {"content": "x", "prompt_ref": "p", "source_message_ids": [1]}},
    ]
    _apply_compaction_updates(events_path=events_path, result_nodes=invalid)
    assert not events_path.exists()

    monkeypatch.setattr("toas.runtime.session_step_edges.write_message_events", lambda *_args, **_kwargs: [])
    _apply_compaction_updates(
        events_path=events_path,
        result_nodes=[{"compaction_update": {"content": "x", "prompt_ref": "p", "source_message_ids": []}}],
    )
    assert not events_path.exists()


@pytest.mark.parametrize(
    "content",
    [
        "# Handoff Summary\n\n## Current Objective\nComplete enough.",
        "# Handoff Summary\n\nPartial only.",
        "free-form summary",
        "",
        "  preserve surrounding whitespace  \n",
    ],
)
def test_compaction_side_effect_persists_advisory_content_verbatim(tmp_path, content):
    events_path = tmp_path / "events.jsonl"

    _apply_compaction_updates(
        events_path=events_path,
        result_nodes=[
            {
                "compaction_update": {
                    "content": content,
                    "prompt_ref": "compaction/handoff_v1",
                    "source_message_ids": [],
                }
            }
        ],
    )

    events = read_log(str(events_path))
    assert events[0]["role"] == "assistant"
    assert events[0]["content"] == content
    assert events[1]["kind"] == "compaction_projection"


def test_apply_result_side_effects_ignores_invalid_intent_updates(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    session_path = tmp_path / "session.md"
    writes = {"intent": 0}

    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_intent_record",
        lambda *_args, **_kwargs: writes.__setitem__("intent", writes["intent"] + 1),
    )

    result_nodes = [
        {"role": "result", "content": "x", "intent_update": "bad"},
        {"role": "result", "content": "x", "intent_update": {"intent_id": "", "title": "t", "status": "active"}},
        {"role": "result", "content": "x", "intent_update": {"intent_id": "i1", "title": "", "status": "active"}},
        {"role": "result", "content": "x", "intent_update": {"intent_id": "i1", "title": "t", "status": ""}},
        {
            "role": "result",
            "content": "x",
            "intent_update": {"intent_id": "i2", "title": "ok", "status": "active", "tags": "not-a-list"},
        },
    ]

    apply_result_side_effects(
        events_path=events_path,
        result_nodes=result_nodes,
        operator_config=OperatorConfig(),
        session_path=session_path,
        session_newline="\n",
        runtime_secrets={},
        serialize_operator_config_toml=lambda _cfg: "",
        write_text_with_newline_style=lambda **_kwargs: None,
        apply_newline_style=lambda text, _nl: text,
    )

    assert writes["intent"] == 1


def test_stitch_frontier_records_ignores_invalid_replay_execution_shapes(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    calls = {"tool_request": 0, "tool_result": 0}
    monkeypatch.setattr("toas.runtime.session_step_edges.extract_plan", lambda *_a, **_k: None)
    monkeypatch.setattr("toas.runtime.session_step_edges.extract_user_shell_plan", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_command_request_record",
        lambda *_args, **_kwargs: {"payload": {"id": "r1"}},
    )
    monkeypatch.setattr("toas.runtime.session_step_edges.write_command_result_record", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_tool_request_record",
        lambda *_a, **_k: calls.__setitem__("tool_request", calls["tool_request"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_tool_result_record",
        lambda *_a, **_k: calls.__setitem__("tool_result", calls["tool_result"] + 1),
    )
    result_nodes = [
        {"role": "result", "content": "x", "extract_execution": {}, "replay_execution": "bad"},
        {"role": "result", "content": "x", "replay_execution": {"target_message_index": "bad", "request_plan": []}},
        {"role": "result", "content": "x", "replay_execution": {"target_message_index": 1, "request_plan": "bad"}},
        {"role": "result", "content": "x", "replay_execution": {"target_message_index": 0, "request_plan": []}},
        {"role": "result", "content": "x", "replay_execution": {"target_message_index": 2, "request_plan": []}},
    ]
    stitch_frontier_records(
        events_path=events_path,
        materialized=[{"id": "n1", "role": "user", "content": "/pwd"}],
        operator_config=OperatorConfig(),
        result_nodes=result_nodes,
        head_id="n1",
        lineage=[{"id": "n_target"}],
        extract_operator_command_tail=lambda _content: ("pwd", []),
    )
    assert calls == {"tool_request": 0, "tool_result": 0}


def test_apply_result_side_effects_ignores_invalid_updates_and_secret_unset(monkeypatch, tmp_path):
    events_path = tmp_path / "events.jsonl"
    session_path = tmp_path / "session.md"
    runtime_secrets = {"llm_api_key": "k1"}
    writes = {"queue": 0, "context": 0, "workspace": 0, "shell_scope": 0, "config_save": 0, "session": 0}
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_execution_queue_record",
        lambda *_a, **_k: writes.__setitem__("queue", writes["queue"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_command_context_record",
        lambda *_a, **_k: writes.__setitem__("context", writes["context"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_workspace_scope_record",
        lambda *_a, **_k: writes.__setitem__("workspace", writes["workspace"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_shell_scope_grant_record",
        lambda *_a, **_k: writes.__setitem__("shell_scope", writes["shell_scope"] + 1),
    )
    monkeypatch.setattr(
        "toas.runtime.session_step_edges.write_text_with_newline_style",
        lambda **_kwargs: writes.__setitem__("session", writes["session"] + 1),
        raising=False,
    )
    result_nodes = [
        {"role": "result", "content": "x", "queue_update": {"id": "", "status": "blocked"}},
        {"role": "result", "content": "x", "queue_update": {"id": "q1", "status": ""}},
        {"role": "result", "content": "x", "context_update": {"cwd": ""}},
        {"role": "result", "content": "x", "workspace_update": {"mode": "bad", "roots": []}},
        {"role": "result", "content": "x", "workspace_update": {"mode": "strict", "roots": [1, ""]}},
        {"role": "result", "content": "x", "secret_update": {"key": "other", "action": "set", "value": "x"}},
        {"role": "result", "content": "x", "secret_update": {"key": "llm_api_key", "action": "set", "value": 7}},
        {"role": "result", "content": "x", "secret_update": {"key": "llm_api_key", "action": "unset"}},
        {"role": "result", "content": "x", "shell_scope_update": {"scope": 1, "action": "add", "grant": "echo"}},
        {"role": "result", "content": "x", "shell_scope_update": {"scope": "session", "action": "add", "grant": ""}},
        {"role": "result", "content": "x", "shell_scope_update": {"scope": "session", "action": "weird", "grant": "echo"}},
        {"role": "result", "content": "x", "shell_scope_update": {"scope": "session", "action": "add", "grant": "echo"}},
        {"role": "result", "content": "x", "shell_scope_update": {"scope": "session", "action": "reset"}},
        {"role": "result", "content": "x", "config_save": {"path": ""}},
        {"role": "result", "content": "x", "session_update": {"transcript": 1}},
        {"role": "result", "content": "x", "lens_update": {"action": "noop"}},
    ]
    apply_result_side_effects(
        events_path=events_path,
        result_nodes=result_nodes,
        operator_config=OperatorConfig(),
        session_path=session_path,
        session_newline="\n",
        runtime_secrets=runtime_secrets,
        serialize_operator_config_toml=lambda _cfg: writes.__setitem__("config_save", writes["config_save"] + 1) or "",
        write_text_with_newline_style=lambda **_kwargs: writes.__setitem__("session", writes["session"] + 1),
        apply_newline_style=lambda text, _nl: text,
    )
    assert "llm_api_key" not in runtime_secrets
    assert writes["queue"] == 0
    assert writes["context"] == 0
    assert writes["workspace"] == 0
    assert writes["shell_scope"] == 2
    assert writes["session"] == 0


# --- extract_operator_command_tail ---

def test_extract_operator_command_tail_parses_slash_command():
    result = extract_operator_command_tail("some text\n/prompt list")
    assert result == ("prompt", ["list"])


def test_extract_operator_command_tail_returns_none_for_no_command():
    assert extract_operator_command_tail("plain text") is None


def test_extract_operator_command_tail_returns_none_for_empty():
    assert extract_operator_command_tail("") is None


def test_extract_operator_command_tail_returns_none_for_bad_quoting():
    assert extract_operator_command_tail('/cmd "unclosed') is None


def test_extract_operator_command_tail_no_args():
    result = extract_operator_command_tail("/show")
    assert result == ("show", [])


def test_extract_operator_command_tail_returns_none_for_bare_slash():
    assert extract_operator_command_tail("/") is None


# --- redact_secret_lines ---

def test_redact_secret_lines_redacts_matching_line():
    text = "/config secret set llm_api_key sk-abc123"
    assert redact_secret_lines(text) == "/config secret set llm_api_key [REDACTED]"


def test_redact_secret_lines_leaves_unrelated_lines():
    text = "line1\nline2"
    assert redact_secret_lines(text) == text


def test_redact_secret_lines_handles_multiline():
    text = "before\n/config secret set llm_api_key mykey\nafter"
    out = redact_secret_lines(text)
    assert "mykey" not in out
    assert "before" in out
    assert "after" in out
