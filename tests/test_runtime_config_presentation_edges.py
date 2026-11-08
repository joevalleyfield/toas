from __future__ import annotations

from dataclasses import replace

import pytest

from toas.config import (
    EndpointCatalogEntry,
    EndpointRateLimitPolicy,
    OperatorConfig,
    TargetCatalogEntry,
    TargetGenerationOverrides,
)
from toas.runtime.config_presentation_edges import (
    _display_value,
    load_config_presentation_template,
    render_config_execution_overview,
    render_config_models_overview,
    render_config_overview,
    render_config_target_overview,
    render_target_list_lines,
)
from toas.runtime.operator_command_context import OperatorCommandContext


def _make_context(
    config: OperatorConfig,
    *,
    events: list[dict] | None = None,
    working: list[dict] | None = None,
    config_sources: dict[str, str] | None = None,
) -> OperatorCommandContext:
    return OperatorCommandContext(
        execute=None,
        generate=None,
        events=events or [],
        working=working or [],
        frontier_role="user",
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[],
        config=config,
        config_sources=config_sources or {},
        already_executed_indices=None,
    )


def test_load_config_presentation_template():
    tmpl = load_config_presentation_template("overview")
    assert "effective configuration" in tmpl
    # Caching check
    assert load_config_presentation_template("overview") is tmpl


def test_display_value():
    assert _display_value(None) == "(unset)"
    assert _display_value("") == "(unset)"
    assert _display_value(()) == "(unset)"
    assert _display_value([]) == "(unset)"
    assert _display_value("foo") == "foo"
    assert _display_value(123) == "123"
    assert _display_value(None, unset="custom") == "custom"


def test_render_config_overview_basic():
    config = OperatorConfig()
    context = _make_context(config)
    res = render_config_overview(step_mod=None, context=context)
    assert "effective configuration" in res
    assert "active target: (none)" in res
    assert "migration notice:" not in res
    assert "warning: configuration file parse error:" not in res


def test_render_config_overview_with_notices_and_active_target():
    config = OperatorConfig()
    endpoints = (
        EndpointCatalogEntry(id="ep-1", base_url="http://ep1:8080/v1", default_model="m1", models=("m1", "m2")),
    )
    targets = (
        TargetCatalogEntry(id="target-1", endpoint="ep-1", model="m1"),
    )
    config = replace(config, llm=replace(config.llm, endpoints=endpoints, targets=targets, target="target-1"))
    context = _make_context(
        config,
        config_sources={
            "__migration__": "old config was migrated",
            "__diagnostics__": "corrupt file skipped",
        },
    )
    res = render_config_overview(step_mod=None, context=context)
    assert "active target: target-1" in res
    assert "migration notice:" in res
    assert "old config was migrated" in res
    assert "warning: configuration file parse error:" in res
    assert "corrupt file skipped" in res


def test_render_config_models_overview():
    # 1. Empty endpoints and targets, no active target
    config = OperatorConfig()
    context = _make_context(config)
    res = render_config_models_overview(step_mod=None, context=context)
    assert "target: (none; using global fallback)" in res
    assert "endpoints:\n  (none)" in res
    assert "targets:\n  (none)" in res

    # 2. Configured endpoints and targets, active target resolving
    endpoints = (
        EndpointCatalogEntry(
            id="ep-local",
            base_url="http://localhost:11434/v1",
            default_model="qwen3",
            models=("qwen3", "llama3"),
            models_last_refreshed_at="2026-11-08T12:00:00Z",
            api_key_source="keyring",
            api_key_ref="local_key",
        ),
    )
    targets = (
        TargetCatalogEntry(id="fast", endpoint="ep-local", model="qwen3"),
    )
    config = replace(config, llm=replace(config.llm, endpoints=endpoints, targets=targets, target="fast"))
    context = _make_context(config)
    res = render_config_models_overview(step_mod=None, context=context)
    assert "target: fast" in res
    assert "ep-local:" in res
    assert "fast: endpoint=ep-local, model=qwen3" in res

    # 3. Active target set but unresolvable
    config = replace(config, llm=replace(config.llm, target="ghost"))
    context = _make_context(config)
    res = render_config_models_overview(step_mod=None, context=context)
    assert "target: ghost" in res


def test_render_config_execution_overview():
    config = OperatorConfig()
    config = replace(config, shell=replace(config.shell, allowed_commands=("git", "ls")))
    context = _make_context(config)
    res = render_config_execution_overview(step_mod=None, context=context)
    assert "execution configuration" in res
    assert "shell.allowed_commands: git, ls" in res

    # More than 8 commands summary truncation
    config = replace(config, shell=replace(config.shell, allowed_commands=tuple(f"cmd{i}" for i in range(10))))
    context = _make_context(config)
    res = render_config_execution_overview(step_mod=None, context=context)
    assert "10 commands (cmd0, cmd1, cmd2, cmd3, cmd4...)" in res

    # Empty commands
    config = replace(config, shell=replace(config.shell, allowed_commands=()))
    context = _make_context(config)
    res = render_config_execution_overview(step_mod=None, context=context)
    assert "shell.allowed_commands: (none)" in res

    # Dynamic step_mod resolver
    class StepMod:
        @staticmethod
        def resolve_effective_shell_allowed(working, cfg, events):
            return ["dynamic_cmd"]

    context = _make_context(config, events=[{"id": "e1"}])
    res = render_config_execution_overview(step_mod=StepMod, context=context)
    assert "shell.allowed_commands: dynamic_cmd" in res


def test_render_config_target_overview():
    config = OperatorConfig()
    context = _make_context(config)

    # Unknown target raises ValueError
    with pytest.raises(ValueError, match="unknown model target: missing"):
        render_config_target_overview("missing", step_mod=None, context=context)

    # Target configured with tags, notes, endpoint rate limit
    endpoints = (
        EndpointCatalogEntry(
            id="ep-1",
            base_url="https://api.example.com/v1",
            rate_limit=EndpointRateLimitPolicy(min_interval_s=1.5, requests_per_minute=60),
        ),
        EndpointCatalogEntry(
            id="ep-nobase",
            base_url="",
        ),
    )
    targets = (
        TargetCatalogEntry(
            id="t1",
            endpoint="ep-1",
            model="gpt-4o",
            tags=("prod", "smart"),
            notes="Use for code reviews",
        ),
        TargetCatalogEntry(
            id="t2",
            endpoint="ep-nobase",
            model="",
            generation=TargetGenerationOverrides(avoid_terms=()),
        ),
        TargetCatalogEntry(
            id="t3",
            endpoint="",
            model="",
        ),
    )
    config = replace(config, llm=replace(config.llm, endpoints=endpoints, targets=targets))
    context = _make_context(config)
    res = render_config_target_overview("t1", step_mod=None, context=context)
    assert "target: t1" in res
    assert "endpoint: ep-1 (https://api.example.com/v1)" in res
    assert "model: gpt-4o" in res
    assert "tags: prod, smart" in res
    assert "notes: Use for code reviews" in res
    assert "requests per minute: 60" in res

    res2 = render_config_target_overview("t2", step_mod=None, context=context)
    assert "endpoint: ep-nobase" in res2
    assert "requests per minute: (none)" in res2
    assert "avoid terms: (none)" in res2

    res3 = render_config_target_overview("t3", step_mod=None, context=context)
    assert "endpoint: (default)" in res3


def test_render_target_list_lines():
    assert render_target_list_lines([]) == ["no configured model targets"]

    targets = [
        TargetCatalogEntry(id="t1", endpoint="ep-1", model="m1"),
        TargetCatalogEntry(id="t2", endpoint="", model=""),
    ]
    lines = render_target_list_lines(targets)
    assert lines[0] == "configured model targets:"
    assert lines[1] == "- t1: endpoint=ep-1, model=m1"
    assert lines[2] == "- t2: endpoint=(default), model=(inferred)"
