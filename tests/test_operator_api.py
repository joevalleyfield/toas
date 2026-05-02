from toas.operator_api import StepOutcome, step_once


def test_step_once_calls_cli_session_runner(monkeypatch):
    called = {"n": 0}

    def fake_run_step_local():
        called["n"] += 1

    monkeypatch.setattr("toas.cli_session_commands.run_step_local", fake_run_step_local)

    out = step_once()

    assert called["n"] == 1
    assert out == StepOutcome(completed=True)
