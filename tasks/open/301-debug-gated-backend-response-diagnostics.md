## Goal

Add debug-gated backend response diagnostics for malformed or empty completion responses without altering normal request semantics or leaking verbose payloads by default.

## Why Now

Live backend integration required deeper visibility when responses did not match expected shape. Ad-hoc exception-body dumping proved useful for debugging but is the wrong default behavior.

## Scope

- keep canonical request path unchanged (`messages` + optional `extra_body`)
- improve parse-failure error path to include concise structured context by default
- add gated verbose diagnostics under explicit debug/trace control (e.g., existing `llm_trace=full` or new explicit flag)
- ensure `llm_call` durability captures enough context to debug without forcing raw full payload logging in minimal mode

## Intended Inputs

- backend call and response normalization in `src/toas/llm.py`
- llm-call durability in `src/toas/graph.py` and callsites in `src/toas/cli.py`

## Intended Outputs

- safer default errors with actionable context
- optional deep diagnostics mode for backend debugging
- tests for minimal vs debug-gated diagnostic behavior

## Constraints

- no request-shape semantic changes in this task
- avoid leaking sensitive/raw payloads in minimal/default mode
- preserve retry error classification behavior

## Non-Goals

- no new transport mode in this task
- no provider-specific parser branches beyond current seams

## Done When

- malformed/empty completion failures include actionable summary context
- verbose raw diagnostics are only present under explicit debug/trace mode
- tests assert both default and debug-gated behavior
