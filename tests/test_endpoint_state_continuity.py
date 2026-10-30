from contextlib import redirect_stdout
from io import StringIO

import pytest

import toas.step as step_mod
from toas.cli_session_commands import run_step
from toas.config import OperatorConfig
from toas.graph import read_log
from toas.runtime.step_runtime import _branch_config_from_direct_declarations


@pytest.mark.parametrize("remove", [False, True])
def test_endpoint_declarations_replay_in_order_and_ignore_invalid_or_external_operations(remove):
    declarations = [
        "/config endpoint add local http://localhost:8080/v1",
        "/config endpoint set local.default_model discovered-model",
        "/config endpoint set missing.default_model ignored",
        "/config endpoint add",
        "/config endpoint capture external",
    ]
    if remove:
        declarations.append("/config endpoint remove local")
    config, applied = _branch_config_from_direct_declarations(
        step_mod=step_mod,
        working=[{"role": "user", "content": command} for command in declarations] + [{"role": "user", "content": "/config endpoint list"}],
        baseline_config=OperatorConfig(),
    )
    assert applied
    assert [endpoint.id for endpoint in config.llm.endpoints] == ([] if remove else ["local"])
    if not remove:
        assert config.llm.endpoints[0].default_model == "discovered-model"


def test_endpoint_survives_config_reconstitution_and_stays_branch_local(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = tmp_path / "session.md"
    transcript = ""

    def submit(command):
        nonlocal transcript
        transcript += f"\n## TOAS:USER\n\n{command}\n"
        session.write_text(transcript, encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            run_step(session_path=str(session))
        rendered = output.getvalue()
        transcript += rendered
        return rendered

    submit("/config set prompt.mode mimic")
    branch_point = transcript
    added = submit("/config endpoint add local http://localhost:8080/v1")
    assert "added endpoint local" in added
    assert "/models refresh local" in added
    assert "local: http://localhost:8080/v1" in submit("/config endpoint list")
    fetches = []

    def fetch(_settings):
        fetches.append(True)
        return {"data": [{"id": "discovered-model"}]}

    monkeypatch.setattr("toas.llm_harness.fetch_models", fetch)
    assert "model catalog refreshed" in submit("/models refresh local")
    assert "discovered-model" in submit("/models known local")
    assert "updated endpoint local.default_model" in submit("/config endpoint set local.default_model discovered-model")
    assert "model=discovered-model" in submit("/config endpoint list")
    assert "discovered-model" in submit("/models known local")
    assert fetches == [True]
    assert "selected model: discovered-model" in submit("/model select local discovered-model")
    assert "active model target: local-discovered-model" in submit("/model")
    assert "unknown endpoint" in submit("/config target add broken local.default_model discovered-model")
    assert "added model target chosen" in submit("/config target add chosen local discovered-model")
    assert "chosen: endpoint=local, model=discovered-model, status=ready" in submit("/model targets")
    assert "selected model target: chosen" in submit("/model select chosen")
    assert "active model target: chosen" in submit("/model")
    records = read_log(str(tmp_path / ".toas/events.jsonl"))
    assert any(event.get("kind") == "config_override" and event.get("related_to") for event in records)

    transcript = branch_point
    assert "no configured endpoints" in submit("/config endpoint list")


def test_endpoint_model_refresh_survives_frontier_restep(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = tmp_path / "session.md"
    transcript = ""

    def submit(command):
        nonlocal transcript
        transcript += f"\n## TOAS:USER\n\n{command}\n"
        session.write_text(transcript, encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            run_step(session_path=str(session))
        rendered = output.getvalue()
        transcript += rendered
        return rendered

    submit("/config endpoint add remote http://localhost:9000/v1")

    # 1. Initial attempt fails
    monkeypatch.setattr("toas.llm_harness.fetch_models", lambda _settings: {"error": "401 Unauthorized"})
    failed_output = submit("/models refresh remote")
    assert "model catalog refresh failed for remote" in failed_output

    # 2. Restep: trim the failed ## RESULT block from transcript and re-execute
    idx = transcript.rfind("## TOAS:USER\n\n## RESULT")
    assert idx != -1
    transcript = transcript[:idx].rstrip() + "\n"
    session.write_text(transcript, encoding="utf-8")

    monkeypatch.setattr("toas.llm_harness.fetch_models", lambda _settings: {"data": [{"id": "restep-model"}]})
    output = StringIO()
    with redirect_stdout(output):
        run_step(session_path=str(session))
    rendered = output.getvalue()
    transcript += rendered
    assert "model catalog refreshed for remote: added restep-model" in rendered

    # 3. Next turn: /models known remote must reflect restep catalog
    known = submit("/models known remote")
    assert "restep-model" in known
    assert "last refresh: (never)" not in known

    # 4. Unknown model gives informative error instead of "not uniquely identified"
    missing = submit("/model select remote nonexistent")
    assert "unknown model in remote: nonexistent" in missing

    # 5. Model select succeeds
    selected = submit("/model select remote restep-model")
    assert "selected model: restep-model" in selected

