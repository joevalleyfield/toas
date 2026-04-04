## Goal

Define the durable record model for operator commands, including request/result pairing and message-space targeting metadata.

## Scope

- introduce durable record kinds for command request and command result
- define linkage fields to head/message/range targets
- define status/error/artifact fields needed for replay and debugging
- specify invariants that preserve message-event lineage separation

## Intended Inputs

- existing tool and model-call record patterns
- current lineage/head/jump semantics
- roadmap direction for operator commands as non-message records

## Intended Outputs

- record schema and invariants documented in code/docs
- append/read helpers in storage layer
- tests validating append shape and lineage isolation

## Constraints

- no command record may become a message parent
- no hidden mutable sidecar state
- link fields must be explicit and durable

## Non-Goals

- no command parser or CLI execution path yet
- no command-specific behavior implementation yet

## Done When

- request/result record shapes are stable and documented
- records can reference message-space targets without parentage coupling
- replay can attribute outcomes to command requests deterministically
