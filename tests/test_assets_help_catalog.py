from __future__ import annotations

import pytest

import toas.assets.help_catalog as help_catalog
from toas.assets.help_catalog import (
    ConfigHelpCatalog,
    HelpFacet,
    HelpTopic,
    load_config_help_catalog,
    render_config_help,
    resolve_config_help_topic,
)
from toas.assets.loader import (
    PackagedAsset,
    list_packaged_assets,
    load_packaged_asset,
    normalize_asset_ref,
)


def test_packaged_asset_loader_lists_and_loads_help_asset():
    assert "config" in list_packaged_assets("help", suffix=".yaml")
    asset = load_packaged_asset("help", "config", suffix=".yaml")
    assert asset.kind == "help"
    assert asset.ref == "config"
    assert "topics:" in asset.content


def test_packaged_asset_loader_rejects_empty_and_traversal_refs():
    with pytest.raises(RuntimeError, match="invalid asset ref"):
        normalize_asset_ref("../help")
    with pytest.raises(RuntimeError, match="invalid asset ref"):
        normalize_asset_ref("/")
    with pytest.raises(RuntimeError, match="missing help asset"):
        load_packaged_asset("help", "missing", suffix=".yaml")


def test_config_help_catalog_parses_topics_facets_and_aliases():
    catalog = load_config_help_catalog()
    assert isinstance(catalog, ConfigHelpCatalog)
    topic = resolve_config_help_topic(catalog, "backend")
    assert topic is not None
    assert topic.topic_id == "models"
    assert topic.facets["plain"].summary
    assert "llm.model" in topic.facets["config"].related_keys
    assert resolve_config_help_topic(catalog, "missing") is None


def test_config_help_renders_overview_curated_and_search_results():
    overview = render_config_help(valid_keys=["llm.model", "generation.max_tokens"])
    assert overview.startswith("config help:")
    assert "topics:" in overview

    curated = render_config_help("models", valid_keys=["llm.model"])
    assert curated.startswith("config help: models")
    assert "related keys:" in curated
    assert "/config show models" in curated

    exact = render_config_help("llm.model", valid_keys=["llm.model", "llm.models"])
    assert "matched by exact key" in exact
    prefix = render_config_help("llm", valid_keys=["llm.model", "llm.models"])
    assert "matched by key prefix" in prefix
    token = render_config_help("timeout", valid_keys=["shell.assistant_timeout_s"])
    assert "matched by key token" in token
    description = render_config_help("provider-compatible", valid_keys=["llm.base_url"])
    assert "matched by description" in description
    no_match = render_config_help("unknown", valid_keys=["llm.model"])
    assert "no matches" in no_match


def test_config_help_rendering_handles_empty_query_and_topics_without_config_facet():
    assert render_config_help("", valid_keys=["llm.model"]).startswith("config help:")
    catalog = ConfigHelpCatalog(
        summary="summary",
        overview_lines=(),
        topics=(HelpTopic("plain", (), "plain summary", {"plain": HelpFacet(summary="plain")}),),
        key_descriptions={},
    )
    assert resolve_config_help_topic(catalog, "plain") is not None


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("topics: [{id: x, summary: x, aliases: bad}]", "invalid aliases"),
        ("topics: [{id: x, summary: x, facets: {plain: []}}]", "invalid facet"),
        ("topics: [{id: x, summary: x, facets: {plain: {summary: 1}}}]", "invalid facet summary"),
        ("[", "invalid help asset"),
        ("- item", "invalid help asset"),
        ("summary: x\noverview: [1]", "invalid config help overview"),
        ("summary: x\ntopics: {}", "invalid config help catalog"),
        ("summary: x\ntopics: [item]", "invalid config help topic"),
        ("summary: x\ntopics: [{id: '', summary: x}]", "invalid config help topic"),
        ("summary: x\ntopics: [{id: x, summary: x, facets: []}]", "invalid config help facets"),
        ("summary: x\nkey_descriptions: {x: 1}", "invalid config key description"),
    ],
)
def test_config_help_catalog_rejects_malformed_assets(monkeypatch, content, message):
    monkeypatch.setattr(
        help_catalog,
        "load_packaged_asset",
        lambda *_args, **_kwargs: PackagedAsset("help", "broken", ".yaml", content),
    )
    with pytest.raises(RuntimeError, match=message):
        load_config_help_catalog()


def test_config_help_catalog_accepts_missing_facet_values(monkeypatch):
    content = "summary: x\ntopics:\n  - id: x\n    summary: x\n    facets:\n      plain:\nkey_descriptions: {}\n"
    monkeypatch.setattr(
        help_catalog,
        "load_packaged_asset",
        lambda *_args, **_kwargs: PackagedAsset("help", "plain", ".yaml", content),
    )
    catalog = load_config_help_catalog()
    assert catalog.topics[0].facets["plain"] == HelpFacet()


def test_config_help_rendering_treats_whitespace_query_as_overview():
    assert render_config_help(" ", valid_keys=[]).startswith("config help:")
