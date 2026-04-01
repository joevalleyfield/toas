## Goal

Make TOAS resilient to backend-imposed personas, hidden system prompts, and provider-native tool semantics by treating protocol collision avoidance as first-class runtime work.

## Scope

- identify action syntaxes that collide less with backend-native tool behavior
- test terminology and framing choices that avoid activating provider-owned protocols
- turn those findings into durable prompt/runtime policy

## Planned Tasks

- `181`: action syntax and trigger-vocabulary probes
- `182`: entrainment-backed prompt variants
- `183`: backend-adaptive generation policy

## Why

The core challenge is not just "structured output quality." It is establishing a controllable TOAS action lane when the backend already has its own system prompt, persona, and tool protocol.

## Done When

- TOAS has a documented strategy for protocol collision avoidance
- prompt/runtime choices reflect observed backend behavior
- later extraction/repair work can build on a clearer action lane
