"""Packaged runtime assets and their shared resource-loading primitives."""

from .loader import PackagedAsset, list_packaged_assets, load_packaged_asset
from .presentation_loader import (
    clear_presentation_template_cache,
    list_presentation_templates,
    load_presentation_template,
    render_template,
    reset_active_presentation_context,
    set_active_presentation_context,
)

__all__ = [
    "PackagedAsset",
    "list_packaged_assets",
    "load_packaged_asset",
    "load_presentation_template",
    "render_template",
    "list_presentation_templates",
    "clear_presentation_template_cache",
    "set_active_presentation_context",
    "reset_active_presentation_context",
]
