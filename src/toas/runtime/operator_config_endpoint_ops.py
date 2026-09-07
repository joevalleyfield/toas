from __future__ import annotations

from .operator_command_context import OperatorCommandContext
from .result_nodes import make_result_node

_ENDPOINT_USAGE = (
    "usage: /config endpoint [list|add|set|remove|capture] ...\n"
    "  add NAME BASE_URL\n"
    "  set NAME.FIELD VALUE\n"
    "  remove NAME\n"
    "  capture NAME\n"
    "fields: base_url, default_model, models, provider, api_key_source, api_key_ref, notes\n"
    "next: /models refresh NAME, then /config target add --all-known NAME"
)
_ENDPOINT_SET_USAGE = "usage: /config endpoint set NAME.FIELD VALUE"
_ENDPOINT_SETTABLE_FIELDS = {
    "base_url",
    "default_model",
    "api_key_source",
    "api_key_ref",
    "provider",
    "models",
    "notes",
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
        f"next: /config endpoint set {endpoint_id}.default_model MODEL\n"
        f"then: /models refresh {endpoint_id}",
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


def _normalize_endpoint_set_value(field: str, raw_value: str) -> tuple[str, str | list[str]]:
    canonical_field = field
    if field == "models":
        return canonical_field, [part.strip() for part in raw_value.split(",") if part.strip()]
    if field == "api_key_source":
        value = raw_value.strip().lower()
        if value not in {"env", "keyring"}:
            raise ValueError("endpoint api_key_source must be env|keyring")
        return canonical_field, value
    return canonical_field, raw_value


def _endpoint_set_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 4:
        raise ValueError(_ENDPOINT_SET_USAGE)
    endpoint_target = args[2]
    if "." not in endpoint_target:
        raise ValueError(_ENDPOINT_SET_USAGE)
    endpoint_id, field = endpoint_target.split(".", 1)
    endpoints_updated = endpoint_list_dicts(context=context)
    for item in endpoints_updated:
        if item["id"] != endpoint_id:
            continue
        if field not in _ENDPOINT_SETTABLE_FIELDS:
            raise ValueError("endpoint field must be one of base_url|default_model|api_key_source|api_key_ref|provider|models|notes")
        canonical_field, value = _normalize_endpoint_set_value(field, args[3])
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
