## Goal

Support backend endpoints that effectively process only a single user message by adding an explicit generation transport mode that serializes projected conversation into one user-message blob.

## Why Now

A live endpoint was observed to ignore all but the final user message in `messages[]`. Under this backend shape, TOAS must explicitly package full projected context into one transaction payload to preserve turn semantics.

## Scope

- add config surface for generation transport mode:
  - `generation.transport_mode = chat_messages | single_user_blob`
- implement serializer seam in `src/toas/llm.py`:
  - `chat_messages`: current behavior
  - `single_user_blob`: collapse projected input into one `{"role": "user", "content": ...}` message
- make blob formatting explicit and stable (role-marked conversation framing), not hidden ad-hoc string glue
- include transport-mode marker in `llm_call` durability for auditability

## Intended Inputs

- generation config in `src/toas/config.py`
- policy derivation in `src/toas/backend_policy.py` (if needed)
- backend call path in `src/toas/llm.py`
- llm-call recording in `src/toas/cli.py` / `src/toas/graph.py`

## Intended Outputs

- first-class support for single-transaction endpoints
- no need for hacks that remove normal message-list usage
- tests covering mode selection and request-shape behavior

## Constraints

- preserve existing default behavior (`chat_messages`)
- do not alter durable message-event model or transcript semantics
- keep direct user intent and model-addressable capability semantics unchanged

## Non-Goals

- no provider-specific one-off codepaths beyond transport-mode seam
- no automatic backend probing/auto-switch in this task

## Done When

- operator can switch transport mode via config/env-supported path
- single-user-blob mode sends exactly one user message containing serialized projected context
- `llm_call` records include transport mode for interpretation
- tests cover both transport modes and failure/retry parity
