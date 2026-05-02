from pathlib import Path

import pytest

from toas.acceptance_harness import (
    AcceptanceBackendConfig,
    AcceptanceWorkspaceConfig,
    load_backend_config,
    load_workspace_config,
    load_replay_fixture,
    materialize_workspace,
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


def test_load_workspace_config_defaults(monkeypatch):
    monkeypatch.delenv("TOAS_ACCEPTANCE_WORKSPACE_MODE", raising=False)
    monkeypatch.delenv("TOAS_ACCEPTANCE_SOURCE_REPO", raising=False)
    monkeypatch.delenv("TOAS_ACCEPTANCE_SOURCE_REF", raising=False)
    cfg = load_workspace_config()
    assert cfg == AcceptanceWorkspaceConfig(mode="scratch", source_repo=None, source_ref=None)


def test_load_workspace_config_requires_source_fields(monkeypatch):
    monkeypatch.setenv("TOAS_ACCEPTANCE_WORKSPACE_MODE", "git_snapshot")
    monkeypatch.delenv("TOAS_ACCEPTANCE_SOURCE_REPO", raising=False)
    monkeypatch.delenv("TOAS_ACCEPTANCE_SOURCE_REF", raising=False)
    with pytest.raises(RuntimeError, match="TOAS_ACCEPTANCE_SOURCE_REPO is required"):
        load_workspace_config()
    monkeypatch.setenv("TOAS_ACCEPTANCE_SOURCE_REPO", "/tmp/repo")
    with pytest.raises(RuntimeError, match="TOAS_ACCEPTANCE_SOURCE_REF is required"):
        load_workspace_config()


def test_materialize_workspace_scratch(tmp_path: Path):
    out = materialize_workspace(
        target_dir=tmp_path / "repo",
        cfg=AcceptanceWorkspaceConfig(mode="scratch", source_repo=None, source_ref=None),
    )
    assert out.exists()
    assert out.is_dir()


def test_materialize_workspace_git_snapshot(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("hello\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init"], cwd=source, check=True, capture_output=True)
    subprocess.run(["git", "add", "README.md"], cwd=source, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "init"],
        cwd=source,
        check=True,
        capture_output=True,
    )
    sha = (
        subprocess.run(["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True)
        .stdout.strip()
    )
    target = tmp_path / "target"
    out = materialize_workspace(
        target_dir=target,
        cfg=AcceptanceWorkspaceConfig(mode="git_snapshot", source_repo=source, source_ref=sha),
    )
    assert out == target
    assert (target / "README.md").read_text(encoding="utf-8") == "hello\n"
