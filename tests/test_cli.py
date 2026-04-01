from pathlib import Path

import pytest

from toas import cli


def test_run_step_bootstraps_missing_files_and_prints_no_history(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    calls = {}

    def fake_step(transcript, log, generate=None, execute=None, bind_index=None, bind_parent=None):
        calls["transcript"] = transcript
        calls["log"] = log
        calls["bind_index"] = bind_index
        calls["bind_parent"] = bind_parent
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path("session.md").read_text(encoding="utf-8") == ""
    assert Path("events.jsonl").read_text(encoding="utf-8") == ""
    assert calls == {"transcript": "", "log": [], "bind_index": None, "bind_parent": None}
    assert capsys.readouterr().out == ""


def test_run_step_appends_all_new_nodes_but_prints_only_consequences(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")

    def fake_step(transcript, log, generate=None, execute=None, bind_index=None, bind_parent=None):
        assert transcript == "## USER\nhello\n"
        assert log == []
        assert bind_index is None
        assert bind_parent is None
        return (
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            [
                {"role": "assistant", "content": "hi"},
            ],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## ASSISTANT\nhi\n\n"


def test_run_jump_is_invokable(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    cli.run_jump(7)

    assert Path("jump.txt").read_text(encoding="utf-8") == "7\n"
    assert capsys.readouterr().out == "bound transcript to node 7\n"


def test_main_defaults_to_step(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas"])
    monkeypatch.setattr(cli, "run_step", lambda: seen.append("step"))

    cli.main()

    assert seen == ["step"]


def test_main_dispatches_jump(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "jump", "12"])
    monkeypatch.setattr(cli, "run_jump", lambda index: seen.append(index))

    cli.main()

    assert seen == [12]


def test_run_step_honors_jump_binding(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")
    Path("events.jsonl").write_text(
        '{"role": "user", "content": "old"}\n',
        encoding="utf-8",
    )
    Path("jump.txt").write_text("1\n", encoding="utf-8")

    def fake_step(transcript, log, generate=None, execute=None, bind_index=None, bind_parent=None):
        assert transcript == "## USER\nhello\n"
        assert log == [{"role": "user", "content": "old"}]
        assert bind_index == 1
        assert bind_parent is None
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_run_step_derives_bind_parent_from_message_event_space(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")
    Path("events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"kind": "jump", "payload": {"bind_index": 1}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "old", "metadata": {}}\n'
        ),
        encoding="utf-8",
    )
    Path("jump.txt").write_text("1\n", encoding="utf-8")

    def fake_step(transcript, log, generate=None, execute=None, bind_index=None, bind_parent=None):
        assert log == [
            {"role": "user", "content": "root"},
            {"role": "assistant", "content": "old"},
        ]
        assert bind_index == 1
        assert bind_parent == "n0"
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_run_step_projects_graph_events_before_calling_step(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")
    Path("events.jsonl").write_text(
        (
            '{"id": "n1", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
            '{"kind": "jump", "payload": {"bind_index": 1}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(transcript, log, generate=None, execute=None, bind_index=None, bind_parent=None):
        assert transcript == "## USER\nhello\n"
        assert log == [{"role": "user", "content": "hello"}]
        assert bind_index is None
        assert bind_parent == "n1"
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_run_step_writes_new_nodes_as_message_events(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")

    def fake_step(transcript, log, generate=None, execute=None, bind_index=None, bind_parent=None):
        return (
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            [{"role": "assistant", "content": "hi"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## ASSISTANT\nhi\n\n"


def test_run_step_preserves_explicit_parent_from_step_output(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## ASSISTANT\nalternate\n", encoding="utf-8")
    Path("events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(transcript, log, generate=None, execute=None, bind_index=None, bind_parent=None):
        return (
            [
                {"role": "assistant", "content": "alternate", "parent": "n0"},
            ],
            [],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
        '{"id": "n2", "parent": "n0", "role": "assistant", "content": "alternate", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == ""


def test_main_rejects_unknown_command(monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["toas", "bogus"])

    with pytest.raises(SystemExit, match="unknown command: bogus"):
        cli.main()
