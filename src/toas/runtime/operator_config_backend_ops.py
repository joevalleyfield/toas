from __future__ import annotations

from .operator_command_context import OperatorCommandContext
from .result_nodes import make_result_node

_BACKEND_USAGE = "usage: /config backend [list|add|set|remove|capture] ..."
_BACKEND_SET_USAGE = "usage: /config backend set <id>.<field> <value>"
_BACKEND_SETTABLE_FIELDS = {"base_url", "model", "api_key_source", "api_key_ref", "models", "notes"}


def _result_node(content: str, *, step_mod, context: OperatorCommandContext, **fields) -> dict:
    return make_result_node(
        content,
        origin_role=context.frontier_role,
        origin_kind="slash_command",
        **fields,
    )


def backend_list_dicts(*, context: OperatorCommandContext) -> list[dict]:
    return [
        {
            "id": b.id,
            "base_url": b.base_url,
            "model": b.model,
            "models": list(b.models),
            "api_key_source": b.api_key_source,
            "api_key_ref": b.api_key_ref,
            "tags": list(b.tags),
            "notes": b.notes,
        }
        for b in context.config.llm.backends
    ]


def _backend_list_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 2:
        raise ValueError("usage: /config backend list")
    if not context.config.llm.backends:
        return [_result_node("no configured backends", step_mod=step_mod, context=context)]
    lines = ["configured backends:"]
    for backend in context.config.llm.backends:
        lines.append(f"- {backend.id}: {backend.base_url} (model={backend.model or '-'})")
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context)]


def _backend_add_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 4:
        raise ValueError("usage: /config backend add <id> <base_url>")
    backend_id = args[2].strip()
    base_url = args[3].strip()
    if not backend_id or not base_url:
        raise ValueError("backend id/base_url must be non-empty")
    backends_updated = [b for b in backend_list_dicts(context=context) if b["id"] != backend_id]
    backends_updated.append(
        {
            "id": backend_id,
            "base_url": base_url,
            "model": "",
            "models": [],
            "api_key_source": "env",
            "api_key_ref": "TOAS_LLM_API_KEY",
            "tags": [],
            "notes": "",
        }
    )
    return [_result_node(f"added backend {backend_id}", step_mod=step_mod, context=context, config_update={"llm": {"backends": backends_updated}})]


def _backend_remove_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 3:
        raise ValueError("usage: /config backend remove <id>")
    backend_id = args[2].strip()
    backends_updated = [b for b in backend_list_dicts(context=context) if b["id"] != backend_id]
    return [_result_node(f"removed backend {backend_id}", step_mod=step_mod, context=context, config_update={"llm": {"backends": backends_updated}})]


def _normalize_backend_set_value(field: str, raw_value: str) -> str | list[str]:
    if field == "models":
        return [part.strip() for part in raw_value.split(",") if part.strip()]
    if field == "api_key_source":
        value = raw_value.strip().lower()
        if value not in {"env", "keyring"}:
            raise ValueError("backend api_key_source must be env|keyring")
        return value
    return raw_value


def _backend_set_result(args: list[str], *, step_mod=None, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 4:
        raise ValueError(_BACKEND_SET_USAGE)
    backend_target = args[2]
    raw_value = args[3]
    if "." not in backend_target:
        raise ValueError(_BACKEND_SET_USAGE)
    backend_id, field = backend_target.split(".", 1)
    backends_updated = backend_list_dicts(context=context)
    matched = False
    for item in backends_updated:
        if item["id"] != backend_id:
            continue
        if field not in _BACKEND_SETTABLE_FIELDS:
            raise ValueError("backend field must be one of base_url|model|api_key_source|api_key_ref|models|notes")
        item[field] = _normalize_backend_set_value(field, raw_value)
        matched = True
        break
    if not matched:
        raise ValueError(f"unknown backend id: {backend_id}")
    return [_result_node(f"updated backend {backend_id}.{field}", step_mod=step_mod, context=context, config_update={"llm": {"backends": backends_updated}})]


def _backend_capture_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 3:
        raise ValueError("usage: /config backend capture <id>")
    backend_id = args[2].strip()
    settings = step_mod.Settings.from_env()
    backends_updated = [b for b in backend_list_dicts(context=context) if b["id"] != backend_id]
    backends_updated.append(
        {
            "id": backend_id,
            "base_url": settings.llm_base_url,
            "model": settings.llm_model,
            "models": [settings.llm_model] if settings.llm_model else [],
            "api_key_source": "env",
            "api_key_ref": "TOAS_LLM_API_KEY",
            "tags": [],
            "notes": "captured from current TOAS_LLM_* runtime",
        }
    )
    return [_result_node(f"captured backend {backend_id} from current runtime", step_mod=step_mod, context=context, config_update={"llm": {"backends": backends_updated}})]


def config_backend_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) < 2:
        raise ValueError(_BACKEND_USAGE)
    sub = args[1]

    if sub == "list":
        return _backend_list_result(args, step_mod=step_mod, context=context)

    if sub == "add":
        return _backend_add_result(args, step_mod=step_mod, context=context)

    if sub == "remove":
        return _backend_remove_result(args, step_mod=step_mod, context=context)

    if sub == "set":
        return _backend_set_result(args, step_mod=step_mod, context=context)

    if sub == "capture":
        return _backend_capture_result(args, step_mod=step_mod, context=context)

    raise ValueError(_BACKEND_USAGE)
