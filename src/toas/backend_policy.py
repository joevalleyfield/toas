from dataclasses import dataclass

from .config import OperatorConfig

NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}


@dataclass(frozen=True)
class BackendGenerationPolicy:
    name: str
    extra_body: dict | None
    avoid_terms: tuple[str, ...]


def default_backend_policy() -> BackendGenerationPolicy:
    # Fields for prompt-version and action-format steering were removed because they
    # were never wired to any runtime consumer; reintroduce only when prompt
    # selection is explicitly driven from config and injected into generation input.
    return BackendGenerationPolicy(
        name="openai-compatible-awkward-backend",
        extra_body=NO_THINKING,
        avoid_terms=("tool", "tool-call", "function", "function-call"),
    )


def generation_policy_from_config(config: OperatorConfig) -> BackendGenerationPolicy:
    thinking_mode = config.generation.thinking_mode
    extra_body = NO_THINKING if thinking_mode == "disabled" else None
    return BackendGenerationPolicy(
        name="openai-compatible-awkward-backend",
        extra_body=extra_body,
        avoid_terms=tuple(config.generation.avoid_terms),
    )
