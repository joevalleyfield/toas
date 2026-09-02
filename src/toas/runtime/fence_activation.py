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
    toolset: str | None = None


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
    attributes = tokens[2:]
    parsed_attributes: dict[str, str] = {}
    toolset = None
    if attributes:
        if any("=" not in attribute for attribute in attributes):
            return FenceActivation("unsupported", language, "explicit-exec", "activation form has extra tokens")
        parsed_attributes = dict(attribute.split("=", 1) for attribute in attributes)
        if len(parsed_attributes) != len(attributes):
            return FenceActivation("unsupported", language, "explicit-exec", "activation form repeats an attribute")
        unknown_attributes = set(parsed_attributes) - {"toolset", "runtime", "cwd", "persist", "path", "overwrite", "timeout_s"}
        if unknown_attributes:
            return FenceActivation("unsupported", language, "explicit-exec", "activation form has unknown attributes")
        toolset = parsed_attributes.get("toolset")
        if "toolset" in parsed_attributes and not toolset:
            return FenceActivation("unsupported", language, "explicit-exec", "toolset value is empty")
    canonical = _LANGUAGE_ALIASES.get(language)
    if canonical is None:
        if toolset is None and parsed_attributes.get("runtime"):
            return FenceActivation("active", language, "explicit-runtime", "unregistered language with explicit runtime")
        return FenceActivation("unsupported", language, "explicit-exec", "language is not registered")
    if canonical in {"yaml", "json"} and toolset not in {None, "toas"}:
        return FenceActivation("unsupported", canonical, "explicit-exec", "toolset is not registered")
    return FenceActivation("active", canonical, "explicit-exec", "explicit exec marker", toolset or ("toas" if canonical in {"yaml", "json"} else None))
