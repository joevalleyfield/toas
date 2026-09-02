"""Lossless source-form adapters for retry materialization."""
from __future__ import annotations

from dataclasses import dataclass

from .fence_activation import classify_fence_activation
from .markdown_fence import fence_attributes, scan_markdown_fences


@dataclass(frozen=True)
class RetryMaterialization:
    """A source-preserving retry projection or an explicit refusal."""

    content: str | None
    reason: str | None = None


def materialize_executable_fence_timeout(*, content: str, opening_offset: int, timeout_s: int) -> RetryMaterialization:
    """Patch one active executable fence header without touching its body."""
    if not isinstance(timeout_s, int) or timeout_s <= 0:
        return RetryMaterialization(None, "timeout must be a positive integer")
    fence = next((item for item in scan_markdown_fences(content) if item.opening_offset == opening_offset), None)
    if fence is None:
        return RetryMaterialization(None, "source fence is unavailable")
    activation = classify_fence_activation(fence)
    if activation.status != "active":
        return RetryMaterialization(None, "source fence is not executable")
    if activation.language in {"json", "yaml"}:
        return RetryMaterialization(None, "source fence has no header timeout contract")
    attributes = fence_attributes(fence)
    if attributes is None:
        return RetryMaterialization(None, "source fence attributes are malformed")
    matching = [attribute for attribute in attributes if attribute.name == "timeout_s"]
    if len(matching) > 1:
        return RetryMaterialization(None, "source fence repeats timeout_s")
    if matching:
        attribute = matching[0]
        patched = content[: attribute.value_start] + str(timeout_s) + content[attribute.value_end :]
    else:
        patched = content[: fence.opening_line_end] + f" timeout_s={timeout_s}" + content[fence.opening_line_end :]
    patched_fence = next((item for item in scan_markdown_fences(patched) if item.opening_offset == opening_offset), None)
    if patched_fence is None or classify_fence_activation(patched_fence).status != "active":
        return RetryMaterialization(None, "patched fence is not executable")
    return RetryMaterialization(patched)
