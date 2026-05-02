from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AcceptanceBackendConfig:
    mode: str
    live_from_step: int | None
    live_from_label: str | None
    write_live_captures: bool


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
