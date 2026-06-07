from pathlib import Path

from toas.operator_api import StepOutcome, step_once
from toas.operator_api import heads_lines, history_lines, rebuild_session
from toas.operator_api import _ensure_session_path_compat
from toas.operator_api import transcript_text, llm_input_messages, prompt_text, prompt_list_lines
from toas.operator_api import intents_lines, session_path_text, surface_lines, bind_surface, select_surface
from toas.operator_api import diff_lines, ancestry_lines


def _write_events(path, lines):
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def test_step_once_calls_cli_session_runner(monkeypatch):
    called = {"n": 0}

    def fake_run_step_local(*, generate_override=None):
        assert generate_override is None
        called["n"] += 1

    out = step_once(run_step_local_fn=fake_run_step_local)

    assert called["n"] == 1
    assert out == StepOutcome(completed=True)


def test_step_once_threads_semantic_callbacks_to_explicit_step_dep():
    seen = {}

    def fake_run_step_local(**kwargs):
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
        run_step_local_fn=fake_run_step_local,
    )

    assert seen["stdin_mode"] is True
    assert seen["control"] == "/session show"
    assert seen["session_path"] == ".toas/session.md"
    assert seen["on_llm_answer_delta"] is answer_cb
    assert seen["on_llm_reasoning_delta"] is reasoning_cb
    assert seen["on_llm_prompt_progress"] is progress_cb
    assert seen["on_projection_delta"] is projection_cb


def test_step_once_threads_explicit_shell_stream_policy_to_step_dep():
    seen = {}

    def fake_run_step_local(**kwargs):
        seen.update(kwargs)

    step_once(stream_stdout_enabled=False, run_step_local_fn=fake_run_step_local)

    assert seen["stream_stdout_enabled"] is False


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


def test_rebuild_session_copies_legacy_session_when_config_path_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "toas.toml").write_text('[session]\ntranscript_path = ".toas/session.md"\n', encoding="utf-8")
    (tmp_path / "session.md").write_text("legacy\n", encoding="utf-8")
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(
        events_path,
        [
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}',
            '{"id":"h0","type":"head","name":"main","parent":"n0","selected":true}',
        ],
    )

    out = rebuild_session(events_path=events_path)

    assert out.session_path == Path(".toas/session.md")
    assert out.session_path.exists()


def test_ensure_session_path_compat_ignores_copy_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "session.md").write_text("legacy\n", encoding="utf-8")
    # Force compat-copy mkdir failure: ".toas" is a file, not directory.
    (tmp_path / ".toas").write_text("not-a-dir\n", encoding="utf-8")

    _ensure_session_path_compat(Path(".toas/session.md"))

    assert not (tmp_path / ".toas/session.md").exists()


def test_ensure_session_path_compat_noops_when_target_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / ".toas/session.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("existing\n", encoding="utf-8")
    (tmp_path / "session.md").write_text("legacy\n", encoding="utf-8")

    _ensure_session_path_compat(Path(".toas/session.md"))

    assert target.read_text(encoding="utf-8") == "existing\n"

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


def test_ensure_session_path_compat_no_legacy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / ".toas/session.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    # No legacy session.md exists
    _ensure_session_path_compat(target)

    assert not target.exists()


def test_ensure_session_path_compat_copies_legacy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / ".toas/session.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "session.md").write_text("legacy content\n", encoding="utf-8")

    _ensure_session_path_compat(target)

    assert target.exists()
    assert target.read_text(encoding="utf-8") == "legacy content\n"
