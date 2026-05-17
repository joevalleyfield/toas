from pathlib import Path

from toas.operator_api import StepOutcome, step_once
from toas.operator_api import heads_lines, history_lines, rebuild_session
from toas.operator_api import _ensure_session_path_compat, select_head
from toas.operator_api import transcript_text, llm_input_messages, prompt_text, prompt_list_lines
from toas.operator_api import intents_lines, session_path_text


def _write_events(path, lines):
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def test_step_once_calls_cli_session_runner(monkeypatch):
    called = {"n": 0}

    def fake_run_step_local(*, generate_override=None):
        assert generate_override is None
        called["n"] += 1

    monkeypatch.setattr("toas.cli_session_commands.run_step_local", fake_run_step_local)

    out = step_once()

    assert called["n"] == 1
    assert out == StepOutcome(completed=True)


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


def test_select_head_writes_head_record_and_message(tmp_path):
    events_path = tmp_path / ".toas/events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    out = select_head(events_path=events_path, head_id="n7")
    assert out.message == "selected head n7"
    assert events_path.read_text(encoding="utf-8") == '{"kind": "head", "payload": {"head_id": "n7"}}\n'


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
