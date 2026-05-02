from pathlib import Path

import pytest

from toas.acceptance_harness import (
    AcceptanceBackendConfig,
    load_backend_config,
    load_replay_fixture,
    should_use_live,
    write_live_capture,
)


def test_should_use_live_mode_matrix():
    labels = {"a": 0, "b": 1}
    assert should_use_live(cfg=AcceptanceBackendConfig("live_only", None, None, False), step_index=0, step_label="a", step_labels=labels) is True
    assert should_use_live(cfg=AcceptanceBackendConfig("replay_only", None, None, False), step_index=1, step_label="b", step_labels=labels) is False
    assert should_use_live(cfg=AcceptanceBackendConfig("hybrid", 1, None, False), step_index=0, step_label="a", step_labels=labels) is False
    assert should_use_live(cfg=AcceptanceBackendConfig("hybrid", 1, None, False), step_index=1, step_label="b", step_labels=labels) is True


def test_should_use_live_by_label_and_unknown_label_errors():
    labels = {"implementation_pass": 0, "recovery_check": 1}
    cfg = AcceptanceBackendConfig("hybrid", None, "recovery_check", False)
    assert should_use_live(cfg=cfg, step_index=0, step_label="implementation_pass", step_labels=labels) is False
    assert should_use_live(cfg=cfg, step_index=1, step_label="recovery_check", step_labels=labels) is True
    bad_cfg = AcceptanceBackendConfig("hybrid", None, "missing", False)
    with pytest.raises(RuntimeError, match="unknown TOAS_ACCEPTANCE_LIVE_FROM_LABEL"):
        should_use_live(cfg=bad_cfg, step_index=0, step_label="implementation_pass", step_labels=labels)


def test_replay_fixture_io(tmp_path: Path):
    payload = {"ok": True}
    write_live_capture(tmp_path, "step1", payload)
    assert load_replay_fixture(tmp_path, "step1") == payload
    with pytest.raises(RuntimeError, match="missing replay fixture"):
        load_replay_fixture(tmp_path, "nope")


def test_load_backend_config_from_env(monkeypatch):
    monkeypatch.setenv("TOAS_ACCEPTANCE_BACKEND_MODE", "hybrid")
    monkeypatch.setenv("TOAS_ACCEPTANCE_LIVE_FROM_STEP", "3")
    monkeypatch.setenv("TOAS_ACCEPTANCE_LIVE_FROM_LABEL", "recover")
    monkeypatch.setenv("TOAS_ACCEPTANCE_WRITE_LIVE_CAPTURES", "true")
    cfg = load_backend_config()
    assert cfg.mode == "hybrid"
    assert cfg.live_from_step == 3
    assert cfg.live_from_label == "recover"
    assert cfg.write_live_captures is True


def test_load_backend_config_rejects_invalid_mode(monkeypatch):
    monkeypatch.setenv("TOAS_ACCEPTANCE_BACKEND_MODE", "bad")
    with pytest.raises(RuntimeError, match="invalid TOAS_ACCEPTANCE_BACKEND_MODE"):
        load_backend_config()
