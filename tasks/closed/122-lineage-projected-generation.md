## Goal

Use lineage-projected context to drive real generation during `step`.

## Scope

- Build generation requests from `project_llm_input(...)`
- Connect the generation path to the new client layer
- Normalize model output into a single assistant message consequence

## Behavior

- `step` generation uses the selected lineage view rather than scraping `session.md` directly
- Adjacent user message concatenation remains the model-facing projection rule
- Generated output becomes a normal assistant consequence

## Rules

- Generation wiring belongs at the operator boundary, not inside transcript parsing
- Context should come from existing projection helpers rather than duplicating assembly logic
- The first pass should prefer clarity over broad configurability

## Non-Goals

- No tool-intent extraction prompting yet
- No system-prompt library yet

## Done When

- A non-callable user frontier can trigger a real model call through projected lineage input
- The request shape is built from durable history plus accepted transcript state
- Tests prove generation no longer depends on ad hoc transcript-only scraping
