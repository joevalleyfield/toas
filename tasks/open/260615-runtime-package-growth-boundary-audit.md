Filed as: 260615-runtime-package-growth-boundary-audit
FKA:
AKA: runtime package bloat; runtime god-package risk; runtime module placement audit
Legacy index:

keywords: runtime, investigation, active, architecture, boundaries, maintainability, package, module

# Runtime Package Growth Boundary Audit

## Current Reality

`src/toas/runtime/` became the natural home for code pulled out of CLI,
daemon, and step-era broad modules. That was an improvement, but the same
pressure can turn `runtime/` into a new god package if every semantic concern
lands there without a named owner.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

Runtime modules should be grouped by ownership force, not merely by the fact
that they are no longer CLI or daemon code.

Before moving more code, TOAS should know which current runtime modules belong
to:

- Operator Semantics
- Activity Lifecycle
- Session Host Supervision
- Transport And Protocol
- Effective Policy And Authority
- Model Invocation
- Model Backend Lifecycle
- Projection And Rendering
- cross-surface edge glue

## Alignment Target

This task is not a request to create new package abstractions. It is a
boundary-audit task for what already exists.

The first useful result is a map of current `runtime/` modules to architecture
domains, with only the highest-signal naming or placement follow-ups split out.

## Known Facts

- `docs/runtime-ownership.md` already warns that `runtime/` is a current home,
  not a blanket owner.
- Recent work moved policy, backend lifecycle, activity, and host behavior into
  runtime-owned modules.
- The package now contains both semantic domain modules and edge/glue modules.

## Unknowns

- Which runtime modules are named by implementation path rather than ownership
  force.
- Which modules mix multiple domains enough to block future alignment work.
- Which naming problems belong with `260614-retire-local-suffix-naming-inversion`.
- Whether any package split is worth doing now, or whether documentation and
  naming are enough.

## Evidence

Ready to leave inception when:

- a runtime module-to-domain map exists
- mixed-domain modules are named with concrete evidence
- any follow-up distinguishes alignment cleanup from speculative package design

## Audit Notes

### 2026-07-09 runtime module-to-domain map

This is a dominant-owner map for the current `src/toas/runtime/` package, not
a request to split packages immediately. Some files still touch adjacent
domains, but the list below records the primary ownership force they should be
read through.

- Operator Semantics:
  `step_runtime.py`, `step_context_runtime.py`, `step_result_runtime.py`,
  `frontier_resolution.py`, `intent_arbitration_edges.py`,
  `reconciliation_handoff.py`, `replay_queue_edges.py`
- Activity Lifecycle:
  `async_activity_store.py`, `async_activity_store_api.py`,
  `async_activity_store_impl.py`, `async_start_adapter.py`,
  `async_step_runtime_worker.py`, `cancel_latency_summary.py`,
  `event_classification.py`, `stream_pacing_summary.py`,
  `stream_subscribe_runtime.py`, `tool_stream_context.py`
- Session Host Supervision:
  `session_host_process.py`, `session_host_state.py`,
  `session_host_stream_bridge.py`
- Transport And Protocol:
  `request_contract.py`, `request_dispatch.py`,
  `request_dispatch_adapter.py`, `request_handler_assembly.py`,
  `request_handler_edges.py`, `request_handlers.py`, `rpc_edges.py`,
  `rpc_payload_edges.py`,
  `stdio_framed_transport.py`, `transport_contract.py`,
  `watch_envelope_adapter.py`, `async_lifecycle_envelope_adapter.py`
- Effective Policy And Authority:
  `policy.py`, `policy_edges.py`, `operator_config_backend_ops.py`
- Model Invocation:
  `context_assembly.py`, `step_generation_runtime.py`
- Model Backend Lifecycle:
  `model_backend_lifecycle.py`
- Projection And Rendering:
  `result_nodes.py`, `rendering_edges.py`, `presentation_edges.py`,
  `stream_presentation_edges.py`, `history_view_edges.py`,
  `diff_ancestry_view_edges.py`, `lineage_edges.py`
- Cross-surface edge glue:
  `request_ops.py`, `session_file_edges.py`, `session_step_edges.py`,
  `operator_commands.py`, `operator_command_context.py`,
  `operator_command_config_help.py`, `operator_command_extract_replay.py`,
  `operator_command_prompt_workspace.py`, `logging_bootstrap.py`

### Highest-signal mixed or misleading seams

- `request_*` cluster is semantically edge-owned but physically runtime-shaped.
  `request_dispatch.py`, `request_dispatch_adapter.py`,
  `request_handler_assembly.py`, `request_handler_edges.py`,
  `request_handlers.py`, and `request_contract.py` mostly assemble envelope
  validation, op maps, transport-safe error handling, and CLI capture wrappers.
  They are useful modules, but their current placement makes it easy to read
  them as semantic runtime ownership rather than protocol/adapter glue.
- `step_generation_runtime.py` mixes owning-domain work with surface-adapter
  work. It coordinates model invocation and step-time generation, but it also
  wires CLI capture helpers, stdout rendering, transcript newline handling, and
  output presentation dependencies through `StepCliDeps`. That combination is a
  likely future token sink because a caller cannot tell quickly whether the file
  is "generation semantics" or "CLI-orchestrated generation glue."
- `session_step_edges.py` is intentionally named as glue, but it is a dense
  convergence point for durable graph writes, session mutation, config updates,
  shell-scope updates, lens updates, and transcript-side effects. The name is
  accurate enough for now, but the file should be treated as a boundary hotspot
  rather than a safe generic home for more session-ish behavior.
- `operator_command_prompt_workspace.py` is large enough to hide multiple
  concerns under a command-family umbrella. That may still be the right current
  home, but at over 1,000 lines it is now a good candidate for future
  sub-splitting by ownership force rather than by slash-command spelling.

### Decision

- No package split is justified yet just from the current module inventory.
- The highest-value near-term gain is naming and documentation truth:
  future contributors should be able to see that large parts of
  `src/toas/runtime/` are protocol/adapter glue, not semantic runtime owners.
- The next follow-ons should stay narrow: move only when a file is causing
  repeated ambiguity or when a concrete behavior change needs a clearer owner.

### Recommended follow-ons

- Open or reuse a narrow follow-on for the `request_*` cluster if future work
  keeps paying a context tax around whether request dispatch belongs to
  Transport And Protocol or to semantic runtime ownership.
- Treat `step_generation_runtime.py` as the highest-leverage candidate for
  future boundary cleanup. A small split between generation semantics and
  CLI-facing orchestration/presentation glue would likely reduce future token
  cost more than a broader package shuffle.
- Treat `session_step_edges.py` and `operator_command_prompt_workspace.py` as
  "watchlist" files: not immediate refactor targets, but files where new work
  should justify itself carefully instead of accreting by convenience.

### 2026-07-10 follow-through note

- Opened `260710-step-generation-domain-boundary-contract` to turn the
  `step_generation_runtime.py` service-locator smell into an explicit
  architecture follow-on before further implementation churn.
- The immediate question is no longer "can `StepCliDeps` get smaller?" but
  "which domains should own step-time generation workflow, policy resolution,
  projection, and session side effects?"
