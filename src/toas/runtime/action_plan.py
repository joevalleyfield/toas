"""Inert plan-level context around normalized tool requests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolRequest:
    """One normalized capability request offered to the execution path."""

    capability: str
    arguments: dict[str, Any]
    stated_intention: str | None = None

    def as_dict(self) -> dict[str, Any]:
        request = {"tool_name": self.capability, "args": dict(self.arguments)}
        if self.stated_intention is not None:
            request["intention"] = self.stated_intention
        return request


@dataclass(frozen=True)
class ActionPlan:
    """One recognized plan and its plan-level provenance context."""

    requests: tuple[ToolRequest, ...]
    origin: str | None = None
    ingress: str | None = None
    source: str | None = None
    plan_position: int | None = None
    selection_id: str | None = None
    toolset: str | None = None

    @classmethod
    def from_normalized_plan(
        cls,
        plan: list[dict],
        *,
        origin: str | None = None,
        ingress: str | None = None,
        source: str | None = None,
        plan_position: int | None = None,
        selection_id: str | None = None,
        toolset: str | None = None,
    ) -> ActionPlan:
        requests = tuple(
            ToolRequest(
                capability=str(request["tool_name"]),
                arguments=dict(request.get("args", {})),
                stated_intention=request.get("intention"),
            )
            for request in plan
        )
        return cls(
            requests=requests,
            origin=origin,
            ingress=ingress,
            source=source,
            plan_position=plan_position,
            selection_id=selection_id,
            toolset=toolset,
        )

    def as_normalized_plan(self) -> list[dict[str, Any]]:
        """Return the incumbent list shape for existing execution/storage code."""
        return [request.as_dict() for request in self.requests]
