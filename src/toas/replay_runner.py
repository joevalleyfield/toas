from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ReplayStep:
    append: str
    run_step: bool
    source: str


def load_replay_steps(script_path: Path) -> list[ReplayStep]:
    try:
        raw = script_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing replay script: {script_path}") from exc

    try:
        parsed = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"invalid replay script: {script_path}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"invalid replay script: {script_path}")

    steps = parsed.get("steps")
    if not isinstance(steps, list) or not steps:
        raise RuntimeError("invalid replay script: steps must be a non-empty list")

    out: list[ReplayStep] = []
    for i, raw_step in enumerate(steps, start=1):
        if isinstance(raw_step, str):
            text = raw_step.strip()
            if not text:
                raise RuntimeError(f"invalid replay script step {i}: empty string step")
            out.append(ReplayStep(append=text, run_step=True, source="append"))
            continue
        if not isinstance(raw_step, dict):
            raise RuntimeError(f"invalid replay script step {i}: expected mapping")
        append = raw_step.get("append")
        if not isinstance(append, str) or not append.strip():
            raise RuntimeError(f"invalid replay script step {i}: append must be a non-empty string")
        run_step = raw_step.get("step", True)
        if not isinstance(run_step, bool):
            raise RuntimeError(f"invalid replay script step {i}: step must be a boolean")
        source = raw_step.get("source", "append")
        if not isinstance(source, str) or not source.strip():
            source = "append"
        out.append(ReplayStep(append=append, run_step=run_step, source=source.strip()))
    return out


def append_text_block(*, session_path: Path, text: str) -> int:
    existing = session_path.read_text(encoding="utf-8") if session_path.exists() else ""
    normalized = text if text.endswith("\n") else f"{text}\n"
    if existing and not existing.endswith("\n"):
        merged = f"{existing}\n{normalized}"
    else:
        merged = f"{existing}{normalized}"
    session_path.write_text(merged, encoding="utf-8")
    return len(normalized)


def render_prompt_append(prompt_ref: str, *, load_prompt_ref) -> str:
    content = load_prompt_ref(prompt_ref)
    return f"## TOAS:SYSTEM\n\n{content}\n"


def render_procedure_append(procedure_name: str) -> str:
    payload = [
        "- operation: procedure",
        "  arguments:",
        f"    name: {procedure_name}",
    ]
    return "## TOAS:USER\n\n```yaml\n" + "\n".join(payload) + "\n```\n"


def write_replay_artifact(
    *,
    artifact_path: Path,
    script_path: Path,
    dry_run: bool,
    steps: list[dict[str, Any]],
    events_tail: list[dict[str, Any]],
    session_tail: str,
) -> None:
    payload = {
        "script": str(script_path),
        "dry_run": dry_run,
        "steps": steps,
        "events_tail": events_tail,
        "session_tail": session_tail,
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
