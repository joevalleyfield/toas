from toas.operator_api import StepOutcome, step_once
from toas.operator_api import heads_lines, history_lines, rebuild_session


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
