"""Packaged runtime assets and their shared resource-loading primitives."""

from .loader import PackagedAsset, list_packaged_assets, load_packaged_asset

__all__ = ["PackagedAsset", "list_packaged_assets", "load_packaged_asset"]
