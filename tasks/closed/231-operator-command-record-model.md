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

## Detailed Implementation Plan

### 1. Storage Layer (`src/toas/graph.py`)
- **Add `write_command_request_record(path, command, args, related_to)`**:
    - `kind`: `"command_request"`
    - `related_to`: optional ID of the nearest triggering message when one exists.
    - `payload`: include:
      - `{ "command": command, "args": args }`
      - explicit target fields as applicable (`head_id`, `message_id`, `range`)
- **Add `write_command_result_record(path, request_id, ok, content, context_update=None)`**:
    - `kind`: `"command_result"`
    - `related_to`: ID of the `command_request` record.
    - `payload`: `{ "ok": ok, "content": content, "context_update": context_update, "workspace_update": workspace_update, ... }`
- **Update `summarize_event`**: Add human-readable summaries for these two new kinds.

### 2. Execution Logic (`src/toas/step.py`)
- **Keep `step` return shape stable**:
    - do not change `step` return type for command-record transport.
    - command request/result durability is orchestrated in CLI around existing append/result flow.

### 3. Orchestration Loop (`src/toas/cli.py`)
- **Update `run_step_local`**:
    - Capture command execution context from frontier and projected command/result nodes.
    - When an operator command is executed:
        1. Call `write_command_request_record` with explicit target fields and optional `related_to`.
        2. Execute the command.
        3. Call `write_command_result_record` using the request record's ID, including any `context_update` / `workspace_update`.
        4. Preserve current context persistence logic while making command result payload replay-complete.

## Invariants to Preserve
- Command records must never be inserted into the `_lineage` projection.
- All command results must be linked to a request.
- Request linkage must be explicit in payload targeting fields even when `related_to` is absent.
