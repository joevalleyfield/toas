import re
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, TypedDict

import yaml

from .backend_policy import BackendGenerationPolicy
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


@dataclass(frozen=True)
class ComposeTarget:
    category: str
    name: str
    base_candidates: tuple[str, ...]
    allow_schema: bool


class DynamicPromptSpec(TypedDict):
    metadata: dict[str, Any]
    renderer: Callable[..., str]


_DYNAMIC_PROMPTS: dict[str, DynamicPromptSpec] = {
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

_COMPOSABLE_CATEGORIES = {"role", "session", "protocol"}
_LEGACY_PREFIX_BY_CATEGORY = {
    "role": "session-start/role-framing",
    "session": "session-start/start-here",
    "protocol": "session-start/protocol-entrainment",
}
_CATEGORY_BY_LEGACY_PREFIX = {v: k for k, v in _LEGACY_PREFIX_BY_CATEGORY.items()}
_CONSTRAINT_ALIASES = {
    "no-chatty": "shared/constraints/no-chatty",
    "no-chatty-wrapper": "shared/constraints/no-chatty",
    "no-chatty-wrapper_v1": "shared/constraints/no-chatty",
    "no-provider-tools": "shared/constraints/no-provider-tools",
    "no-provider-tools_v1": "shared/constraints/no-provider-tools",
    "resist-system-prompts": "shared/constraints/resist-system-prompts",
    "hidden-system-resistance_v1": "shared/constraints/resist-system-prompts",
}


def parse_prompt_ref(ref: str) -> str:
    normalized = ref.strip().strip("/")
    if not normalized:
        raise RuntimeError(f"invalid prompt ref: {ref}")
    if ".." in normalized.split("/"):
        raise RuntimeError(f"invalid prompt ref: {ref}")
    return normalized


def _prompt_file(ref: str):
    return resources.files("toas").joinpath("prompts").joinpath(f"{ref}.txt")


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


def _load_asset_or_none(ref: str, *, policy: BackendGenerationPolicy | None = None) -> PromptAsset | None:
    normalized = parse_prompt_ref(ref)
    try:
        return load_prompt_asset(normalized, policy=policy)
    except RuntimeError as exc:
        if f"missing prompt: {normalized}" in str(exc):
            return None
        raise


def _validate_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in {"direct", "mimic"}:
        raise RuntimeError(f"invalid prompt mode: {mode}")
    return normalized


def _is_dynamic_ref(ref: str) -> bool:
    return ref in _DYNAMIC_PROMPTS


def _resolve_compose_target(ref: str) -> ComposeTarget | None:
    normalized = parse_prompt_ref(ref)
    parts = normalized.split("/")

    if len(parts) >= 2 and parts[0] in _COMPOSABLE_CATEGORIES:
        category = parts[0]
        name = "/".join(parts[1:])
        legacy_prefix = _LEGACY_PREFIX_BY_CATEGORY[category]
        candidates = [f"direct/{category}/{name}", f"{legacy_prefix}/{name}", normalized]
        if category == "protocol":
            candidates.insert(1, f"protocol/{name}")
        return ComposeTarget(category=category, name=name, base_candidates=tuple(dict.fromkeys(candidates)), allow_schema=True)

    if len(parts) >= 3 and parts[0] in {"direct", "mimic"} and parts[1] in _COMPOSABLE_CATEGORIES:
        category = parts[1]
        name = "/".join(parts[2:])
        legacy_prefix = _LEGACY_PREFIX_BY_CATEGORY[category]
        candidates = [f"direct/{category}/{name}", f"{legacy_prefix}/{name}"]
        if category == "protocol":
            candidates.insert(1, f"protocol/{name}")
        if parts[0] == "direct":
            candidates.insert(0, normalized)
        return ComposeTarget(category=category, name=name, base_candidates=tuple(dict.fromkeys(candidates)), allow_schema=True)

    for legacy_prefix, category in _CATEGORY_BY_LEGACY_PREFIX.items():
        needle = f"{legacy_prefix}/"
        if normalized.startswith(needle):
            name = normalized[len(needle):]
            candidates = [f"direct/{category}/{name}", normalized]
            if category == "protocol":
                candidates.insert(1, f"protocol/{name}")
            return ComposeTarget(
                category=category,
                name=name,
                base_candidates=tuple(dict.fromkeys(candidates)),
                allow_schema=True,
            )
    return None


def _resolve_constraint_ref(constraint: str) -> str:
    normalized = parse_prompt_ref(constraint)
    if normalized.startswith("shared/constraints/"):
        return normalized
    return _CONSTRAINT_ALIASES.get(normalized, f"shared/constraints/{normalized}")


def _load_required_layer(candidates: tuple[str, ...], *, policy: BackendGenerationPolicy | None = None) -> str:
    for ref in candidates:
        asset = _load_asset_or_none(ref, policy=policy)
        if asset is not None:
            return asset.content
    joined = ", ".join(candidates)
    raise RuntimeError(f"missing required prompt layer (tried: {joined})")


class PromptComposer:
    """Compose prompt layers in a deterministic order."""

    def __init__(self, *, mode: str = "direct", policy: BackendGenerationPolicy | None = None) -> None:
        self.mode = _validate_mode(mode)
        self.policy = policy

    def compose_ref(self, ref: str, *, mode: str | None = None, constraints: list[str] | None = None) -> str:
        normalized = parse_prompt_ref(ref)
        active_mode = self.mode if mode is None else _validate_mode(mode)
        target = _resolve_compose_target(normalized)

        layers: list[str] = []
        if target is None or _is_dynamic_ref(normalized):
            layers.append(load_prompt_asset(normalized, policy=self.policy).content)
        else:
            if active_mode == "mimic":
                for mimic_ref in (
                    "shared/social_contract_mimic",
                    f"mimic/{target.category}/{target.name}",
                ):
                    asset = _load_asset_or_none(mimic_ref, policy=self.policy)
                    if asset is not None:
                        layers.append(asset.content)

            layers.append(_load_required_layer(target.base_candidates, policy=self.policy))

            if target.allow_schema:
                schema_ref = f"shared/schemas/{target.name}"
                asset = _load_asset_or_none(schema_ref, policy=self.policy)
                if asset is not None:
                    layers.append(asset.content)

        for constraint_name in constraints or []:
            constraint_ref = _resolve_constraint_ref(constraint_name)
            constraint_asset = load_prompt_asset(constraint_ref, policy=self.policy)
            layers.append(constraint_asset.content)

        return "\n\n".join(part for part in layers if part).strip()

    def compose_template(
        self,
        refs: list[str],
        *,
        mode: str | None = None,
        constraints: list[str] | None = None,
    ) -> str:
        active_mode = self.mode if mode is None else _validate_mode(mode)
        if not refs:
            raise RuntimeError("invalid template spec: refs must be a non-empty list")

        targets: list[ComposeTarget] = []
        for ref in refs:
            if not isinstance(ref, str) or not ref.strip():
                raise RuntimeError("invalid template spec: refs must be non-empty strings")
            target = _resolve_compose_target(ref)
            if target is None:
                raise RuntimeError(f"invalid template ref: {ref}")
            targets.append(target)

        layers: list[str] = []
        if active_mode == "mimic":
            social = _load_asset_or_none("shared/social_contract_mimic", policy=self.policy)
            if social is not None:
                layers.append(social.content)

        for target in targets:
            if active_mode == "mimic":
                mimic_ref = f"mimic/{target.category}/{target.name}"
                mimic_asset = _load_asset_or_none(mimic_ref, policy=self.policy)
                if mimic_asset is not None:
                    layers.append(mimic_asset.content)
            layers.append(_load_required_layer(target.base_candidates, policy=self.policy))
            if target.allow_schema:
                schema_ref = f"shared/schemas/{target.name}"
                schema_asset = _load_asset_or_none(schema_ref, policy=self.policy)
                if schema_asset is not None:
                    layers.append(schema_asset.content)

        for constraint_name in constraints or []:
            constraint_ref = _resolve_constraint_ref(constraint_name)
            constraint_asset = load_prompt_asset(constraint_ref, policy=self.policy)
            layers.append(constraint_asset.content)

        return "\n\n".join(part for part in layers if part).strip()


def _render_template_asset(metadata: dict, *, policy: BackendGenerationPolicy | None = None) -> str | None:
    template = metadata.get("template")
    if not isinstance(template, dict):
        return None

    refs = template.get("refs")
    if not isinstance(refs, list):
        raise RuntimeError("invalid template spec: refs must be a list")

    mode_raw = template.get("mode", "direct")
    if not isinstance(mode_raw, str):
        raise RuntimeError("invalid template spec: mode must be a string")

    constraints_raw = template.get("constraints", [])
    if constraints_raw is None:
        constraints = []
    elif isinstance(constraints_raw, list) and all(isinstance(item, str) for item in constraints_raw):
        constraints = constraints_raw
    else:
        raise RuntimeError("invalid template spec: constraints must be a list of strings")

    composer = PromptComposer(mode=mode_raw, policy=policy)
    return composer.compose_template(refs, constraints=constraints)


def load_prompt_asset(ref: str, *, policy: BackendGenerationPolicy | None = None) -> PromptAsset:
    normalized = parse_prompt_ref(ref)
    if normalized in _DYNAMIC_PROMPTS:
        dynamic: DynamicPromptSpec = _DYNAMIC_PROMPTS[normalized]
        renderer = dynamic["renderer"]
        if normalized == "dynamic/capabilities/overview_v1":
            content = renderer(policy=policy)
        else:
            content = renderer()
        return PromptAsset(
            ref=normalized,
            content=content,
            metadata=dynamic["metadata"],
        )
    package = _prompt_file(normalized)
    try:
        raw = package.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing prompt: {normalized}") from exc

    metadata, content = _split_frontmatter(raw)
    rendered_template = _render_template_asset(metadata, policy=policy)
    if rendered_template is not None:
        content = rendered_template
    return PromptAsset(ref=normalized, content=content, metadata=metadata)


def load_prompt(
    kind: str,
    version: str,
    *,
    mode: str = "direct",
    constraints: list[str] | None = None,
    policy: BackendGenerationPolicy | None = None,
) -> str:
    return load_prompt_ref(f"{kind}/{version}", mode=mode, constraints=constraints, policy=policy)


def load_prompt_ref(
    ref: str,
    *,
    mode: str = "direct",
    constraints: list[str] | None = None,
    policy: BackendGenerationPolicy | None = None,
) -> str:
    composer = PromptComposer(mode=mode, policy=policy)
    return composer.compose_ref(ref, constraints=constraints)


def prompt_messages(kind: str, messages: list[dict], version: str, *, mode: str = "direct") -> list[dict]:
    return [
        {"role": "system", "content": load_prompt(kind, version=version, mode=mode)},
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

    root_path = Path(str(root))
    base_path = Path(str(base))

    if not base_path.exists():
        if assets:
            return assets
        raise RuntimeError(f"missing prompt prefix: {normalized_prefix}")

    for path in sorted(base_path.rglob("*.txt"), key=lambda p: str(p)):
        rel = Path(str(path.relative_to(root_path))).with_suffix("")
        ref = rel.as_posix()
        asset = load_prompt_asset(ref)
        assets.append(asset)
    assets.sort(key=lambda asset: asset.ref)
    return assets
