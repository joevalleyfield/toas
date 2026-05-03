from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AcceptanceBackendConfig:
    mode: str
    live_from_step: int | None
    live_from_label: str | None
    write_live_captures: bool


@dataclass(frozen=True)
class AcceptanceWorkspaceConfig:
    mode: str
    source_repo: Path | None
    source_ref: str | None


def load_workspace_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_backend_config() -> AcceptanceBackendConfig:
    mode = os.getenv("TOAS_ACCEPTANCE_BACKEND_MODE", "hybrid").strip().lower()
    if mode not in {"replay_only", "live_only", "hybrid"}:
        raise RuntimeError(f"invalid TOAS_ACCEPTANCE_BACKEND_MODE: {mode}")
    live_from_step_raw = os.getenv("TOAS_ACCEPTANCE_LIVE_FROM_STEP", "").strip()
    live_from_step = int(live_from_step_raw) if live_from_step_raw else None
    live_from_label = os.getenv("TOAS_ACCEPTANCE_LIVE_FROM_LABEL", "").strip() or None
    write_live_captures = os.getenv("TOAS_ACCEPTANCE_WRITE_LIVE_CAPTURES", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return AcceptanceBackendConfig(
        mode=mode,
        live_from_step=live_from_step,
        live_from_label=live_from_label,
        write_live_captures=write_live_captures,
    )


def load_workspace_config() -> AcceptanceWorkspaceConfig:
    mode = os.getenv("TOAS_ACCEPTANCE_WORKSPACE_MODE", "scratch").strip().lower()
    if mode not in {"scratch", "git_snapshot"}:
        raise RuntimeError(f"invalid TOAS_ACCEPTANCE_WORKSPACE_MODE: {mode}")
    source_repo_raw = os.getenv("TOAS_ACCEPTANCE_SOURCE_REPO", "").strip()
    source_ref = os.getenv("TOAS_ACCEPTANCE_SOURCE_REF", "").strip() or None
    source_repo = Path(source_repo_raw).expanduser().resolve() if source_repo_raw else None
    if mode == "git_snapshot":
        if source_repo is None:
            raise RuntimeError("TOAS_ACCEPTANCE_SOURCE_REPO is required for git_snapshot mode")
        if source_ref is None:
            raise RuntimeError("TOAS_ACCEPTANCE_SOURCE_REF is required for git_snapshot mode")
    return AcceptanceWorkspaceConfig(mode=mode, source_repo=source_repo, source_ref=source_ref)


def resolve_workspace_config(
    *,
    default_mode: str,
    default_source_repo: Path | None,
    default_source_ref: str | None,
) -> AcceptanceWorkspaceConfig:
    mode = os.getenv("TOAS_ACCEPTANCE_WORKSPACE_MODE", default_mode).strip().lower()
    if mode not in {"scratch", "git_snapshot"}:
        raise RuntimeError(f"invalid TOAS_ACCEPTANCE_WORKSPACE_MODE: {mode}")
    source_repo_raw = os.getenv("TOAS_ACCEPTANCE_SOURCE_REPO", "").strip()
    source_ref_raw = os.getenv("TOAS_ACCEPTANCE_SOURCE_REF", "").strip()
    source_repo = (
        Path(source_repo_raw).expanduser().resolve()
        if source_repo_raw
        else (default_source_repo.resolve() if default_source_repo else None)
    )
    source_ref = source_ref_raw or default_source_ref
    if mode == "git_snapshot":
        if source_repo is None:
            raise RuntimeError("TOAS_ACCEPTANCE_SOURCE_REPO is required for git_snapshot mode")
        if source_ref is None:
            raise RuntimeError("TOAS_ACCEPTANCE_SOURCE_REF is required for git_snapshot mode")
    return AcceptanceWorkspaceConfig(mode=mode, source_repo=source_repo, source_ref=source_ref)


def should_use_live(
    *,
    cfg: AcceptanceBackendConfig,
    step_index: int,
    step_label: str,
    step_labels: dict[str, int],
) -> bool:
    if cfg.mode == "live_only":
        return True
    if cfg.mode == "replay_only":
        return False
    if cfg.live_from_label:
        if cfg.live_from_label not in step_labels:
            raise RuntimeError(f"unknown TOAS_ACCEPTANCE_LIVE_FROM_LABEL: {cfg.live_from_label}")
        return step_index >= step_labels[cfg.live_from_label]
    if cfg.live_from_step is not None:
        return step_index >= cfg.live_from_step
    return False


def load_replay_fixture(fixtures_dir: Path, step_label: str) -> dict[str, Any]:
    fixture_path = fixtures_dir / f"{step_label}.json"
    if not fixture_path.exists():
        raise RuntimeError(f"missing replay fixture for step: {step_label}")
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def write_live_capture(fixtures_dir: Path, step_label: str, payload: dict[str, Any]) -> None:
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    (fixtures_dir / f"{step_label}.json").write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def materialize_workspace(*, target_dir: Path, cfg: AcceptanceWorkspaceConfig) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    if cfg.mode == "scratch":
        return target_dir
    assert cfg.source_repo is not None
    assert cfg.source_ref is not None
    clone = subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--no-checkout",
            "--",
            str(cfg.source_repo),
            str(target_dir),
        ],
        capture_output=True,
        check=False,
    )
    if clone.returncode != 0:
        stderr = clone.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git clone failed: {stderr}")
    checkout = subprocess.run(
        ["git", "-C", str(target_dir), "checkout", "--quiet", cfg.source_ref],
        capture_output=True,
        check=False,
    )
    if checkout.returncode != 0:
        stderr = checkout.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git checkout failed: {stderr}")
    return target_dir
