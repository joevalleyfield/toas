"""Presentation edges and declarative template rendering for configuration."""
from __future__ import annotations

import functools
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from ..assets.loader import load_packaged_asset

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext


@functools.lru_cache(maxsize=16)
def load_config_presentation_template(name: str) -> str:
    """Load a presentation template from package assets."""
    return load_packaged_asset("presentation", f"config/{name}", suffix=".txt").content


def _display_value(value: object, *, unset: str = "(unset)") -> str:
    if value is None or value == "" or value == () or value == []:
        return unset
    return str(value)


def render_config_overview(*, step_mod: Any, context: OperatorCommandContext) -> str:
    """Render the operator-facing effective configuration summary."""
    from ..graph import active_target_selection
    from .model_targets import (
        resolve_model_target,
        resolve_target_generation,
        resolve_target_invocation,
    )
    from .policy_edges import settings_for_runtime

    settings, _sources = settings_for_runtime(context.config, runtime_secrets={})
    head_id = next((m.get("id") for m in reversed(context.working) if m.get("id")), None) if context.working else None
    active_id = context.config.llm.target or active_target_selection(context.events, head_id=head_id)
    active_target = resolve_model_target(context.config, active_id) if active_id else None
    invocation = (
        resolve_target_invocation(
            context.config,
            active_target,
            settings,
            secret_resolver=lambda **_kwargs: "",
        )
        if active_target is not None
        else None
    )
    effective_settings = invocation.settings if invocation is not None else settings
    generation = (
        resolve_target_generation(context.config, active_target)
        if active_target is not None
        else context.config.generation
    )
    known_models = {
        model_id
        for endpoint in context.config.llm.endpoints
        for model_id in endpoint.models
        if model_id
    }
    avoid_terms = len(generation.avoid_terms)

    template = load_config_presentation_template("overview")
    rendered = template.format(
        active_target=active_id or "(none)",
        active_endpoint=effective_settings.llm_base_url or "(unset)",
        active_model=effective_settings.llm_model or "(unresolved)",
        transport=effective_settings.llm_transport_mode or "(default)",
        endpoints_count=len(context.config.llm.endpoints),
        targets_count=len(context.config.llm.targets),
        models_count=len(known_models),
        backend_mode=context.config.backend.mode,
        thinking_mode=generation.thinking_mode,
        thinking_budget=generation.thinking_budget_tokens or "(unset)",
        max_tokens=generation.max_tokens or "(auto/unset)",
        max_retries=generation.max_retries,
        retry_delay_s=generation.retry_delay_s,
        avoid_terms=avoid_terms,
        arbitration=context.config.extraction.intent_arbitration,
        shell_staging=context.config.extraction.shell_staging,
        projection_shape=context.config.extraction.projection_shape,
        streaming_mode=context.config.runtime.streaming_mode,
        thinking_stream_mode=context.config.runtime.thinking_stream_mode,
        prompt_progress_mode=context.config.runtime.prompt_progress_mode,
        async_runs=context.config.runtime.async_runs,
        assistant_timeout_s=context.config.shell.assistant_timeout_s,
        newline_style=context.config.tool_writes.newline_style,
    )

    lines = [rendered]
    migration_notice = (context.config_sources or {}).get("__migration__")
    if migration_notice:
        lines.extend(
            [
                "",
                "migration notice:",
                f"  {migration_notice}",
                "  loaded values were normalized into llm.endpoints.",
                "  /config save writes canonical endpoint configuration.",
            ]
        )
    diagnostic_notice = (context.config_sources or {}).get("__diagnostics__")
    if diagnostic_notice:
        lines.extend(
            [
                "",
                "warning: configuration file parse error:",
                f"  {diagnostic_notice}",
                "  file was ignored; using lower precedence or defaults.",
            ]
        )
    return "\n".join(lines)


def render_config_models_overview(*, step_mod: Any, context: OperatorCommandContext) -> str:
    """Render model configuration as an operator-readable topology."""
    from ..graph import active_target_selection
    from .policy_edges import settings_for_runtime

    settings, _sources = settings_for_runtime(context.config, runtime_secrets={})
    head_id = next((m.get("id") for m in reversed(context.working) if m.get("id")), None) if context.working else None
    active_id = context.config.llm.target or active_target_selection(context.events, head_id=head_id)
    active_target = None
    if active_id:
        from .model_targets import (
            resolve_model_target,
            resolve_target_generation,
            resolve_target_invocation,
        )

        active_target = resolve_model_target(context.config, active_id)
        if active_target is not None:
            invocation = resolve_target_invocation(
                context.config,
                active_target,
                settings,
                secret_resolver=lambda **_kwargs: "",
            )
            if invocation is not None:
                settings = invocation.settings
            generation = resolve_target_generation(context.config, active_target)
        else:
            generation = context.config.generation
    else:
        generation = context.config.generation

    # Format endpoints block
    endpoints_lines: list[str] = []
    if context.config.llm.endpoints:
        for endpoint in context.config.llm.endpoints:
            models = ", ".join(endpoint.models) or "(none)"
            refreshed = endpoint.models_last_refreshed_at or "(never)"
            endpoints_lines.extend(
                [
                    f"  {endpoint.id}:",
                    f"    base URL: {_display_value(endpoint.base_url)}",
                    f"    default model: {_display_value(endpoint.default_model)}",
                    f"    known models: {models}",
                    f"    last refresh: {refreshed}",
                    f"    credentials: {endpoint.api_key_source} (ref {endpoint.api_key_ref})",
                ]
            )
    else:
        endpoints_lines.append("  (none)")
    endpoints_block = "\n".join(endpoints_lines)

    # Format targets block
    targets_lines: list[str] = []
    if context.config.llm.targets:
        for target in context.config.llm.targets:
            endpoint_id = target.endpoint or "(default)"
            model_id = target.model or "(inferred)"
            targets_lines.append(f"  {target.id}: endpoint={endpoint_id}, model={model_id}")
    else:
        targets_lines.append("  (none)")
    targets_block = "\n".join(targets_lines)

    template = load_config_presentation_template("models_overview")
    return template.format(
        active_target=active_id or "(none; using global fallback)",
        active_endpoint=_display_value(settings.llm_base_url),
        active_model=_display_value(settings.llm_model, unset="(unresolved)"),
        active_transport=_display_value(settings.llm_transport_mode, unset="(default)"),
        fallback_base_url=_display_value(context.config.llm.base_url),
        fallback_model=_display_value(context.config.llm.model),
        fallback_provider=_display_value(context.config.llm.provider),
        fallback_credentials=f"{context.config.llm.api_key_source} (ref {context.config.llm.api_key_ref})",
        fallback_thinking=generation.thinking_mode,
        fallback_max_tokens=_display_value(generation.max_tokens, unset="(auto)"),
        endpoints_block=endpoints_block,
        targets_block=targets_block,
    )


def render_config_execution_overview(*, step_mod: Any, context: OperatorCommandContext) -> str:
    """Render execution configuration as an operator-readable composed view."""
    shell = context.config.shell
    if hasattr(step_mod, "resolve_effective_shell_allowed") and context.events is not None:
        allowed = step_mod.resolve_effective_shell_allowed(context.working, context.config, context.events)
    else:
        allowed = shell.allowed_commands
    allowed_summary = f"{len(allowed)} commands ({', '.join(allowed[:5])}...)" if len(allowed) > 8 else (", ".join(allowed) or "(none)")
    tool_writes = context.config.tool_writes

    template = load_config_presentation_template("execution_overview")
    return template.format(
        assistant_timeout_s=shell.assistant_timeout_s,
        allowed_summary=allowed_summary,
        newline_style=tool_writes.newline_style,
    )


def render_config_target_overview(target_id: str, *, step_mod: Any, context: OperatorCommandContext) -> str:
    """Render details for a specific configured model target."""
    from ..config import EndpointRateLimitPolicy
    from .model_targets import (
        resolve_model_target,
        resolve_target_generation,
        resolve_target_invocation,
    )
    from .policy_edges import settings_for_runtime

    target = resolve_model_target(context.config, target_id)
    if target is None:
        choices = ", ".join(item.id for item in context.config.llm.targets) or "(none)"
        raise ValueError(f"unknown model target: {target_id}\navailable targets: {choices}")

    base_settings, _ = settings_for_runtime(context.config, runtime_secrets={})
    resolved_inv = resolve_target_invocation(context.config, target, base_settings, secret_resolver=lambda **_kw: "")
    generation = resolve_target_generation(context.config, target)
    endpoint = next((e for e in context.config.llm.endpoints if e.id == target.endpoint.strip()), None) if target.endpoint else None

    endpoint_desc = target.endpoint or "(default)"
    if endpoint is not None and endpoint.base_url:
        endpoint_desc = f"{endpoint_desc} ({endpoint.base_url})"
    model_desc = target.model or (resolved_inv.settings.llm_model if resolved_inv else "(unresolved)")

    rate_limit = endpoint.rate_limit if endpoint is not None else EndpointRateLimitPolicy()
    rpm_str = str(rate_limit.requests_per_minute) if rate_limit.requests_per_minute is not None else "(none)"
    avoid_terms_str = ", ".join(generation.avoid_terms) if generation.avoid_terms else "(none)"

    template = load_config_presentation_template("target_overview")
    rendered = template.format(
        target_id=target.id,
        endpoint_desc=endpoint_desc,
        model_desc=model_desc,
        thinking_mode=generation.thinking_mode,
        thinking_budget=generation.thinking_budget_tokens or "(unset)",
        max_tokens=generation.max_tokens or "(auto/unset)",
        transport_mode=generation.transport_mode,
        max_retries=generation.max_retries,
        retry_delay_s=generation.retry_delay_s,
        avoid_terms_str=avoid_terms_str,
        min_interval_s=rate_limit.min_interval_s,
        rpm_str=rpm_str,
    )

    lines = [rendered]
    if target.tags:
        lines.extend(["", f"tags: {', '.join(target.tags)}"])
    if target.notes:
        lines.extend(["", f"notes: {target.notes}"])
    return "\n".join(lines)


def render_target_list_lines(targets: Sequence[Any]) -> list[str]:
    """Render the list of configured model targets."""
    if not targets:
        return ["no configured model targets"]
    lines = ["configured model targets:"]
    for target in targets:
        endpoint = target.endpoint or "(default)"
        model = target.model or "(inferred)"
        lines.append(f"- {target.id}: endpoint={endpoint}, model={model}")
    return lines
