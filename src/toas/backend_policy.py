from dataclasses import dataclass

from .config import OperatorConfig
from .llm import NO_THINKING


@dataclass(frozen=True)
class BackendGenerationPolicy:
    name: str
    extra_body: dict | None
    max_tokens: int | None
    avoid_terms: tuple[str, ...]


def default_backend_policy() -> BackendGenerationPolicy:
    # Fields for prompt-version and action-format steering were removed because they
    # were never wired to any runtime consumer; reintroduce only when prompt
    # selection is explicitly driven from config and injected into generation input.
    return BackendGenerationPolicy(
        name="openai-compatible-awkward-backend",
        extra_body=NO_THINKING,
        max_tokens=None,
        avoid_terms=("tool", "tool-call", "function", "function-call"),
    )


def generation_policy_from_config(config: OperatorConfig) -> BackendGenerationPolicy:
    thinking_mode = config.generation.thinking_mode
    thinking_budget_tokens = config.generation.thinking_budget_tokens
    max_tokens = config.generation.max_tokens or None
    if thinking_mode == "disabled":
        extra_body = NO_THINKING
    elif thinking_budget_tokens > 0:
        extra_body = {"thinking": {"budget_tokens": thinking_budget_tokens}}
    else:
        extra_body = None
    return BackendGenerationPolicy(
        name="openai-compatible-awkward-backend",
        extra_body=extra_body,
        max_tokens=max_tokens,
        avoid_terms=tuple(config.generation.avoid_terms),
    )
