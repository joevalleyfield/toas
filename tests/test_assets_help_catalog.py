from __future__ import annotations

import pytest

import toas.assets.help_catalog as help_catalog
from toas.assets.help_catalog import (
    ConfigHelpCatalog,
    HelpFacet,
    HelpTopic,
    load_config_help_catalog,
    render_config_help,
    render_plain_help,
    resolve_config_help_keys,
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
    topic = resolve_config_help_topic(catalog, "endpoint")
    assert topic is not None
    assert topic.topic_id == "models"
    assert topic.facets["plain"].summary
    assert "llm.model" in topic.facets["config"].related_keys
    assert "llm.targets" in topic.facets["config"].related_keys
    assert "not proof of live availability" in topic.facets["plain"].summary
    assert resolve_config_help_topic(catalog, "missing") is None


def test_config_help_renders_overview_curated_and_search_results():
    overview = render_config_help(valid_keys=["llm.model", "generation.max_tokens"])
    assert overview.startswith("config help:")
    assert "topics:" in overview

    curated = render_config_help("models", valid_keys=["llm.model"])
    assert curated.startswith("config help: models")
    assert "related keys:" in curated
    assert "/config show models" in curated
    assert "live" in curated
    assert "refresh" in curated
    assert "/model select TARGET" in curated
    target_search = render_config_help("llm.targets", valid_keys=["llm.targets"])
    assert "durable named endpoint/model/generation selections" in target_search

    exact = render_config_help("llm.model", valid_keys=["llm.model", "llm.endpoints"])
    assert "matched by exact key" in exact
    prefix = render_config_help("llm", valid_keys=["llm.model", "llm.endpoints"])
    assert "matched by key prefix" in prefix
    token = render_config_help("timeout", valid_keys=["shell.assistant_timeout_s"])
    assert "matched by key token" in token
    description = render_config_help("provider-compatible", valid_keys=["llm.base_url"])
    assert "matched by description" in description
    no_match = render_config_help("unknown", valid_keys=["llm.model"])
    assert "no matches" in no_match


def test_config_help_precedence_topic_exposes_winning_source_guidance():
    rendered = render_config_help("precedence", valid_keys=[])
    assert "config help: precedence" in rendered
    assert "highest-precedence source" in rendered
    assert "winning source only" in rendered
    assert "/config show <topic> --sources" in rendered

    catalog = load_config_help_catalog()
    topic = resolve_config_help_topic(catalog, "sources")
    assert topic is not None
    assert topic.topic_id == "precedence"
    assert resolve_config_help_topic(catalog, "provenance") == topic


def test_config_help_topic_keys_preserve_asset_order_and_omit_missing_keys():
    assert resolve_config_help_keys("models", ["backend.mode", "llm.model", "other"]) == [
        "llm.model",
        "backend.mode",
    ]
    assert resolve_config_help_keys("precedence", ["llm.model"]) == []
    assert resolve_config_help_keys("unknown", ["llm.model"]) is None


def test_plain_help_renders_behavioral_facet_and_config_cross_link():
    rendered = render_plain_help("endpoint")
    assert rendered is not None
    assert rendered.startswith("help: models")
    assert "endpoint provides access" in rendered
    assert "configuration: /help config models" in rendered
    assert "/models refresh local" in rendered
    assert "/model select local-MODEL" in rendered

    for alias in ("model", "endpoint", "models"):
        aliased = render_plain_help(alias)
        assert aliased is not None
        assert aliased.splitlines()[0] == "help: models"

    generation = render_plain_help("generation")
    assert generation is not None
    assert "thinking posture" in generation
    assert "configuration: /help config generation" in generation
    assert render_plain_help("precedence") is None
    assert render_plain_help("unknown") is None


def test_plain_help_renders_extraction_invariant_and_execution_boundary():
    rendered = render_plain_help("intent")
    assert rendered is not None
    assert rendered.startswith("help: extraction")
    assert "source order" in rendered
    assert "does not execute" in rendered
    assert "configuration: /help config extraction" in rendered


def test_plain_help_renders_history_projection_chooser_from_asset():
    rendered = render_plain_help("history")
    assert rendered is not None
    assert rendered.startswith("help: history")
    assert "find branch tips" in rendered
    assert "read a bounded root-to-head lineage" in rendered
    assert "inspect history topology" in rendered
    assert "reconstruct transcript-shaped context" in rendered
    assert "audit model-visible input" in rendered
    assert "configuration:" not in rendered


def test_plain_help_renders_capability_orientation_from_asset():
    rendered = render_plain_help("capabilities")
    assert rendered is not None
    assert rendered.startswith("help: capabilities")
    assert "registry describes" in rendered
    assert "configured profile" in rendered
    assert "currently callable" in rendered
    assert "capability_help(topic: \"capture_task_thread\")" in rendered
    assert "arguments.title" in rendered
    assert "/config show capability_advertisement" in rendered


def test_plain_help_renders_facet_next_actions(monkeypatch):
    catalog = ConfigHelpCatalog(
        summary="summary",
        overview_lines=(),
        topics=(
            HelpTopic(
                "topic",
                (),
                "topic summary",
                {"plain": HelpFacet(summary="plain", next_actions=("/help config topic",))},
            ),
        ),
        key_descriptions={},
    )
    monkeypatch.setattr(help_catalog, "load_config_help_catalog", lambda: catalog)
    assert render_plain_help("topic") == "help: topic\nplain\n\nnext:\n  /help config topic"


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


def test_config_help_streaming_topic_and_plain_help():
    catalog = load_config_help_catalog()
    topic = resolve_config_help_topic(catalog, "streaming")
    assert topic is not None
    assert topic.topic_id == "streaming"
    assert "stream" in topic.aliases
    assert "runtime.streaming_mode" in topic.facets["config"].related_keys
    assert "runtime.thinking_stream_mode" in topic.facets["config"].related_keys

    plain = render_plain_help("streaming")
    assert plain is not None
    assert "generation streaming" in plain
    assert "tool execution streaming" in plain

    rendered_config = render_config_help("streaming", valid_keys=["runtime.streaming_mode"])
    assert "config help: streaming" in rendered_config
    assert "runtime.streaming_mode" in rendered_config
