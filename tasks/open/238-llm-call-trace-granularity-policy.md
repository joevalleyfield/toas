## Goal

Define and implement an explicit `llm_call` trace granularity policy that preserves debuggability while avoiding default quadratic log growth.

## Scope

- define runtime modes for `llm_call` durability (for example: minimal vs full trace)
- keep minimal mode as default for normal operation
- make full request/response trace an explicit opt-in for forensic sessions
- document exactly which fields are recorded in each mode

## Intended Inputs

- current `llm_call` record shape and write path
- closed task goals from model-failure/normalization work (`123`, `173`)
- current operator expectations around durable debugging facts

## Intended Outputs

- explicit policy in docs and runtime
- configurable trace mode switch
- tests validating per-mode `llm_call` payload shape

## Constraints

- preserve deterministic failure observability in all modes
- avoid silent mode-dependent behavioral differences in transcript-visible output
- keep model-call records distinct from message events

## Non-Goals

- no provider-agnostic tracing framework
- no full telemetry pipeline

## Done When

- default mode avoids redundant full-input snapshots
- opt-in mode captures full forensic payload when explicitly enabled
- storage/observability tradeoff is explicit and test-covered
