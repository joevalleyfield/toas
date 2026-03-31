from pathlib import Path

import pytest

from toas import cli


def test_run_step_bootstraps_missing_files_and_prints_no_history(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    calls = {}

    def fake_step(transcript, log, generate=None, execute=None):
        calls["transcript"] = transcript
        calls["log"] = log
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path("session.md").read_text(encoding="utf-8") == ""
    assert Path("events.jsonl").read_text(encoding="utf-8") == ""
    assert calls == {"transcript": "", "log": []}
    assert capsys.readouterr().out == ""


def test_run_step_appends_all_new_nodes_but_prints_only_consequences(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")

    def fake_step(transcript, log, generate=None, execute=None):
        assert transcript == "## USER\nhello\n"
        assert log == []
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
        '{"role": "user", "content": "hello"}\n'
        '{"role": "assistant", "content": "hi"}\n'
    )
    assert capsys.readouterr().out == "## ASSISTANT\nhi\n\n"


def test_run_jump_is_invokable(capsys):
    cli.run_jump(7)
    assert capsys.readouterr().out == "jump to 7 not implemented\n"


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


def test_main_rejects_unknown_command(monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["toas", "bogus"])

    with pytest.raises(SystemExit, match="unknown command: bogus"):
        cli.main()
