from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from .loader import load_packaged_asset


@dataclass(frozen=True)
class HelpFacet:
    summary: str = ""
    related_keys: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class HelpTopic:
    topic_id: str
    aliases: tuple[str, ...]
    summary: str
    facets: dict[str, HelpFacet]


@dataclass(frozen=True)
class ConfigHelpCatalog:
    summary: str
    overview_lines: tuple[str, ...]
    topics: tuple[HelpTopic, ...]
    key_descriptions: dict[str, str]


def _string_tuple(value: Any, *, field: str, ref: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise RuntimeError(f"invalid {field} in help asset: {ref}")
    return tuple(item.strip() for item in value)


def _facet(value: Any, *, ref: str) -> HelpFacet:
    if value is None:
        return HelpFacet()
    if not isinstance(value, dict):
        raise RuntimeError(f"invalid facet in help asset: {ref}")
    summary = value.get("summary", "")
    if not isinstance(summary, str):
        raise RuntimeError(f"invalid facet summary in help asset: {ref}")
    return HelpFacet(
        summary=summary.strip(),
        related_keys=_string_tuple(value.get("related_keys"), field="related_keys", ref=ref),
        next_actions=_string_tuple(value.get("next_actions"), field="next_actions", ref=ref),
    )


def load_config_help_catalog() -> ConfigHelpCatalog:
    asset = load_packaged_asset("help", "config", suffix=".yaml")
    try:
        parsed = yaml.safe_load(asset.content) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"invalid help asset: {asset.ref}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"invalid help asset: {asset.ref}")
    summary = parsed.get("summary", "")
    overview = parsed.get("overview", [])
    raw_topics = parsed.get("topics", [])
    raw_descriptions = parsed.get("key_descriptions", {})
    if not isinstance(summary, str) or not isinstance(overview, list) or not all(isinstance(line, str) for line in overview):
        raise RuntimeError(f"invalid config help overview in asset: {asset.ref}")
    if not isinstance(raw_topics, list) or not isinstance(raw_descriptions, dict):
        raise RuntimeError(f"invalid config help catalog in asset: {asset.ref}")

    topics: list[HelpTopic] = []
    for raw_topic in raw_topics:
        if not isinstance(raw_topic, dict):
            raise RuntimeError(f"invalid config help topic in asset: {asset.ref}")
        topic_id = raw_topic.get("id")
        topic_summary = raw_topic.get("summary", "")
        raw_facets = raw_topic.get("facets", {})
        if not isinstance(topic_id, str) or not topic_id.strip() or not isinstance(topic_summary, str):
            raise RuntimeError(f"invalid config help topic in asset: {asset.ref}")
        if not isinstance(raw_facets, dict):
            raise RuntimeError(f"invalid config help facets in asset: {asset.ref}")
        topics.append(
            HelpTopic(
                topic_id=topic_id.strip(),
                aliases=_string_tuple(raw_topic.get("aliases"), field="aliases", ref=asset.ref),
                summary=topic_summary.strip(),
                facets={name: _facet(value, ref=asset.ref) for name, value in raw_facets.items()},
            )
        )
    descriptions: dict[str, str] = {}
    for key, description in raw_descriptions.items():
        if not isinstance(key, str) or not isinstance(description, str) or not key.strip() or not description.strip():
            raise RuntimeError(f"invalid config key description in asset: {asset.ref}")
        descriptions[key.strip()] = description.strip()
    return ConfigHelpCatalog(
        summary=summary.strip(),
        overview_lines=tuple(overview),
        topics=tuple(topics),
        key_descriptions=descriptions,
    )


def resolve_config_help_topic(catalog: ConfigHelpCatalog, query: str) -> HelpTopic | None:
    normalized = query.strip().casefold()
    for topic in catalog.topics:
        if normalized == topic.topic_id.casefold() or normalized in {alias.casefold() for alias in topic.aliases}:
            return topic
    return None


def resolve_config_help_keys(query: str, valid_keys: list[str]) -> list[str] | None:
    """Resolve a curated topic to its currently available related keys."""
    topic = resolve_config_help_topic(load_config_help_catalog(), query)
    if topic is None:
        return None
    facet = topic.facets.get("config")
    if facet is None or not facet.related_keys:
        return []
    available = {key.casefold(): key for key in valid_keys}
    return [available[key.casefold()] for key in facet.related_keys if key.casefold() in available]


def render_config_help(query: str | None = None, *, valid_keys: list[str]) -> str:
    catalog = load_config_help_catalog()
    if not query:
        lines = ["config help:", catalog.summary, *catalog.overview_lines, "", "topics:"]
        lines.extend(f"  {topic.topic_id} ({', '.join(topic.aliases)})" for topic in catalog.topics)
        return "\n".join(lines)

    topic = resolve_config_help_topic(catalog, query)
    if topic is not None:
        facet = topic.facets.get("config") or HelpFacet(summary=topic.summary)
        lines = [f"config help: {topic.topic_id}", facet.summary or topic.summary]
        if facet.related_keys:
            lines.extend(["", "related keys:", *(f"  {key}" for key in facet.related_keys)])
        if facet.next_actions:
            lines.extend(["", "next:", *(f"  {action}" for action in facet.next_actions)])
        return "\n".join(lines)

    normalized = query.strip().casefold()
    if not normalized:
        return render_config_help(valid_keys=valid_keys)
    descriptions = catalog.key_descriptions
    results: list[tuple[int, str, str]] = []
    for key in valid_keys:
        key_lower = key.casefold()
        description = descriptions.get(key, "")
        reason = ""
        rank = 4
        if key_lower == normalized:
            rank, reason = 0, "exact key"
        elif key_lower.startswith(normalized + "."):
            rank, reason = 1, "key prefix"
        elif normalized in {token for token in key_lower.replace(".", "_").replace("-", "_").split("_") if token}:
            rank, reason = 2, "key token"
        elif normalized in description.casefold():
            rank, reason = 3, "description"
        if reason:
            results.append((rank, key, reason))
    if not results:
        return (
            f"config help: no matches for {query!r}\n"
            "hint: try a concept such as models or generation, or an exact key; "
            "use /config show for live state"
        )
    lines = [f"config help search: {query}", "matching keys:"]
    for _rank, key, reason in sorted(results):
        description = descriptions.get(key) or ""
        suffix = f" — {description}" if description else ""
        lines.append(f"  {key}{suffix} (matched by {reason})")
    lines.extend(["", "inspect: /config show <filter>", "set: /config set <key> <value>"])
    return "\n".join(lines)


def render_plain_help(query: str) -> str | None:
    """Render a behavioral topic facet, if the packaged catalog provides one."""
    catalog = load_config_help_catalog()
    topic = resolve_config_help_topic(catalog, query)
    if topic is None:
        return None
    facet = topic.facets.get("plain")
    if facet is None:
        return None
    lines = [f"help: {topic.topic_id}", facet.summary or topic.summary]
    if "config" in topic.facets:
        lines.extend(["", f"configuration: /help config {topic.topic_id}"])
    if facet.next_actions:
        lines.extend(["", "next:", *(f"  {action}" for action in facet.next_actions)])
    return "\n".join(lines)
