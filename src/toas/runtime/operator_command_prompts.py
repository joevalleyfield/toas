"""Operator commands for prompt browsing and rendering."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .operator_command_registry import OperatorCommandDescriptor

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext


def handle_prompts_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> tuple[str, dict]:
    """Execute /prompts operator command."""
    if len(args) > 1:
        raise ValueError("usage: /prompts [prefix]")
    content = step_mod._render_prompt_browse_commands(args[0] if args else None)
    return content, {"transcript_inert": False}


def handle_prompt_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> tuple[str, dict]:
    """Execute /prompt operator command."""
    if not args:
        return step_mod._render_prompt_browse_commands(None), {"transcript_inert": False}
    ref_or_prefix = args[0]
    mode = context.config.prompt.mode
    constraints: list[str] = list(context.config.prompt.constraints)
    i = 1
    while i < len(args):
        token = args[i]
        if token == "--mode":
            if i + 1 >= len(args):
                raise ValueError("usage: /prompt [ref_or_prefix] [--mode <direct|mimic>] [--constraint <name> ...]")
            mode = args[i + 1]
            i += 2
            continue
        if token == "--constraint":
            if i + 1 >= len(args):
                raise ValueError("usage: /prompt [ref_or_prefix] [--mode <direct|mimic>] [--constraint <name> ...]")
            constraints.append(args[i + 1])
            i += 2
            continue
        raise ValueError("usage: /prompt [ref_or_prefix] [--mode <direct|mimic>] [--constraint <name> ...]")
    exact = None
    try:
        exact = step_mod.load_prompt_ref(
            ref_or_prefix,
            mode=mode,
            constraints=constraints or None,
            policy=step_mod.generation_policy_from_config(context.config),
            capability_profile=context.config.capability_advertisement.profile,
            capability_hidden_tools=context.config.capability_advertisement.hidden_tools,
            prompt_ingress=context.config.prompt.ingress,
            prompt_output_profile=context.config.prompt.output_profile,
        )
    except RuntimeError:
        exact = None
    if exact is not None:
        if exact.startswith("## TOAS:STATE"):
            return exact, {"transcript_render": "raw_turn", "transcript_inert": False}
        frontier_role = context.working[-1]["role"] if context.working else "user"
        if frontier_role == "control":
            return f"## TOAS:USER\n\n{exact}", {"transcript_render": "raw"}
        rendered_then_user = f"{exact}\n\n## TOAS:USER\n\n"
        return rendered_then_user, {"transcript_render": "raw", "transcript_inert": False}
    content = step_mod._render_prompt_browse_commands(ref_or_prefix)
    if not content:
        raise ValueError(f"unknown prompt ref or prefix: {ref_or_prefix}")
    return content, {"transcript_inert": False}


def get_prompts_command_descriptors() -> tuple[OperatorCommandDescriptor, ...]:
    """Return descriptors for prompt browsing and rendering."""
    return (
        OperatorCommandDescriptor("prompts", "compat alias for /prompt", "usage: /prompts [prefix]", "transcript", handle_prompts_command),
        OperatorCommandDescriptor("prompt", "browse or render prompt assets", "usage: /prompt [ref_or_prefix] [--mode <direct|mimic>] [--constraint <name> ...]", "transcript", handle_prompt_command),
    )
