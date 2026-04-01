## Goal

Connect lineage-projected context to real model calls through a durable, inspectable LLM interface.

## Scope

- Provider and model abstraction
- Request construction from projected lineage context
- Response normalization into operator consequences
- Retry and failure handling
- Durable recording of model-facing operations where justified

## Non-Goals

- No multi-provider orchestration complexity at first
- No aggressive caching before correctness and traceability

## Done When

- `step` can use a real model backend through a stable integration boundary
- Model requests are built from existing lineage projection rather than ad hoc transcript scraping
- Failures and retries are explicit enough to debug without hidden state
