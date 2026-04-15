## Goal

Increase coverage for `llm.py` by testing high-risk stream normalization and reasoning/progress extraction paths that have shown real-world variance.

## Why Now

`llm.py` remains a major reliability seam (~72% coverage) and provider-dependent chunk shapes continue to produce edge behavior.

## Scope

- add tests for stream chunk normalization across expected provider variants
- add tests for reasoning/prompt-progress extraction gates and fallback behavior
- add tests for error and timeout shaping in stream and non-stream calls
- perform small refactors to isolate pure helpers where needed for testability

## Intended Behavior

- chunk/stream handling is deterministic across known payload shapes
- regressions in reasoning/progress projection are caught early

## Constraints

- preserve current API/request semantics and durable `llm_call` contracts
- no backend policy redesign in this slice

## Done When

- new tests cover targeted stream/normalization/error seams in `llm.py`
- coverage rises and known shape regressions are represented by tests
