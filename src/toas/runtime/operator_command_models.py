"""Operator commands for model and endpoint configuration and inspection."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..assets.presentation_loader import render_template
from ..graph import active_target_selection
from .model_setup import discovered_model_selection, selection_commands
from .operator_command_registry import OperatorCommandDescriptor

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext


def _display_model_id(model_id: str) -> str:
    """Keep endpoint path prefixes out of the compact operator view."""
    return model_id.rsplit("/", 1)[-1] or model_id


def _parse_models_flags(args: list[str]) -> tuple[str | None, bool, bool]:
    endpoint: str | None = None
    details = False
    raw = False
    for arg in args:
        if arg == "--details":
            if details:
                raise ValueError("usage: /models ... ENDPOINT [--details|--raw]")
            details = True
        elif arg == "--raw":
            if raw:
                raise ValueError("usage: /models ... ENDPOINT [--details|--raw]")
            raw = True
        elif endpoint is None and arg.strip():
            endpoint = arg.strip()
        else:
            raise ValueError("usage: /models ... ENDPOINT [--details|--raw]")
    return endpoint, details, raw


def _resolve_models_endpoint(endpoint_id: str | None, context: OperatorCommandContext) -> str:
    if endpoint_id is not None:
        return endpoint_id
    endpoints = context.config.llm.endpoints
    if not endpoints:
        raise ValueError("no configured endpoints\nhint: use /config endpoint add NAME BASE_URL")
    if len(endpoints) > 1:
        choices = ", ".join(endpoint.id for endpoint in endpoints)
        raise ValueError(f"endpoint is required when multiple endpoints are configured: {choices}")
    return endpoints[0].id


def handle_endpoint_command(args: list[str], context: OperatorCommandContext, step_mod: Any) -> Any:
    """Handle /endpoint command."""
    if len(args) > 1:
        raise ValueError("usage: /endpoint [id]")
    available = step_mod._available_endpoints(context.config)
    if not args:
        if not available:
            return "no endpoints available in current capability space"
        endpoints_block = "\n".join(f"/endpoint {name}" for name in available)
        return render_template("models", "available_endpoints", endpoints_block=endpoints_block)
    selected = args[0]
    unavailable_block = ""
    if available and selected not in available:
        options = "\n".join(f"/endpoint {name}" for name in available)
        unavailable_block = f"\n\nchosen endpoint unavailable in current capability space\nchoose one of:\n{options}"
    return render_template("models", "endpoint_intent", selected=selected, unavailable_block=unavailable_block)


def handle_endpoints_command(args: list[str], context: OperatorCommandContext, step_mod: Any) -> Any:
    """Handle /endpoints command."""
    if args:
        raise ValueError("usage: /endpoints")
    endpoints = context.config.llm.endpoints
    if not endpoints:
        return "no configured endpoints"

    lines = []
    for endpoint in endpoints:
        provider = endpoint.provider or "(default)"
        default_model = endpoint.default_model or "(none)"
        models = ", ".join(endpoint.models) if endpoint.models else "(none)"
        refreshed = endpoint.models_last_refreshed_at or "(never)"
        unseen = [
            observation.id
            for observation in endpoint.model_observations
            if endpoint.models_last_refreshed_at and observation.last_seen != endpoint.models_last_refreshed_at
        ]
        unseen_text = ", ".join(unseen) if unseen else "(none)"
        lines.append(
            f"- {endpoint.id}: provider={provider}, base_url={endpoint.base_url}, "
            f"default_model={default_model}, known_models={models}, last_refresh={refreshed}, "
            f"not_seen_latest={unseen_text}"
        )
    return render_template("models", "endpoints_list", endpoints_block="\n".join(lines))


def handle_model_command(args: list[str], context: OperatorCommandContext, step_mod: Any) -> Any:
    """Handle /model command."""
    if not args:
        return _handle_model_overview(step_mod=step_mod, context=context)
    handlers = {"targets": _handle_model_targets, "select": _handle_model_select}
    if args[0] in handlers:
        return handlers[args[0]](args[1:], step_mod=step_mod, context=context)
    raise ValueError("usage: /model | /model targets | /model select <target> | /model select ENDPOINT MODEL")


def _handle_model_overview(*, step_mod: Any, context: OperatorCommandContext) -> str:
    from .model_targets import resolve_model_target

    head_id = next((m.get("id") for m in reversed(context.working) if m.get("id")), None) if context.working else None
    active_id = active_target_selection(context.events, head_id=head_id)
    active = resolve_model_target(context.config, active_id) if active_id else None
    if active is None:
        return render_template("models", "model_fallback_overview", fallback=context.config.llm.model.strip() or "(none)")
    return render_template("models", "model_overview", active_id=active.id, endpoint=active.endpoint or "(default)", model=active.model or "(inferred)")


def _handle_model_targets(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> str:
    if args:
        raise ValueError("usage: /model targets")
    from .model_targets import resolve_target_invocation

    if not context.config.llm.targets:
        return "no configured model targets"
    head_id = next((m.get("id") for m in reversed(context.working) if m.get("id")), None) if context.working else None
    active = active_target_selection(context.events, head_id=head_id)
    lines = []
    for target in context.config.llm.targets:
        resolved = resolve_target_invocation(context.config, target, step_mod.Settings.from_env())
        endpoint = target.endpoint or "(default)"
        model = target.model or (resolved.settings.llm_model if resolved is not None else "(unresolved)")
        status = "ready" if resolved is not None else "unresolved endpoint"
        marker = " *" if target.id == active else ""
        lines.append(f"- {target.id}{marker}: endpoint={endpoint}, model={model}, status={status}")
    return render_template("models", "model_targets_list", targets_block="\n".join(lines), active_target=active or "(none)")


def _handle_model_select(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if len(args) == 2:
        fields = discovered_model_selection(context.config, args[0], args[1])
        content = fields.pop("content")
        return content, fields
    if len(args) != 1 or not args[0].strip():
        raise ValueError("usage: /model select <target> | /model select ENDPOINT MODEL")
    target_id = args[0].strip()
    from .model_targets import resolve_model_target, resolve_target_invocation

    target = resolve_model_target(context.config, target_id)
    if target is None:
        choices = ", ".join(item.id for item in context.config.llm.targets) or "(none)"
        raise ValueError(f"unknown model target: {target_id}\navailable targets: {choices}")
    if resolve_target_invocation(context.config, target, step_mod.Settings.from_env()) is None:
        raise ValueError(f"model target endpoint is not configured: {target_id}")
    return (
        f"selected model target: {target.id}",
        {"policy_update": {"key": "llm.target", "scope": "session", "action": "set", "value": target.id}},
    )


def _endpoint_runtime_settings(endpoint: Any, context: OperatorCommandContext, step_mod: Any) -> Any:
    from ..secrets import resolve_secret
    from .policy_edges import settings_for_runtime

    base_settings, _sources = settings_for_runtime(context.config)
    endpoint_key = resolve_secret(
        source=endpoint.api_key_source,
        ref=endpoint.api_key_ref,
        default=base_settings.llm_api_key,
    )
    return step_mod.Settings(
        llm_base_url=endpoint.base_url or base_settings.llm_base_url,
        llm_api_key=endpoint_key,
        llm_model=endpoint.default_model or base_settings.llm_model,
        llm_trace=base_settings.llm_trace,
        llm_transport_mode=base_settings.llm_transport_mode,
        llm_stream_mode=base_settings.llm_stream_mode,
        llm_provider=endpoint.provider or base_settings.llm_provider,
        llm_ca_file=base_settings.llm_ca_file,
    )


def _endpoint_dict(entry: Any) -> dict[str, Any]:
    return {
        "id": entry.id,
        "base_url": entry.base_url,
        "default_model": entry.default_model,
        "models": list(entry.models),
        "api_key_source": entry.api_key_source,
        "api_key_ref": entry.api_key_ref,
        "provider": entry.provider,
        "tags": list(entry.tags),
        "notes": entry.notes,
        "models_last_refreshed_at": entry.models_last_refreshed_at,
        "model_observations": [{"id": item.id, "last_seen": item.last_seen} for item in entry.model_observations],
    }


def handle_models_command(args: list[str], context: OperatorCommandContext, step_mod: Any) -> Any:
    """Handle /models command."""
    if not args:
        return render_template("models", "models_help")
    mode = args[0]
    if mode == "refresh":
        return _handle_models_refresh(args[1:], step_mod=step_mod, context=context)
    if mode not in {"live", "known"}:
        raise ValueError("usage: /models live|known|refresh ENDPOINT (configured endpoint name)")
    endpoint_id, details, raw = _parse_models_flags(args[1:])
    if raw and mode == "known":
        raise ValueError("/models known does not support --raw; the known catalog has no stored response body")
    endpoint_id = _resolve_models_endpoint(endpoint_id, context)
    endpoint = next((entry for entry in context.config.llm.endpoints if entry.id == endpoint_id), None)
    if endpoint is None:
        raise ValueError(f"unknown endpoint: {endpoint_id}")
    if mode == "known":
        models = ", ".join(endpoint.models) if endpoint.models else "(none)"
        unseen = ", ".join(
            observation.id
            for observation in endpoint.model_observations
            if endpoint.models_last_refreshed_at and observation.last_seen != endpoint.models_last_refreshed_at
        ) or "(none)"
        details_block = "\n  details: normalized endpoint metadata is not available yet; use /models live ENDPOINT --raw" if details else ""
        return render_template("models", "known_catalog", endpoint_id=endpoint.id, models=models, last_refresh=endpoint.models_last_refreshed_at or "(never)", unseen=unseen, details_block=details_block, selection_block="\n".join(selection_commands(endpoint)))

    from ..llm_harness import fetch_models
    from .model_observations import observe_endpoint_models

    settings = _endpoint_runtime_settings(endpoint, context, step_mod)
    observation = observe_endpoint_models(settings, fetcher=fetch_models, include_raw=raw)
    models_text = ", ".join(_display_model_id(m) for m in observation.get("models", ())) if observation.get("models") else "(none)"
    status_details = f"  reported models: {models_text}" if observation["status"] == "ok" else f"  error: {observation['error']}"
    details_block = "\n  details: normalized model metadata is not available yet; use --raw for the endpoint response" if details else ""
    raw_block = f"\n  raw response:\n{observation.get('raw_response', observation.get('error', '(none)'))}" if raw else ""
    return render_template("models", "live_observation", endpoint=observation["endpoint"] or "(default)", protocol=observation["protocol"] or "(unknown)", status=observation["status"], status_details=status_details, details_block=details_block, raw_block=raw_block)


def _handle_models_refresh(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> Any:
    endpoint_id, details, raw = _parse_models_flags(args)
    endpoint_id = _resolve_models_endpoint(endpoint_id, context)
    endpoint = next((entry for entry in context.config.llm.endpoints if entry.id == endpoint_id), None)
    if endpoint is None:
        raise ValueError(f"unknown endpoint: {endpoint_id}")

    from ..llm_harness import fetch_models
    from .model_observations import merge_endpoint_model_ids, observe_endpoint_models

    settings = _endpoint_runtime_settings(endpoint, context, step_mod)
    observation = observe_endpoint_models(settings, fetcher=fetch_models, include_raw=raw)
    if observation["status"] != "ok":
        lines = [
            f"model catalog refresh failed for {endpoint_id}: {observation['status']}",
            f"error: {observation['error']}",
        ]
        if raw:
            lines.extend(["raw response:", str(observation.get("raw_response", observation.get("error", "(none)")))])
        return "\n".join(lines)

    refreshed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    updated_endpoint = merge_endpoint_model_ids(
        endpoint,
        observation.get("models", ()),
        observed_at=refreshed_at,
    )
    updated_endpoint = replace(updated_endpoint, models_last_refreshed_at=refreshed_at)
    endpoints = [
        _endpoint_dict(updated_endpoint if entry.id == endpoint_id else entry)
        for entry in context.config.llm.endpoints
    ]
    observed = observation.get("models", ())
    added = [model_id for model_id in observed if model_id not in endpoint.models]
    content = (
        f"model catalog refreshed for {endpoint_id}: "
        f"added {', '.join(_display_model_id(model_id) for model_id in added) if added else '(none)'} "
        f"({len(added)} added), "
        f"{len(updated_endpoint.models)} known"
    )
    if details:
        content += "\ndetails: normalized model metadata is not available yet"
    content += "\n\nselect a model:\n" + "\n".join(selection_commands(updated_endpoint))
    if raw:
        content += "\nraw response:\n" + str(observation.get("raw_response", "(none)"))
    return content, {"config_update": {"llm": {"endpoints": endpoints}}}


def get_models_command_descriptors() -> tuple[OperatorCommandDescriptor, ...]:
    """Return descriptors for model and endpoint operator commands."""
    return (
        OperatorCommandDescriptor("endpoint", "Inspect or select available endpoint intent", "usage: /endpoint [id]", "models", handle_endpoint_command),
        OperatorCommandDescriptor("endpoints", "List configured model endpoints and catalog status", "usage: /endpoints", "models", handle_endpoints_command),
        OperatorCommandDescriptor("model", "Inspect or select active model target", "usage: /model | /model targets | /model select <target> | /model select ENDPOINT MODEL", "models", handle_model_command),
        OperatorCommandDescriptor("models", "Query live endpoints or inspect durable model catalog", "usage: /models live|known|refresh ENDPOINT (configured endpoint name)", "models", handle_models_command),
    )
