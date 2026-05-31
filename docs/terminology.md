# TOAS Terminology

Status: CURRENT
Normative Scope: shared vocabulary for runtime/transport/ownership discussions
Task Link: `572`

## Purpose

This glossary defines terms that are easy to rotate or conflate during architecture and refactor work.

## Core Terms

- `cli`
  - Operator command surface (`toas ...`) and argument/dispatch handling.

- `runtime`
  - Semantic execution ownership: frontier resolution, consequence execution, policy enforcement, and durable/projection behavior.

- `host`
  - Session-owned stdio transport process (for example `toas host serve`) used for persistent local interaction lanes.

- `daemon`
  - Compatibility RPC transport/service process (for example `toas daemon start|stop|status`), not the semantic owner of runtime behavior.

- `async`
  - Execution mode/lifecycle shape (`step --async`, `watch`, `cancel`) independent from transport process naming.

## Control-Surface Terms

- `session`
  - User-controlled working transcript context; often expressed as a selected transcript target.

- `surface`
  - Durable selection/binding control object that maps operator intent to a transcript target over shared graph state.

- `transcript_path`
  - Concrete file path for the working transcript content (for example `.toas/session.md`).

## Protocol/Streaming Terms

- `lane`
  - Semantic stream category (for example `events`, `stdout`, compatibility projections).

- `phase`
  - Lifecycle position within a lane sequence (for example begin/delta/end framing).

- `terminal`
  - Completion/cancellation/failure boundary after which the activity is considered final for that lane/request.

## Durable vs Presented Terms

- `record`
  - Durable append-only entry in history (`events.jsonl`), including message and non-message kinds.

- `event`
  - Generic lifecycle emission term; may be durable or transport-level depending on context.

- `projection`
  - Rendered output view (for example `RESULT` blocks) derived from durable/transport data; not itself canonical durable message history.

## Architecture Axes (Do Not Conflate)

- `ownership`
  - Which module/layer defines semantics and invariants.

- `transport`
  - How requests/events are carried (stdio, RPC, compatibility channels).

- `execution`
  - Where and how consequence work actually runs.

These three axes can point to different modules during migration periods.

## Routing/Mode Terms

- `local`
  - Execution/routing path that does not require daemon RPC.

- `rpc`
  - Execution/routing path that uses daemon RPC request handling.

- `host-attached`
  - Client flow attached to a session host process for persistent stdio-framed interaction.

## Legacy Seam Names

- Preferred: `runtime_step`
  - Use for semantic step ownership language in docs/tasks.

- Legacy seam label: `run_step_local`
  - Existing compatibility-era symbol; retain in code where needed until seam refactors land.
