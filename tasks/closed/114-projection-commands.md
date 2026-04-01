## Goal

Expose transcript and history projections as practical operator commands.

## Scope

- Add CLI commands for projecting a lineage-backed transcript view
- Add CLI commands for inspecting model-facing projected input
- Decide which projection targets the active selected head by default

## Behavior

- A user can render a usable transcript view from durable history
- A user can inspect the model-facing projection without invoking generation
- The operator can target either an explicit head or the current selected head

## Rules

- Projected transcript views are convenience output, not transcript authority
- Model-facing projections must preserve always-on adjacent-user concatenation
- Projection commands must not mutate prior message history

## Non-Goals

- No editor integration beyond stdout-oriented CLI output
- No promise to reconstruct every exact user edit ever made in `session.md`

## Done When

- There is a CLI path to inspect transcript projection from history
- There is a CLI path to inspect LLM-input projection from history
- Both commands operate against explicit or selected heads without hidden sidecar state
