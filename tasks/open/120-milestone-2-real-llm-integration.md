## Goal

Connect lineage-projected context to real model calls through a durable, inspectable LLM interface.

## Scope

- OpenAI-compatible provider and model abstraction
- Request construction from projected lineage context
- Response normalization into operator consequences
- Retry and failure handling
- Durable recording of model-facing operations where justified

## Why

The operator already knows how to choose a lineage and shape model-facing context, but generation is still a stub. This milestone should connect that existing projection model to a real backend without overcommitting to a broad multi-provider framework too early.

## Planned Tasks

- `121`: local OpenAI-compatible client and settings
- `122`: generation integration through lineage-projected input
- `123`: explicit failure behavior and model-call records

## Non-Goals

- No multi-provider orchestration complexity at first
- No aggressive caching before correctness and traceability

## Done When

- `step` can use a real model backend through a stable integration boundary
- Model requests are built from existing lineage projection rather than ad hoc transcript scraping
- Failures and retries are explicit enough to debug without hidden state
