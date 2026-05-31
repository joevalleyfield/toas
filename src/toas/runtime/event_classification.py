from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventPolicy:
    kind: str
    durable: bool
    projected: bool
    ephemeral: bool
    terminal: bool


_EVENT_POLICIES: dict[str, EventPolicy] = {
    "request": EventPolicy("request", durable=True, projected=False, ephemeral=False, terminal=False),
    "accepted": EventPolicy("accepted", durable=False, projected=False, ephemeral=True, terminal=False),
    "progress": EventPolicy("progress", durable=False, projected=False, ephemeral=True, terminal=False),
    "stdout": EventPolicy("stdout", durable=False, projected=True, ephemeral=False, terminal=False),
    "stderr": EventPolicy("stderr", durable=False, projected=True, ephemeral=False, terminal=False),
    "telemetry": EventPolicy("telemetry", durable=False, projected=False, ephemeral=True, terminal=False),
    "warning": EventPolicy("warning", durable=False, projected=True, ephemeral=False, terminal=False),
    "status": EventPolicy("status", durable=False, projected=False, ephemeral=True, terminal=False),
    "result": EventPolicy("result", durable=True, projected=True, ephemeral=False, terminal=True),
    "error": EventPolicy("error", durable=True, projected=True, ephemeral=False, terminal=True),
    "cancel": EventPolicy("cancel", durable=True, projected=False, ephemeral=False, terminal=False),
    "cancelled": EventPolicy("cancelled", durable=True, projected=True, ephemeral=False, terminal=True),
    "heartbeat": EventPolicy("heartbeat", durable=False, projected=False, ephemeral=True, terminal=False),
    "capability": EventPolicy("capability", durable=False, projected=False, ephemeral=True, terminal=False),
    # Existing daemon streaming event kinds.
    "llm_delta": EventPolicy("llm_delta", durable=False, projected=True, ephemeral=False, terminal=False),
    "llm_reasoning": EventPolicy("llm_reasoning", durable=False, projected=True, ephemeral=False, terminal=False),
    "prompt_progress": EventPolicy("prompt_progress", durable=False, projected=False, ephemeral=True, terminal=False),
    "tool_progress": EventPolicy("tool_progress", durable=False, projected=True, ephemeral=False, terminal=False),
    "tool_done": EventPolicy("tool_done", durable=False, projected=True, ephemeral=False, terminal=False),
    "projection_delta": EventPolicy("projection_delta", durable=False, projected=True, ephemeral=False, terminal=False),
    "projection_done": EventPolicy("projection_done", durable=False, projected=True, ephemeral=False, terminal=False),
    "run_done": EventPolicy("run_done", durable=True, projected=True, ephemeral=False, terminal=True),
    # Existing daemon stream event shape; treated as terminal projected outcome.
    "llm_done": EventPolicy("llm_done", durable=True, projected=True, ephemeral=False, terminal=True),
}


def event_policy(kind: str) -> EventPolicy:
    normalized = str(kind).strip().lower()
    policy = _EVENT_POLICIES.get(normalized)
    if policy is None:
        raise ValueError(f"unknown event kind: {kind}")
    return policy


def should_persist_event(kind: str) -> bool:
    return event_policy(kind).durable


def should_project_event(kind: str) -> bool:
    return event_policy(kind).projected


def is_ephemeral_event(kind: str) -> bool:
    return event_policy(kind).ephemeral


def is_terminal_event(kind: str, *, final_flag: bool = False) -> bool:
    return final_flag or event_policy(kind).terminal
