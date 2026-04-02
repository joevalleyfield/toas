from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import re

import yaml

from .capability_prompts import (
    render_capability_overview,
    render_capability_repo_work,
    render_capability_start_here,
)


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


@dataclass(frozen=True)
class PromptAsset:
    ref: str
    content: str
    metadata: dict


_DYNAMIC_PROMPTS = {
    "dynamic/capabilities/overview_v1": {
        "metadata": {
            "name": "Capability Overview",
            "description": "Advertise the current TOAS runtime capabilities and limits.",
            "category": "capability-advertisement",
        },
        "renderer": render_capability_overview,
    },
    "dynamic/capabilities/repo-work_v1": {
        "metadata": {
            "name": "Repo Work Capabilities",
            "description": "Advertise repo-reading, searching, shell, and history inspection capabilities.",
            "category": "capability-advertisement",
        },
        "renderer": render_capability_repo_work,
    },
    "dynamic/capabilities/start-here_v1": {
        "metadata": {
            "name": "Capability Start Here",
            "description": "Advertise a simple set of ways the user can start working with TOAS.",
            "category": "capability-advertisement",
        },
        "renderer": render_capability_start_here,
    },
}


def parse_prompt_ref(ref: str) -> str:
    normalized = ref.strip().strip("/")
    if not normalized:
        raise RuntimeError(f"invalid prompt ref: {ref}")
    if ".." in normalized.split("/"):
        raise RuntimeError(f"invalid prompt ref: {ref}")
    return normalized


def _prompt_file(ref: str):
    return resources.files("toas").joinpath("prompts", f"{ref}.txt")


def _split_frontmatter(text: str) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text.strip()

    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError("invalid prompt metadata") from exc

    if not isinstance(metadata, dict):
        raise RuntimeError("invalid prompt metadata")

    content = text[match.end():].strip()
    return metadata, content


def load_prompt_asset(ref: str) -> PromptAsset:
    normalized = parse_prompt_ref(ref)
    if normalized in _DYNAMIC_PROMPTS:
        dynamic = _DYNAMIC_PROMPTS[normalized]
        return PromptAsset(
            ref=normalized,
            content=dynamic["renderer"](),
            metadata=dynamic["metadata"],
        )
    package = _prompt_file(normalized)
    try:
        raw = package.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing prompt: {normalized}") from exc

    metadata, content = _split_frontmatter(raw)
    return PromptAsset(ref=normalized, content=content, metadata=metadata)


def load_prompt(kind: str, version: str) -> str:
    return load_prompt_asset(f"{kind}/{version}").content


def load_prompt_ref(ref: str) -> str:
    return load_prompt_asset(ref).content


def prompt_messages(kind: str, messages: list[dict], version: str) -> list[dict]:
    return [
        {"role": "system", "content": load_prompt(kind, version=version)},
        *messages,
    ]


def list_prompt_assets(prefix: str | None = None) -> list[PromptAsset]:
    root = resources.files("toas").joinpath("prompts")
    base = root
    normalized_prefix = None
    if prefix is not None:
        normalized_prefix = parse_prompt_ref(prefix)
        base = root.joinpath(normalized_prefix)

    assets = []
    if prefix is None:
        candidate_dynamic = sorted(_DYNAMIC_PROMPTS)
    else:
        candidate_dynamic = sorted(
            ref for ref in _DYNAMIC_PROMPTS if ref == normalized_prefix or ref.startswith(f"{normalized_prefix}/")
        )

    for ref in candidate_dynamic:
        assets.append(load_prompt_asset(ref))

    if not base.exists():
        if assets:
            return assets
        raise RuntimeError(f"missing prompt prefix: {normalized_prefix}")

    for path in sorted(base.rglob("*.txt"), key=lambda p: str(p)):
        rel = Path(str(path.relative_to(root))).with_suffix("")
        ref = rel.as_posix()
        asset = load_prompt_asset(ref)
        assets.append(asset)
    assets.sort(key=lambda asset: asset.ref)
    return assets
