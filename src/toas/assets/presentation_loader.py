"""Presentation template loading with workspace-level overrides and consolidated domain catalogs."""
from __future__ import annotations

import contextvars
import functools
from pathlib import Path
from typing import Any

import yaml

from .loader import normalize_asset_ref

_ACTIVE_PRESENTATION_CONTEXT: contextvars.ContextVar[tuple[tuple[str, ...], str | None]] = contextvars.ContextVar(
    "_ACTIVE_PRESENTATION_CONTEXT", default=((), None)
)


def set_active_presentation_context(
    *,
    workspace_roots: tuple[str, ...] = (),
    command_cwd: str | None = None,
) -> contextvars.Token:
    """Set the active presentation lookup context (workspace roots and command cwd)."""
    return _ACTIVE_PRESENTATION_CONTEXT.set((workspace_roots, command_cwd))


def reset_active_presentation_context(token: contextvars.Token) -> None:
    """Reset the presentation lookup context."""
    _ACTIVE_PRESENTATION_CONTEXT.reset(token)


@functools.lru_cache(maxsize=32)
def _load_packaged_family_catalog(family: str) -> dict[str, str]:
    from importlib import resources

    norm_family = normalize_asset_ref(family)
    resource = resources.files("toas").joinpath("assets", "presentation", f"{norm_family}.yaml")
    try:
        raw = resource.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v).rstrip("\r\n") for k, v in parsed.items()}
    except FileNotFoundError:
        pass
    return {}


def _lookup_dirs(workspace_roots: tuple[str, ...], command_cwd: str | None) -> list[Path]:
    lookup_dirs: list[Path] = [Path(root) for root in workspace_roots]
    lookup_dirs.append(Path(command_cwd) if command_cwd is not None else Path.cwd())
    return lookup_dirs


@functools.lru_cache(maxsize=128)
def _cached_load_presentation_catalog(
    family: str,
    workspace_roots: tuple[str, ...],
    command_cwd: str | None,
) -> dict[str, str]:
    norm_family = normalize_asset_ref(family)
    catalog = dict(_load_packaged_family_catalog(norm_family))
    lookup_dirs = _lookup_dirs(workspace_roots, command_cwd)

    # Load workspace overrides in reverse order so higher-priority roots overwrite lower ones
    for base_dir in reversed(lookup_dirs):
        # 1. Check <base_dir>/.toas/presentation.yaml
        unified_file = base_dir / ".toas" / "presentation.yaml"
        if unified_file.is_file():
            try:
                parsed = yaml.safe_load(unified_file.read_text(encoding="utf-8"))
                if isinstance(parsed, dict) and norm_family in parsed and isinstance(parsed[norm_family], dict):
                    catalog.update({str(k): str(v).rstrip("\r\n") for k, v in parsed[norm_family].items()})
            except Exception:
                pass

        # 2. Check <base_dir>/.toas/assets/presentation/<family>.yaml
        family_file = base_dir / ".toas" / "assets" / "presentation" / f"{norm_family}.yaml"
        if family_file.is_file():
            try:
                parsed = yaml.safe_load(family_file.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    catalog.update({str(k): str(v).rstrip("\r\n") for k, v in parsed.items()})
            except Exception:
                pass

    return catalog


def load_presentation_template(
    family: str,
    name: str,
    *,
    workspace_roots: tuple[str, ...] = (),
    command_cwd: str | None = None,
) -> str:
    """Load a presentation template (.txt or .yaml key) with workspace override support."""
    norm_family = normalize_asset_ref(family)
    norm_name = normalize_asset_ref(name)

    if not workspace_roots and command_cwd is None:
        ctx_roots, ctx_cwd = _ACTIVE_PRESENTATION_CONTEXT.get()
        workspace_roots = ctx_roots
        command_cwd = ctx_cwd

    # First check individual legacy file overrides: <root>/.toas/assets/presentation/<family>/<name>.txt
    lookup_dirs = _lookup_dirs(workspace_roots, command_cwd)
    relative_txt = Path(".toas") / "assets" / "presentation" / norm_family / f"{norm_name}.txt"
    for base_dir in lookup_dirs:
        candidate = base_dir / relative_txt
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").rstrip("\r\n")

    catalog = _cached_load_presentation_catalog(norm_family, workspace_roots, command_cwd)
    if norm_name in catalog:
        return catalog[norm_name]
    raise RuntimeError(f"missing presentation asset: {norm_family}/{norm_name}")


def render_template(
    family: str,
    name: str,
    *,
    workspace_roots: tuple[str, ...] = (),
    command_cwd: str | None = None,
    **kwargs: Any,
) -> str:
    """Load and format a presentation template with keyword arguments."""
    template = load_presentation_template(
        family,
        name,
        workspace_roots=workspace_roots,
        command_cwd=command_cwd,
    )
    if kwargs:
        return template.format(**kwargs)
    return template


def list_presentation_templates(
    family: str | None = None,
    *,
    workspace_roots: tuple[str, ...] = (),
    command_cwd: str | None = None,
) -> list[str]:
    """List all available presentation template refs, combining packaged assets and workspace overrides."""
    if not workspace_roots and command_cwd is None:
        ctx_roots, ctx_cwd = _ACTIVE_PRESENTATION_CONTEXT.get()
        workspace_roots = ctx_roots
        command_cwd = ctx_cwd

    families = [family] if family is not None else ["config", "models", "replay", "shell", "workspace"]
    refs: set[str] = set()

    for fam in families:
        norm_fam = normalize_asset_ref(fam)
        catalog = _cached_load_presentation_catalog(norm_fam, workspace_roots, command_cwd)
        for key in catalog:
            refs.add(f"{norm_fam}/{key}")

    # Also include any loose txt files in workspace overrides
    lookup_dirs = _lookup_dirs(workspace_roots, command_cwd)

    for base_dir in lookup_dirs:
        override_dir = base_dir / ".toas" / "assets" / "presentation"
        if override_dir.is_dir():
            for path in override_dir.rglob("*.txt"):
                if path.is_file():
                    ref = path.relative_to(override_dir).as_posix().removesuffix(".txt")
                    if family is None or ref.startswith(f"{normalize_asset_ref(family)}/"):
                        refs.add(ref)

    return sorted(refs)


def clear_presentation_template_cache() -> None:
    """Clear cached presentation templates and catalogs."""
    _load_packaged_family_catalog.cache_clear()
    _cached_load_presentation_catalog.cache_clear()
