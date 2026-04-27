from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import re
from typing import Any

import yaml


@dataclass(frozen=True)
class ProcedureAsset:
    name: str
    description: str
    plan: list[dict]


def list_procedures() -> list[str]:
    base = resources.files("toas").joinpath("procedures")
    names: list[str] = []
    for item in base.iterdir():
        if item.is_file() and item.name.endswith(".yaml"):
            names.append(item.name.removesuffix(".yaml"))
    return sorted(names)


def _interpolate_procedure_yaml(raw_text: str, *, name: str, params: dict[str, Any]) -> str:
    try:
        prelim = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError:
        prelim = {}

    defaults = prelim.get("defaults", {}) if isinstance(prelim, dict) else {}
    if not isinstance(defaults, dict):
        defaults = {}
    merged = {**defaults, **params}

    interpolated = raw_text
    for key, value in merged.items():
        interpolated = interpolated.replace(f"{{{{ {key} }}}}", str(value))
        interpolated = interpolated.replace(f"{{{{{key}}}}}", str(value))

    missing = re.findall(r"\{\{\s*(.*?)\s*\}\}", interpolated)
    if missing:
        unique_missing = sorted(set(missing))
        names = ", ".join(unique_missing)
        raise RuntimeError(f"procedure {name} missing required parameters: {names}")
    return interpolated


def load_procedure(name: str, params: dict[str, Any] | None = None) -> ProcedureAsset:
    normalized = name.strip()
    actual_params = params or {}
    if not normalized or ".." in normalized.split("/"):
        raise RuntimeError(f"invalid procedure name: {name}")
    path = resources.files("toas").joinpath("procedures").joinpath(f"{normalized}.yaml")
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing procedure: {normalized}") from exc
    raw = _interpolate_procedure_yaml(raw_text, name=normalized, params=actual_params)

    try:
        parsed = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"invalid procedure asset: {normalized}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"invalid procedure asset: {normalized}")

    description = parsed.get("description", "")
    steps = parsed.get("steps", [])
    if not isinstance(description, str) or not description.strip():
        raise RuntimeError(f"invalid procedure asset: {normalized}")
    if not isinstance(steps, list) or not steps:
        raise RuntimeError(f"invalid procedure asset: {normalized}")

    normalized_steps: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            raise RuntimeError(f"invalid procedure asset: {normalized}")
        op = step.get("operation")
        if not isinstance(op, str) or not op.strip():
            raise RuntimeError(f"invalid procedure asset: {normalized}")
        if op.strip() == "procedure":
            raise RuntimeError(f"invalid procedure asset: {normalized}")
        params = step.get("params", {})
        if not isinstance(params, dict):
            raise RuntimeError(f"invalid procedure asset: {normalized}")
        normalized_steps.append({"tool_name": op.strip(), "args": dict(params)})

    return ProcedureAsset(
        name=normalized,
        description=description.strip(),
        plan=normalized_steps,
    )
