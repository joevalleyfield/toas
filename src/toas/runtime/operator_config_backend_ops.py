from __future__ import annotations

from .operator_command_context import OperatorCommandContext


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


def config_backend_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) < 2:
        raise ValueError("usage: /config backend [list|add|set|remove|capture] ...")
    sub = args[1]

    if sub == "list":
        if len(args) != 2:
            raise ValueError("usage: /config backend list")
        if not context.config.llm.backends:
            return [{"role": "result", "content": "no configured backends"}]
        lines = ["configured backends:"]
        for backend in context.config.llm.backends:
            lines.append(f"- {backend.id}: {backend.base_url} (model={backend.model or '-'})")
        return [{"role": "result", "content": "\n".join(lines)}]

    if sub == "add":
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
        return [
            {
                "role": "result",
                "content": f"added backend {backend_id}",
                "config_update": {"llm": {"backends": backends_updated}},
            }
        ]

    if sub == "remove":
        if len(args) != 3:
            raise ValueError("usage: /config backend remove <id>")
        backend_id = args[2].strip()
        backends_updated = [b for b in backend_list_dicts(context=context) if b["id"] != backend_id]
        return [
            {
                "role": "result",
                "content": f"removed backend {backend_id}",
                "config_update": {"llm": {"backends": backends_updated}},
            }
        ]

    if sub == "set":
        if len(args) != 4:
            raise ValueError("usage: /config backend set <id>.<field> <value>")
        backend_target = args[2]
        raw_value = args[3]
        if "." not in backend_target:
            raise ValueError("usage: /config backend set <id>.<field> <value>")
        backend_id, field = backend_target.split(".", 1)
        backends_updated = backend_list_dicts(context=context)
        matched = False
        for item in backends_updated:
            if item["id"] != backend_id:
                continue
            if field not in {"base_url", "model", "api_key_source", "api_key_ref", "models", "notes"}:
                raise ValueError(
                    "backend field must be one of base_url|model|api_key_source|api_key_ref|models|notes"
                )
            if field == "models":
                item[field] = [part.strip() for part in raw_value.split(",") if part.strip()]
            elif field == "api_key_source":
                value = raw_value.strip().lower()
                if value not in {"env", "keyring"}:
                    raise ValueError("backend api_key_source must be env|keyring")
                item[field] = value
            else:
                item[field] = raw_value
            matched = True
            break
        if not matched:
            raise ValueError(f"unknown backend id: {backend_id}")
        return [
            {
                "role": "result",
                "content": f"updated backend {backend_id}.{field}",
                "config_update": {"llm": {"backends": backends_updated}},
            }
        ]

    if sub == "capture":
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
        return [
            {
                "role": "result",
                "content": f"captured backend {backend_id} from current runtime",
                "config_update": {"llm": {"backends": backends_updated}},
            }
        ]

    raise ValueError("usage: /config backend [list|add|set|remove|capture] ...")
