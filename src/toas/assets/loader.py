from __future__ import annotations

from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class PackagedAsset:
    kind: str
    ref: str
    suffix: str
    content: str


def normalize_asset_ref(ref: str) -> str:
    normalized = ref.strip().strip("/")
    if not normalized or ".." in normalized.split("/"):
        raise RuntimeError(f"invalid asset ref: {ref}")
    return normalized


def load_packaged_asset(kind: str, ref: str, *, suffix: str) -> PackagedAsset:
    normalized_kind = normalize_asset_ref(kind)
    normalized_ref = normalize_asset_ref(ref)
    resource = resources.files("toas").joinpath("assets", normalized_kind, f"{normalized_ref}{suffix}")
    try:
        content = resource.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing {normalized_kind} asset: {normalized_ref}") from exc
    return PackagedAsset(kind=normalized_kind, ref=normalized_ref, suffix=suffix, content=content)


def list_packaged_assets(kind: str, *, suffix: str) -> list[str]:
    normalized_kind = normalize_asset_ref(kind)
    root = resources.files("toas").joinpath("assets", normalized_kind)
    refs: list[str] = []
    for path in root.rglob(f"*{suffix}"):
        if path.is_file() and path.name.endswith(suffix):
            refs.append(str(path.relative_to(root)).removesuffix(suffix))
    return sorted(refs)
