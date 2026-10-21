"""Discovery-to-selection affordances, retaining endpoint API identifiers."""

import shlex

from ..config import OperatorConfig


def selection_commands(endpoint) -> list[str]:
    models = tuple(dict.fromkeys(endpoint.models))
    labels = [model.rsplit("/", 1)[-1] for model in models]
    return [
        "/model select " + shlex.join([endpoint.id, label if labels.count(label) == 1 else model])
        for model, label in zip(models, labels, strict=True)
    ]


def discovered_model_selection(config: OperatorConfig, endpoint_id: str, model: str) -> dict:
    from .operator_command_config_help import _target_id_for_model

    endpoint = next((item for item in config.llm.endpoints if item.id == endpoint_id), None)
    if endpoint is None:
        raise ValueError(f"unknown endpoint: {endpoint_id}")
    matches = [item for item in dict.fromkeys(endpoint.models) if item == model or item.rsplit("/", 1)[-1] == model]
    if model in matches:
        matches = [model]
    if len(matches) != 1:
        raise ValueError(f"model is not uniquely identified in {endpoint_id}: {model}\nuse /models known {endpoint_id} for selection commands")
    model_id = matches[0]
    existing = next((item for item in config.llm.targets if item.endpoint == endpoint_id and item.model == model_id), None)
    target_id = existing.id if existing else _target_id_for_model(endpoint_id, model_id)
    base_id = target_id
    suffix = 2
    while existing is None and any(item.id == target_id for item in config.llm.targets):
        target_id = f"{base_id}-{suffix}"
        suffix += 1
    fields: dict = {"target_selection_update": {"action": "set", "target_id": target_id}}
    if existing is None:
        fields["config_update"] = {"llm": {"targets": {target_id: {"endpoint": endpoint_id, "model": model_id}}}}
    fields["content"] = f"selected model: {model_id.rsplit('/', 1)[-1]}\nendpoint: {endpoint_id}\nready: send your next message"
    return fields
