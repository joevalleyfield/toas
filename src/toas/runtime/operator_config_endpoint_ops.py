from __future__ import annotations

from dataclasses import asdict

from ..config import OperatorConfig
from .operator_command_context import OperatorCommandContext
from .result_nodes import make_result_node

_ENDPOINT_USAGE = (
    "usage: /config endpoint [list|add|set|remove|capture] ...\n"
    "  add NAME BASE_URL\n"
    "  set NAME.FIELD VALUE\n"
    "  set NAME FIELD VALUE\n"
    "  remove NAME\n"
    "  capture NAME\n"
    "fields: base_url, default_model, models, provider, api_key_source, api_key_ref, notes, generation.<trait>, rate_limit.<trait>\n"
    "next: /models refresh NAME, then /config target add --all-known NAME"
)
_ENDPOINT_SET_USAGE = (
    "usage: /config endpoint set NAME.FIELD VALUE | /config endpoint NAME set FIELD VALUE\n"
    "fields: base_url, default_model, models, provider, api_key_source, api_key_ref, notes, generation.<trait>, rate_limit.<trait>\n"
    "environment-variable auth: set NAME.api_key_ref ENV_VAR_NAME "
    "(api_key_source defaults to env; api_key_ref defaults to TOAS_LLM_API_KEY)"
)
_ENDPOINT_SETTABLE_FIELDS = {
    "base_url",
    "default_model",
    "api_key_source",
    "api_key_ref",
    "provider",
    "models",
    "notes",
    "generation.thinking_mode",
    "generation.thinking_budget_tokens",
    "generation.max_tokens",
    "generation.max_retries",
    "generation.retry_delay_s",
    "generation.transport_mode",
    "generation.avoid_terms",
    "rate_limit.min_interval_s",
    "rate_limit.requests_per_minute",
}


def _result_node(content: str, *, step_mod, context: OperatorCommandContext, **fields) -> dict:
    return make_result_node(content, origin_role=context.frontier_role, origin_kind="slash_command", **fields)


def endpoint_list_dicts(*, context: OperatorCommandContext) -> list[dict]:
    return [
        {
            "id": endpoint.id,
            "base_url": endpoint.base_url,
            "default_model": endpoint.default_model,
            "models": list(endpoint.models),
            "api_key_source": endpoint.api_key_source,
            "api_key_ref": endpoint.api_key_ref,
            "provider": endpoint.provider,
            "tags": list(endpoint.tags),
            "notes": endpoint.notes,
            "models_last_refreshed_at": endpoint.models_last_refreshed_at,
            "model_observations": [{"id": item.id, "last_seen": item.last_seen} for item in endpoint.model_observations],
            "generation": {k: v for k, v in asdict(endpoint.generation).items() if v is not None},
            "rate_limit": asdict(endpoint.rate_limit),
        }
        for endpoint in context.config.llm.endpoints
    ]


def _endpoint_list_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 2:
        raise ValueError("usage: /config endpoint list")
    if not context.config.llm.endpoints:
        return [_result_node("no configured endpoints", step_mod=step_mod, context=context)]
    lines = ["configured endpoints:"]
    for endpoint in context.config.llm.endpoints:
        lines.append(f"- {endpoint.id}: {endpoint.base_url} (model={endpoint.default_model or '-'})")
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context)]


def _endpoint_add_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 4:
        raise ValueError("usage: /config endpoint add NAME BASE_URL")
    endpoint_id = args[2].strip()
    base_url = args[3].strip()
    if not endpoint_id or not base_url:
        raise ValueError("endpoint NAME/BASE_URL must be non-empty")
    endpoints_updated = [entry for entry in endpoint_list_dicts(context=context) if entry["id"] != endpoint_id]
    endpoints_updated.append({
        "id": endpoint_id,
        "base_url": base_url,
        "default_model": "",
        "models": [],
        "api_key_source": "env",
        "api_key_ref": "TOAS_LLM_API_KEY",
        "provider": "",
        "tags": [],
        "notes": "",
        "models_last_refreshed_at": "",
    })
    return [_result_node(
        f"added endpoint {endpoint_id}\n"
        f"next: /models refresh {endpoint_id}\n"
        "then: use a selection command from the discovered model list\n"
        f"if authentication is required: /config endpoint set {endpoint_id}.api_key_ref ENV_VAR_NAME (defaults to TOAS_LLM_API_KEY)",
        step_mod=step_mod,
        context=context,
        config_update={"llm": {"endpoints": endpoints_updated}},
    )]


def _endpoint_remove_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 3:
        raise ValueError("usage: /config endpoint remove NAME")
    endpoint_id = args[2].strip()
    endpoints_updated = [entry for entry in endpoint_list_dicts(context=context) if entry["id"] != endpoint_id]
    return [_result_node(f"removed endpoint {endpoint_id}", step_mod=step_mod, context=context, config_update={"llm": {"endpoints": endpoints_updated}})]


def _normalize_endpoint_set_value(field: str, raw_value: str) -> tuple[str, object]:
    canonical_field = field
    if field == "models":
        return canonical_field, [part.strip() for part in raw_value.split(",") if part.strip()]
    if field == "api_key_source":
        value = raw_value.strip().lower()
        if value not in {"env", "keyring"}:
            raise ValueError("endpoint api_key_source must be env|keyring")
        return canonical_field, value
    if field in {"generation.thinking_budget_tokens", "generation.max_tokens", "generation.max_retries"}:
        try:
            int_val = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"{field}: expected int") from exc
        if int_val < 0:
            raise ValueError(f"{field}: expected >= 0")
        return canonical_field, int_val
    if field == "generation.retry_delay_s":
        try:
            parsed_value = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"{field}: expected float") from exc
        if parsed_value < 0:
            raise ValueError(f"{field}: expected >= 0")
        return canonical_field, parsed_value
    if field == "generation.avoid_terms":
        return canonical_field, [part.strip() for part in raw_value.split(",") if part.strip()]
    if field == "rate_limit.min_interval_s":
        try:
            parsed_value = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"{field}: expected float") from exc
        if parsed_value < 0:
            raise ValueError(f"{field}: expected >= 0")
        return canonical_field, parsed_value
    if field == "rate_limit.requests_per_minute":
        stripped = raw_value.strip().lower()
        if stripped in {"", "none", "null", "unset"}:
            return canonical_field, None
        try:
            rpm_value = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"{field}: expected int") from exc
        if rpm_value <= 0:
            raise ValueError(f"{field}: expected > 0")
        return canonical_field, rpm_value
    return canonical_field, raw_value


def _endpoint_set_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) == 5 and args[2] == "set":
        endpoint_id = args[1].strip()
        field = args[3].strip()
        raw_value = args[4]
    elif len(args) == 5 and args[1] == "set":
        endpoint_id = args[2].strip()
        field = args[3].strip()
        raw_value = args[4]
    elif len(args) == 4 and args[1] == "set":
        endpoint_target = args[2]
        if "." not in endpoint_target:
            raise ValueError(_ENDPOINT_SET_USAGE)
        endpoint_id, field = endpoint_target.split(".", 1)
        endpoint_id = endpoint_id.strip()
        field = field.strip()
        raw_value = args[3]
    else:
        raise ValueError(_ENDPOINT_SET_USAGE)

    endpoints_updated = endpoint_list_dicts(context=context)
    for item in endpoints_updated:
        if item["id"] != endpoint_id:
            continue
        if field not in _ENDPOINT_SETTABLE_FIELDS:
            allowed = "base_url|default_model|api_key_source|api_key_ref|provider|models|notes|generation.<trait>|rate_limit.<trait>"
            raise ValueError(f"endpoint field must be one of {allowed}")
        canonical_field, value = _normalize_endpoint_set_value(field, raw_value)
        if "." in canonical_field:
            prefix, sub = canonical_field.split(".", 1)
            item.setdefault(prefix, {})[sub] = value
        else:
            item[canonical_field] = value
        return [_result_node(f"updated endpoint {endpoint_id}.{canonical_field}", step_mod=step_mod, context=context, config_update={"llm": {"endpoints": endpoints_updated}})]
    raise ValueError(f"unknown endpoint id: {endpoint_id}")


def _endpoint_capture_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 3:
        raise ValueError("usage: /config endpoint capture NAME")
    endpoint_id = args[2].strip()
    settings = step_mod.Settings.from_env()
    endpoints_updated = [entry for entry in endpoint_list_dicts(context=context) if entry["id"] != endpoint_id]
    endpoints_updated.append({
        "id": endpoint_id,
        "base_url": settings.llm_base_url,
        "default_model": settings.llm_model,
        "models": [settings.llm_model] if settings.llm_model else [],
        "api_key_source": "env",
        "api_key_ref": "TOAS_LLM_API_KEY",
        "provider": getattr(settings, "llm_provider", ""),
        "tags": [],
        "notes": "captured from current TOAS_LLM_* runtime",
        "models_last_refreshed_at": "",
    })
    return [_result_node(f"captured endpoint {endpoint_id} from current runtime", step_mod=step_mod, context=context, config_update={"llm": {"endpoints": endpoints_updated}})]


def config_endpoint_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) < 2:
        raise ValueError(_ENDPOINT_USAGE)
    if len(args) >= 3 and args[2] == "set":
        return _endpoint_set_result(args, step_mod=step_mod, context=context)
    handlers = {
        "list": _endpoint_list_result,
        "add": _endpoint_add_result,
        "remove": _endpoint_remove_result,
        "set": _endpoint_set_result,
        "capture": _endpoint_capture_result,
    }
    handler = handlers.get(args[1])
    if handler is None:
        raise ValueError(_ENDPOINT_USAGE)
    return handler(args, step_mod=step_mod, context=context)


def endpoint_declaration_update(args: list[str], *, config: OperatorConfig) -> dict:
    """Reconstitute deterministic endpoint declarations without external probes."""
    context = OperatorCommandContext(
        execute=None, events=[], working=[], frontier_role="user", transcript="",
        command_cwd=".", previous_command_cwd=None, workspace_mode="strict",
        workspace_roots=[], config=config, config_sources=None, already_executed_indices=None,
    )
    if len(args) >= 3 and args[2] == "set":
        return _endpoint_set_result(args, context=context)[0]["config_update"]
    handlers = {"add": _endpoint_add_result, "set": _endpoint_set_result, "remove": _endpoint_remove_result}
    return handlers[args[1]](args, context=context)[0]["config_update"]
