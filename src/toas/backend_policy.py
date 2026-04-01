from dataclasses import dataclass

from .llm import NO_THINKING


@dataclass(frozen=True)
class BackendGenerationPolicy:
    name: str
    extra_body: dict | None
    preferred_action_formats: tuple[str, ...]
    avoid_terms: tuple[str, ...]
    protocol_prompt_version: str
    entrainment_prompt_version: str


def default_backend_policy() -> BackendGenerationPolicy:
    return BackendGenerationPolicy(
        name="openai-compatible-awkward-backend",
        extra_body=NO_THINKING,
        preferred_action_formats=("yaml_action_block", "json_action_object"),
        avoid_terms=("tool", "tool-call", "function", "function-call"),
        protocol_prompt_version="terse_v1",
        entrainment_prompt_version="entrain_v1",
    )
