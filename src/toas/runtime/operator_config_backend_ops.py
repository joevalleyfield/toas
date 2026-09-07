"""Temporary user-facing compatibility for the retired endpoint command name."""

from __future__ import annotations

from .operator_command_context import OperatorCommandContext
from .operator_config_endpoint_ops import config_endpoint_result


def config_backend_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    """Translate the legacy command spelling at the public boundary only."""
    translated = ["endpoint", *args[1:]]
    try:
        result = config_endpoint_result(translated, step_mod=step_mod, context=context)
    except ValueError as exc:
        raise ValueError(str(exc).replace("endpoint", "backend").replace("Endpoint", "Backend").replace("default_model", "model")) from exc
    for node in result:
        if isinstance(node.get("content"), str):
            node["content"] = node["content"].replace("endpoint", "backend").replace("Endpoint", "Backend").replace("default_model", "model")
    return result
