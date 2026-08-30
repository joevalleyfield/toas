"""Potency classification for structurally scanned Markdown fences."""
from __future__ import annotations

from dataclasses import dataclass

from .markdown_fence import MarkdownFence

_LANGUAGE_ALIASES = {
    "bash": "bash",
    "json": "json",
    "powershell": "powershell",
    "python": "python",
    "sh": "bash",
    "shell": "bash",
    "sql": "sql",
    "toas-tool": "toas-tool",
    "yaml": "yaml",
}


@dataclass(frozen=True)
class FenceActivation:
    """Lane-neutral result of deciding whether a fence claims execution."""

    status: str
    language: str | None
    predicate: str
    reason: str


def classify_fence_activation(fence: MarkdownFence | None) -> FenceActivation:
    if fence is None:
        return FenceActivation("malformed", None, "structure", "no closed fence was available")

    tokens = fence.info_tokens
    if not tokens:
        return FenceActivation("inert", None, "none", "no activation marker")
    language = tokens[0].casefold()
    if language in {"inert", "toas-output"} or "inert" in {token.casefold() for token in tokens[1:]}:
        return FenceActivation("inert", language, "explicit-inert", "explicit inert fence form")
    if "exec" not in {token.casefold() for token in tokens[1:]}:
        return FenceActivation("inert", language, "none", "no activation marker")
    if len(tokens) != 2:
        return FenceActivation("unsupported", language, "explicit-exec", "activation form has extra tokens")
    canonical = _LANGUAGE_ALIASES.get(language)
    if canonical is None:
        return FenceActivation("unsupported", language, "explicit-exec", "language is not registered")
    return FenceActivation("active", canonical, "explicit-exec", "explicit exec marker")
