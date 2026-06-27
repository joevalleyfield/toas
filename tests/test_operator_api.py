
import toas.operator_api as operator_api_mod
import pytest
from toas.operator_api import (
    StepOutcome,
    ancestry_lines,
    bind_surface,
    diff_lines,
    heads_lines,
    history_lines,
    intents_lines,
    llm_input_messages,
    prompt_list_lines,
    prompt_text,
    rebuild_session,
    select_surface,
    session_path_text,
    step_once,
    surface_lines,
    transcript_text,
)


def _write_events(path, lines):
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def _write_duplicate_id_history(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        path,
        [
            '{"id":"n1","parent":null,"role":"user","content":"first","metadata":{}}',
            '{"id":"n2","parent":"n1","role":"assistant","content":"child","metadata":{}}',
            '{"id":"n1","parent":"n2","role":"user","content":"duplicate","metadata":{}}',
        ],
    )


def test_step_once_calls_cli_session_runner(monkeypatch):
    called = {"n": 0}

    def fake_run_step(*, generate_override=None):
        assert generate_override is None
        called["n"] += 1

    out = step_once(run_step_fn=fake_run_step)

    assert called["n"] == 1
    assert out == StepOutcome(completed=True)


def test_step_once_threads_semantic_callbacks_to_explicit_step_dep():
    seen = {}

    def fake_run_step(**kwargs):
        seen.update(kwargs)

    answer_cb = lambda _text: None
    reasoning_cb = lambda _text: None
    progress_cb = lambda _obj: None
    projection_cb = lambda _text: None

    step_once(
        stdin_mode=True,
        control="/session show",
        session_path=".toas/session.md",
        on_llm_answer_delta=answer_cb,
        on_llm_reasoning_delta=reasoning_cb,
        on_llm_prompt_progress=progress_cb,
        on_projection_delta=projection_cb,
        run_step_fn=fake_run_step,
    )

    assert seen["stdin_mode"] is True
    assert seen["control"] == "/session show"
    assert seen["session_path"] == ".toas/session.md"
    assert seen["on_llm_answer_delta"] is answer_cb
    assert seen["on_llm_reasoning_delta"] is reasoning_cb
    assert seen["on_llm_prompt_progress"] is progress_cb
    assert seen["on_projection_delta"] is projection_cb


def test_step_once_threads_explicit_stream_policy_to_step_dep():
    seen = {}

    def fake_run_step(**kwargs):
        seen.update(kwargs)

    step_once(
        stream_stdout_enabled=False,
        stream_thinking_enabled=True,
        stream_prompt_progress_enabled=False,
        llm_stream_mode="enabled",
        debug_prompt_progress_enabled=True,
        debug_prompt_progress_file=".toas/progress.log",
        run_step_fn=fake_run_step,
    )

    assert seen["stream_stdout_enabled"] is False
    assert seen["stream_thinking_enabled"] is True
    assert seen["stream_prompt_progress_enabled"] is False
    assert seen["llm_stream_mode"] == "enabled"
    assert seen["debug_prompt_progress_enabled"] is True
    assert seen["debug_prompt_progress_file"] == ".toas/progress.log"


def test_heads_lines_formats_selected_head(tmp_path):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}',
            '{"id":"n1","parent":"n0","role":"assistant","content":"hi","metadata":{}}',
            '{"id":"n2","parent":"n1","role":"assistant","content":"selected","metadata":{},"head":{"selected":true}}',
            '{"id":"h0","type":"head","name":"main","parent":"n2","selected":true}',
        ],
    )

    out = heads_lines(events_path=events_path)

    assert any("n2 assistant: selected" in line for line in out.lines)


def test_heads_lines_computes_stats_without_per_head_lineage(tmp_path, monkeypatch):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"root","provenance":{"source":"user_authored"}}',
            '{"id":"n1","parent":"n0","role":"assistant","content":"main","provenance":{"source":"llm_generated"}}',
            '{"id":"n2","parent":"n1","role":"assistant","content":"same role","provenance":{"source":"llm_generated"}}',
            '{"id":"n3","parent":"n1","role":"user","content":"branch","provenance":{"source":"user_authored"}}',
        ],
    )

    def fail_message_lineage(*_args, **_kwargs):
        raise AssertionError("heads_lines should not rebuild each head lineage")

    monkeypatch.setattr("toas.operator_api.message_lineage", fail_message_lineage)

    out = heads_lines(events_path=events_path)

    assert out.lines == [
        "  n2 assistant: same role  [d=3 t=1 G:2 U:1]",
        "  n3 user: branch  [d=3 t=2 G:1 U:2]",
    ]


def test_lineage_stats_counts_turns_and_unknown_provenance():
    assert operator_api_mod._lineage_stats(
        [
            {"role": "user", "content": "root", "provenance": {"source": "user_authored"}},
            {"role": "assistant", "content": "reply"},
            {"role": "assistant", "content": "followup", "provenance": {"source": "llm_generated"}},
        ]
    ) == {
        "depth": 3,
        "turns": 1,
        "provenance": {"user_authored": 1, "?": 1, "llm_generated": 1},
    }


def test_lineage_stats_empty_lineage_returns_zeroes():
    assert operator_api_mod._lineage_stats([]) == {"depth": 0, "turns": 0, "provenance": {}}


def test_history_lines_includes_selected_bind_and_recent(tmp_path):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}',
            '{"id":"n1","parent":"n0","role":"assistant","content":"hi","metadata":{}}',
            '{"id":"n2","parent":"n1","role":"assistant","content":"selected","metadata":{},"head":{"selected":true}}',
            '{"id":"h0","type":"head","name":"main","parent":"n2","selected":true}',
            '{"id":"b0","type":"bind","name":"default","parent":"n2","selected":true}',
        ],
    )

    out = history_lines(events_path=events_path, limit=3)

    assert out.lines[0].startswith("selected_head=")
    assert out.lines[1].startswith("bind_index=")
    assert "heads:" in out.lines
    assert "recent:" in out.lines


def test_rebuild_session_writes_transcript_and_returns_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}',
            '{"id":"n1","parent":"n0","role":"assistant","content":"hi","metadata":{}}',
            '{"id":"n2","parent":"n1","role":"assistant","content":"selected","metadata":{}}',
            '{"id":"h0","type":"head","name":"main","parent":"n2","selected":true}',
            '{"id":"b0","type":"bind","name":"default","parent":"n2","selected":true}',
        ],
    )

    out = rebuild_session(events_path=events_path)

    assert out.target_label == "n2"
    assert out.session_path.exists()
    contents = out.session_path.read_text(encoding="utf-8")
    assert "## TOAS:USER" in contents


def test_transcript_text_projects_selected_head(tmp_path):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}',
            '{"id":"n1","parent":"n0","role":"assistant","content":"hi","metadata":{}}',
            '{"id":"h0","type":"head","name":"main","parent":"n1","selected":true}',
        ],
    )
    out = transcript_text(events_path=events_path)
    assert "## TOAS:USER" in out.text
    assert "hello" in out.text


def test_llm_input_messages_projects_selected_head(tmp_path):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}',
            '{"id":"n1","parent":"n0","role":"assistant","content":"hi","metadata":{}}',
            '{"id":"h0","type":"head","name":"main","parent":"n1","selected":true}',
        ],
    )
    out = llm_input_messages(events_path=events_path)
    assert out.messages[0]["role"] == "user"


def test_query_surfaces_use_segmented_logical_history(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    segments_dir = events_path.parent / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    (segments_dir / "000001-events.jsonl").write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"from cold","metadata":{}}\n'
        ),
        encoding="utf-8",
    )
    events_path.write_text(
        '{"id":"n2","parent":"n1","role":"user","content":"from hot","metadata":{}}\n',
        encoding="utf-8",
    )

    heads = heads_lines(events_path=events_path)
    history = history_lines(events_path=events_path, limit=5)
    transcript = transcript_text(events_path=events_path)
    llm_input = llm_input_messages(events_path=events_path)

    assert any("n2 user: from hot" in line for line in heads.lines)
    assert any("n1 assistant: from cold" in line for line in history.lines)
    assert "from cold" in transcript.text
    assert "from hot" in transcript.text
    assert [message["content"] for message in llm_input.messages] == ["hello", "from cold", "from hot"]


@pytest.mark.parametrize(
    ("surface_fn", "kwargs"),
    [
        (heads_lines, {}),
        (history_lines, {"limit": 5}),
        (transcript_text, {}),
        (llm_input_messages, {}),
    ],
)
def test_history_query_surfaces_refuse_fatal_history_corruption(tmp_path, surface_fn, kwargs):
    events_path = tmp_path / ".toas" / "events.jsonl"
    _write_duplicate_id_history(events_path)

    with pytest.raises(SystemExit, match="fatal durable-history corruption: duplicate_message_id"):
        surface_fn(events_path=events_path, **kwargs)


def test_graph_text_refuses_fatal_history_corruption(tmp_path):
    from toas.operator_api import graph_text

    events_path = tmp_path / ".toas" / "events.jsonl"
    _write_duplicate_id_history(events_path)

    with pytest.raises(SystemExit, match="fatal durable-history corruption: duplicate_message_id"):
        graph_text(events_path=events_path)


def test_rebuild_session_refuses_fatal_history_corruption_without_writing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    events_path = tmp_path / ".toas" / "events.jsonl"
    _write_duplicate_id_history(events_path)

    with pytest.raises(SystemExit, match="fatal durable-history corruption: duplicate_message_id"):
        rebuild_session(events_path=events_path)

    assert not (tmp_path / ".toas" / "session.md").exists()


def test_prompt_text_resolves_with_configured_constraints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "toas.toml").write_text(
        '[prompt]\nmode = "direct"\nconstraints = ["x"]\n',
        encoding="utf-8",
    )
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(events_path, ['{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}'])
    out = prompt_text(events_path=events_path, ref="dynamic/capabilities/overview_v1")
    assert "TOAS" in out.text


def test_prompt_list_lines_lists_assets():
    out = prompt_list_lines()
    assert any(line.startswith("session-start") for line in out.lines)


def test_intents_lines_reports_none_when_missing(tmp_path):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    out = intents_lines(events_path=events_path)
    assert out.lines == ["intents: (none)"]


def test_session_path_text_uses_resolved_config_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "toas.toml").write_text('[session]\ntranscript_path = ".toas/session-purpose.md"\n', encoding="utf-8")
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(events_path, ['{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}'])
    out = session_path_text(events_path=events_path)
    assert out.path == ".toas/session-purpose.md"


def test_session_path_text_prefers_selected_surface_binding_over_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        (
            '{"kind": "config_override", "payload": {"session": {"transcript_path": ".toas/from-config.md"}}}\n'
            '{"kind": "surface_bind", "payload": {"surface_id": "docs", "transcript_path": ".toas/from-surface.md"}}\n'
            '{"kind": "surface_select", "payload": {"surface_id": "docs"}}\n'
        ),
        encoding="utf-8",
    )
    out = session_path_text(events_path=events_path)
    assert out.path == ".toas/from-surface.md"


def test_surface_lines_bind_and_select_roundtrip(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    out_empty = surface_lines(events_path=events_path)
    assert out_empty.lines == ["surfaces: (none)"]

    bound = bind_surface(events_path=events_path, surface_id="docs", transcript_path=".toas/session-docs.md", reason="seed")
    assert bound.message == "bound surface docs -> .toas/session-docs.md"
    selected = select_surface(events_path=events_path, surface_id="docs")
    assert selected.message == "selected surface docs"

    out = surface_lines(events_path=events_path)
    assert out.lines == ["surfaces:", "* docs\t.toas/session-docs.md"]


def test_diff_lines_reports_common_ancestor(tmp_path):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"root","metadata":{}}',
            '{"id":"a","parent":"n0","role":"assistant","content":"left","metadata":{}}',
            '{"id":"b","parent":"n0","role":"assistant","content":"right","metadata":{}}',
        ],
    )
    out = diff_lines(events_path=events_path, head_a="a", head_b="b")
    assert any("common ancestor: n0" in line for line in out.lines)


def test_ancestry_lines_reports_tail(tmp_path):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"u0","metadata":{}}',
            '{"id":"n1","parent":"n0","role":"assistant","content":"a1","metadata":{}}',
            '{"id":"n2","parent":"n1","role":"user","content":"u2","metadata":{}}',
        ],
    )
    out = ancestry_lines(events_path=events_path, message_id="n2", depth=2)
    assert len(out.lines) == 2


def test_rebind_surface_writes_records(tmp_path, monkeypatch):
    from toas.operator_api import rebind_surface

    events_path = tmp_path / "events.jsonl"
    events_path.write_text("", encoding="utf-8")

    outcome = rebind_surface(
        events_path=events_path,
        surface_id="s1",
        from_head_id="h1",
        to_head_id="h2",
        reason="test",
    )

    assert "rebound surface s1 from h1 to h2" in outcome.message
    text = events_path.read_text(encoding="utf-8")
    assert '"kind": "surface_rebind"' in text
    assert '"kind": "surface_guardrail"' in text


def test_index_rebuild_message(tmp_path, monkeypatch):
    from toas.operator_api import index_rebuild_message

    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        '{"id": "n1", "parent": null, "role": "user", "content": "hello"}\n',
        encoding="utf-8",
    )

    outcome = index_rebuild_message(events_path=events_path)

    assert "1 message event(s) indexed" in outcome.message
    assert (tmp_path / "events.idx").exists()


def test_prov_summary_includes_unknown(tmp_path, monkeypatch):
    from toas.operator_api import _prov_summary

    assert _prov_summary({"?": 3}) == "?:3"
    assert _prov_summary({"llm_generated": 1, "?": 2}) == "G:1 ?:2"


def test_graph_text_handles_consequence_projection(tmp_path):
    from toas.operator_api import graph_text

    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        '{"id": "n1", "parent": null, "role": "user", "content": "hello"}\n',
        encoding="utf-8",
    )

    out = graph_text(events_path=events_path, projection="consequence")

    assert "n1" in out.text


def test_graph_text_refuses_oversized_full_render(tmp_path):
    from toas.operator_api import _GRAPH_FULL_RENDER_NODE_LIMIT, graph_text

    events_path = tmp_path / "events.jsonl"
    _write_events(
        events_path,
        [
            (
                '{"id":"n%d","parent":%s,"role":"user","content":"x","metadata":{}}'
                % (index, '"n%d"' % (index - 1) if index else "null")
            )
            for index in range(_GRAPH_FULL_RENDER_NODE_LIMIT + 1)
        ],
    )

    out = graph_text(events_path=events_path)

    assert "graph render refused" in out.text
    assert str(_GRAPH_FULL_RENDER_NODE_LIMIT + 1) in out.text
