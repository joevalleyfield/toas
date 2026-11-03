# Direct Tool-to-Artifact Capture

Filed as: 261010-direct-tool-artifact-capture
FKA:
AKA: tool call save_as artifact; direct artifact capture; tool result to artifact
Legacy index:

keywords: runtime, tools, state, artifacts

Parent: `260926-state-step-requirements`
Related: `261009-explicit-reference-expansion-and-report-projection`, `261010-scratch-read-file-ingestion-threshold`

Status: COMPLETED; tool calls declare label and optional target to auto-populate durable state upon execution

## Context and Motivation

Persisting tool output into `state.artifacts` currently requires an awkward multi-turn ceremony:
1. Turn N: The model issues a tool call.
2. Turn N+1: The runtime executes the tool and presents the output in the single-turn ephemeral observation. The model must formulate an explicit reference string or transcribe output into `state.artifacts`.
3. Turn N+2: The content is finally accessible in state, or the model has to issue another read tool call to inspect what it couldn't capture in Turn N.

This introduces turn latency and puts bookkeeping burden on the model to track scratch paths and reference syntax. At the moment of requesting a tool, the model already knows whether it wants the result saved into durable state, what semantic role the output serves (`label`), and where it belongs (`target`).

## Design and Intent

### 1. Tool Call Affordances
Allow batch tool calls to declare:
- `label`: optional string; the model's declared snake_cased semantic intent (e.g. `"open_tasks_listing"`, `"git_diff_summary"`).
- `target`: optional string; destination path in the state tree (e.g. `"artifacts"`, `"notes.evidence"`). Defaults to `"artifacts"`.

When `label` is omitted, tool execution behaves normally (ephemeral observation only, no automatic state injection).

### 2. Runtime Execution and Identity Duality
Upon executing a tool that specifies `label`:
- The runtime executes the tool and mints a unique, immutable runtime `id` (e.g. `ib_7c3a91bf`) backed by `.toas/scratch/<id>.txt`.
- The runtime captures the artifact directly into the state tree at `target`:
  - If `target` is a list (e.g. `state.artifacts`): appends an artifact descriptor containing `label`, `id`, `path`, and content/reference.
  - If `target` is a dict: sets `state[target][label] = ...`.
  - Intermediate dot-paths are created dynamically to preserve 100% schema-agnostic state trees.
- In Turn N+1, the content is immediately available in state (or in observation) so the model can inspect, reason, or complete the task on Turn N+1 without an extra round-trip ceremony.

### 3. Prompt Instructions & Schema
- Update `default_protocol()["schema"]` tool call definitions with `label` and `target`.
- Update `instructions_v1.txt` explaining direct artifact capture via `label` on tool calls.

## Acceptance Criteria

1. **Tool Schema**: Tool call dictionaries accept optional `label` (string) and optional `target` (string).
2. **State Injection**: When `label` is provided, the runtime captures the executed tool's output into `state` at `target` (defaulting to `artifacts`) during step processing.
3. **Schema-Agnostic Tree Traversal**: Handles list targets (appends), dict targets (inserts key), and dotted paths (`a.b.c`).
4. **Immediate Visibility**: In Turn N+1, the captured artifact is present in the assembled state packet.
5. **No Interference with Normal Tool Calls**: Tool calls without `label` execute normally without modifying state.
6. **Testing and Coverage**: Unit and integration tests in `test_state_step.py` cover single and multi-turn execution with direct capture; repo-wide check script passes with 100.00% statement coverage.

## Resolution

- **Tool Schema & Validation**: Updated `_normalize_tool_call` in `src/toas/graph.py` to validate and preserve `label` and `target` as non-empty strings. Updated `default_protocol()` and `swe_v1.yaml` schema to include optional `label` and `target`.
- **Runtime Execution**: In `src/toas/runtime/state_step.py`, wired direct artifact capture into `execute_batch` (model proposed tools) and `consolidate_user` (user intent tools). Output is extracted, written to `.toas/scratch/<block_id>.txt`, minted with descriptor `{"id": block_id, "label": label, "path": rel_scratch, "ref": rel_scratch}`, and injected into state via `inject_artifact_into_state`. State modifications trigger durable `state_diff` and `state_snapshot` records and update `outcome["captured_artifact"]`.
- **Packet Assembly & Turn N+1 Immediate Visibility**: `_apply_captured_artifacts_from_records` syncs captured artifacts from log events into state packet during `build_state_step_packet`, and `_expand_compound_observation` automatically expands the scratch file into complete content on Turn N+1.
- **Verification**: Added comprehensive unit tests and multi-turn integration tests in `tests/test_state_step.py` and `tests/test_graph.py`. Full `./scripts/check.sh` passes with 100.00% statement coverage across all 160+ files (3,725 tests).
