from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import re

import yaml


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


@dataclass(frozen=True)
class PromptAsset:
    ref: str
    content: str
    metadata: dict


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

    if not base.exists():
        raise RuntimeError(f"missing prompt prefix: {normalized_prefix}")

    assets = []
    for path in sorted(base.rglob("*.txt"), key=lambda p: str(p)):
        rel = Path(str(path.relative_to(root))).with_suffix("")
        ref = rel.as_posix()
        asset = load_prompt_asset(ref)
        assets.append(asset)
    return assets
