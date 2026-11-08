"""Declarative operator command registry and descriptor contracts."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext


@dataclass(frozen=True)
class OperatorCommandDescriptor:
    """Declarative specification of an operator command."""

    name: str
    summary: str = ""
    usage: str = ""
    category: str = "general"
    handler: Callable[[list[str], OperatorCommandContext, Any], Any] = field(default=None)  # type: ignore[assignment]
    aliases: tuple[str, ...] = ()
    source: str = ""
    fenced: bool = False
    help_handler: Callable[[OperatorCommandContext, Any], Any] | None = None


def build_command_result_node(
    content: str,
    *,
    context: OperatorCommandContext,
    source: str = "command.operator",
    fenced: bool = False,
    **fields: Any,
) -> dict:
    """Create a standardized operator command result node with optional fenced view formatting."""
    if fenced and "\n" in content:
        from ..tools_cluster.rendering import render_fenced_output

        content = render_fenced_output(
            content=content,
            kind="view",
            source=source,
            potency="inert",
        )
    from .result_nodes import make_result_node

    return make_result_node(
        content,
        origin_role=context.frontier_role,
        origin_kind="slash_command",
        **fields,
    )


class OperatorCommandRegistry:
    """Registry managing declarative operator command descriptors and unified dispatch."""

    def __init__(self) -> None:
        self._descriptors_by_name: dict[str, OperatorCommandDescriptor] = {}
        self._name_by_alias: dict[str, str] = {}

    def register(self, descriptor: OperatorCommandDescriptor) -> None:
        """Register a command descriptor under its primary name and aliases."""
        if not descriptor.name:
            raise ValueError("command descriptor name cannot be empty")
        self._descriptors_by_name[descriptor.name] = descriptor
        for alias in descriptor.aliases:
            self._name_by_alias[alias] = descriptor.name

    def unregister(self, name: str) -> None:
        """Unregister a command descriptor."""
        descriptor = self._descriptors_by_name.pop(name, None)
        if descriptor:
            for alias in descriptor.aliases:
                self._name_by_alias.pop(alias, None)

    def get(self, name_or_alias: str) -> OperatorCommandDescriptor | None:
        """Look up a command descriptor by primary name or registered alias."""
        canonical_name = self._name_by_alias.get(name_or_alias, name_or_alias)
        return self._descriptors_by_name.get(canonical_name)

    def has_command(self, name_or_alias: str) -> bool:
        """Check whether a command name or alias is registered."""
        return self.get(name_or_alias) is not None

    def list_descriptors(self) -> tuple[OperatorCommandDescriptor, ...]:
        """Return all registered command descriptors."""
        return tuple(self._descriptors_by_name.values())

    def dispatch(
        self,
        command: str,
        args: list[str],
        *,
        context: OperatorCommandContext,
        step_mod: Any,
    ) -> list[dict] | None:
        """Dispatch a command if registered, intercepting help and wrapping results."""
        descriptor = self.get(command)
        if descriptor is None:
            return None

        source = descriptor.source or (f"command.{descriptor.name}" if descriptor.fenced else "command.operator")
        fenced = descriptor.fenced

        from ..assets.presentation_loader import (
            reset_active_presentation_context,
            set_active_presentation_context,
        )

        token = set_active_presentation_context(
            workspace_roots=tuple(context.workspace_roots),
            command_cwd=context.command_cwd,
        )
        try:
            # Automatic help interception
            if args in (["--help"], ["-h"]):
                if descriptor.help_handler is not None:
                    res = descriptor.help_handler(context, step_mod)
                    return self._coerce_result(res, context=context, source=source, fenced=fenced)
                if descriptor.usage:
                    return [build_command_result_node(descriptor.usage, context=context, source=source, fenced=fenced)]

            if descriptor.handler is None:
                return None

            result = descriptor.handler(args, context, step_mod)
            return self._coerce_result(result, context=context, source=source, fenced=fenced)
        finally:
            reset_active_presentation_context(token)

    def _coerce_result(
        self,
        result: Any,
        *,
        context: OperatorCommandContext,
        source: str,
        fenced: bool,
    ) -> list[dict]:
        """Coerce raw handler returns (string, dict, or list of dicts) into standard result nodes."""
        if isinstance(result, str):
            return [build_command_result_node(result, context=context, source=source, fenced=fenced)]
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], dict):
            content, extra = result
            return [build_command_result_node(content, context=context, source=source, fenced=fenced, **extra)]
        if isinstance(result, dict):
            return [result]
        if isinstance(result, list):
            return result
        raise TypeError(f"unexpected command handler result type: {type(result).__name__}")


_DEFAULT_REGISTRY: OperatorCommandRegistry | None = None


def _handle_step_command(args: list[str], context: OperatorCommandContext, step_mod: Any) -> str:
    if args and (not args[0].isdigit() or int(args[0]) <= 0):
        return "usage: /step [N]"
    count = int(args[0]) if args else 1
    return f"[STEP] budget: {count}"


def _register_builtin_descriptors(registry: OperatorCommandRegistry) -> None:
    """Register core built-in operator commands."""
    from ..skills import handle_skills_commands
    from .operator_command_config_help import (
        _CONFIG_USAGE,
        _handle_config_command,
        _handle_help_command,
    )
    from .operator_command_intent import get_intent_command_descriptors
    from .operator_command_lens import get_lens_command_descriptors
    from .operator_command_models import get_models_command_descriptors
    from .operator_command_prompts import get_prompts_command_descriptors
    from .operator_command_replay import get_replay_command_descriptors
    from .operator_command_shell import get_shell_command_descriptors
    from .operator_command_transcript import get_transcript_command_descriptors
    from .operator_command_workspace import get_workspace_command_descriptors
    from .source_reference_operations import handle_source_reference_commands

    core_descriptors = (
        OperatorCommandDescriptor("config", "Inspect or update operator configuration", _CONFIG_USAGE, "configuration", lambda args, context, step_mod: _handle_config_command(args, step_mod=step_mod, context=context), source="command.config", fenced=True, help_handler=lambda context, step_mod: step_mod.render_help_config()),
        OperatorCommandDescriptor("help", "Display session help or topic documentation", "usage: /help [topic]", "help", lambda args, context, step_mod: _handle_help_command(args, step_mod=step_mod, context=context), source="command.help", fenced=True),
        OperatorCommandDescriptor("run", "Execute selected assistant plan or operations", "usage: /run [pN|pN..|pN.oM|pN.oM..|oM|oM..]", "execution", lambda args, context, step_mod: handle_source_reference_commands("run", args, step_mod=step_mod, context=context)),
        OperatorCommandDescriptor("stage", "Stage selected assistant plan as next user message", "usage: /stage [pN|pN..|pN.oM|pN.oM..|oM|oM..]", "execution", lambda args, context, step_mod: handle_source_reference_commands("stage", args, step_mod=step_mod, context=context)),
        OperatorCommandDescriptor("skills", "List available agent skills", "usage: /skills", "skills", lambda args, context, step_mod: handle_skills_commands("skills", args, step_mod=step_mod, context=context)),
        OperatorCommandDescriptor("skill", "Inspect or activate a skill", "usage: /skill <name>", "skills", lambda args, context, step_mod: handle_skills_commands("skill", args, step_mod=step_mod, context=context)),
        OperatorCommandDescriptor("specialize", "Specialize a skill for current workspace", "usage: /specialize <name>", "skills", lambda args, context, step_mod: handle_skills_commands("specialize", args, step_mod=step_mod, context=context)),
        OperatorCommandDescriptor("step", "Advance execution budget", "usage: /step [N]", "execution", _handle_step_command),
    )
    providers = (
        lambda: core_descriptors,
        get_models_command_descriptors,
        get_shell_command_descriptors,
        get_workspace_command_descriptors,
        get_prompts_command_descriptors,
        get_lens_command_descriptors,
        get_intent_command_descriptors,
        get_transcript_command_descriptors,
        get_replay_command_descriptors,
    )
    for provider in providers:
        for descriptor in provider():
            registry.register(descriptor)


def get_default_operator_command_registry() -> OperatorCommandRegistry:
    """Retrieve or initialize the global default operator command registry."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = OperatorCommandRegistry()
        _register_builtin_descriptors(_DEFAULT_REGISTRY)
    return _DEFAULT_REGISTRY


def reset_default_operator_command_registry() -> None:
    """Reset the default registry (primarily for isolated test fixtures)."""
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = None
