# TOAS Architecture Masterplan

Status: DIRECTIONAL
Normative Scope: draft target architecture for critique and sequencing
Task Link: `260614-toas-architecture-masterplan-draft`
Related: `400`, `525`, `675`, `260614-runtime-owned-backend-lifecycle-architecture`

## Purpose

This document is a proposal, not settled doctrine.

It sketches the architecture TOAS should move toward after the CLI and daemon
decomposition work. Its main job is to prevent the next failure mode: replacing
an overgrown CLI or daemon with an overgrown `runtime/` package.

The intended critique questions are:

- Are the proposed domains real, or are they just nicer names?
- Does each domain have a clear source of truth?
- Where should dependency injection cross boundaries, and where is it hiding
  missing ownership?
- Which pieces should remain compatibility adapters rather than become owners?

## North Star

TOAS is a durable transcript/event substrate with live runtime hosts around it.

It is not primarily:

- a CLI
- a daemon
- an autonomous agent loop
- a single runtime package that owns everything

The product shape is:

```text
user/editor/shell
  edits or selects transcript surface
    -> runtime host resolves one consequence layer
      -> durable event graph records facts
      -> projections/renderers expose readable state
      -> tools/model/backend workers do bounded work
```

The core invariant remains:

> `toas step` accepts transcript state, synchronizes it into durable history,
> and resolves one layer of consequence.

Everything else should support that substrate without hiding ownership behind
ambient service state.

## Proposed Domains

### Durable State

Owns append-only canonical facts and derived indexes.

Examples:

- message events
- control records
- tool records
- model-call records
- config and operational records
- indexes and query helpers

Current homes:

- `graph.py`
- `graph_*_edges.py`
- `graph_*_writers.py`

Target pressure:

- keep mutation and query semantics explicit
- prefer durable records over sidecar state when the fact should survive
- avoid letting transport or presentation layers decide durable meaning

### Transcript And Alignment

Owns working transcript parsing, projection, branch alignment, and surface
selection mechanics.

Examples:

- transcript block parsing
- role marker escaping
- selected surface/session precedence
- parentage and lineage alignment
- transcript reconstruction

Current homes include:

- `transcript.py`
- `runtime/frontier_resolution.py`
- `runtime/session_file_edges.py`
- parts of `operator_api.py`

Target pressure:

- separate "what text says" from "what action happens next"
- keep projection targeting read-only unless an explicit operation mutates
  durable state

### Operator Semantics

Owns the meaning of advancing the frontier.

Examples:

- frontier classification
- generation vs execution choice
- operator command dispatch
- one-layer consequence policy
- result-node lane semantics
- context assembly quality gates

Current homes include:

- `runtime/step_runtime.py`
- `runtime/step_*_runtime.py`
- `runtime/operator_commands.py`
- `runtime/operator_command_*`
- `runtime/result_nodes.py`

Target pressure:

- this is a semantic domain, not a dumping ground for every runtime-adjacent
  helper
- callers should ask for an operator operation, not assemble the operation from
  many phase callbacks

### Activities And Streams

Owns live async activity state, stream lanes, cancellation, terminality, and
subscribe/watch semantics.

Examples:

- run ids
- activity status
- event streams
- cancellation requests
- terminal event policy
- subscribe offsets and sequence numbers

Current homes include:

- `runtime/async_activity_store*`
- `runtime/stream_subscribe_runtime.py`
- `runtime/event_classification.py`
- `runtime/watch_envelope_adapter.py`
- `runtime/async_lifecycle_envelope_adapter.py`

Target pressure:

- treat `activity -> event stream -> completion/cancellation` as the live
  runtime primitive
- keep transport-specific envelope compatibility at the edges
- test terminality and replay/subscribe behavior as domain contracts

### Capabilities

Owns model-addressable and user-intent tools.

Examples:

- shell execution
- file read/search/edit helpers
- apply-patch operations
- capability help and survey helpers
- tool-result shaping

Current homes:

- `tools_cluster/`
- `tools.py` as public registry facade

Target pressure:

- keep direct user intent distinct from model-addressable capability policy
- preserve the shared result shape where useful without merging authority
- keep capability implementation out of CLI, daemon, host, and operator
  orchestration modules

### Model And Backend

Owns model-call transport, backend/provider configuration, and managed backend
process lifecycle.

Examples:

- LLM HTTP calls
- backend/model selection
- generation policy
- managed-local backend process start/stop/status
- backend health checks

Current homes include:

- `llm.py`
- `backend_policy.py`
- `config.py`
- `runtime/operator_config_backend_ops.py`
- currently, `daemon/backend_lifecycle.py`

Target pressure:

- distinguish model-call transport from managed backend process lifecycle
- move managed backend lifecycle to a runtime-owned workspace/domain boundary
- keep daemon and host as adapters over lifecycle semantics

### Host And Supervision

Owns session-rooted runtime process supervision and local stdio request
handling.

Examples:

- `toas host serve`
- owner identity
- owner-liveness watchdog
- local request handler
- stdio host request/response loop

Current homes include:

- `cli_host_commands.py`
- `runtime/session_host_process.py`
- `runtime/session_host_state.py`
- `runtime/request_handler_assembly.py`

Target pressure:

- host is the primary local persistent runtime process
- host should be session-owned, not an ambient service
- host can invoke other domains but should not become the owner of all domains

### Transport And Protocol

Owns request framing, response envelopes, carrier compatibility, and RPC/stdio
transport details.

Examples:

- protocol envelope shape
- stdio framing
- Unix socket and Windows named-pipe transport
- daemon RPC compatibility
- request dispatch adapters

Current homes include:

- `rpc_protocol.py`
- `rpc_transport.py`
- `rpc_unix.py`
- `rpc_windows.py`
- `rpc_tcp.py`
- `runtime/request_dispatch*.py`
- `runtime/request_contract.py`

Target pressure:

- transport should carry requests and events, not decide semantic ownership
- envelope compatibility belongs near protocol edges
- avoid letting request handler assembly become an application container

### Presentation And Operator Surfaces

Owns command parsing, stdout rendering, transcript rendering, and human-facing
diagnostics.

Examples:

- CLI argument dispatch
- stdout contract
- transcript projection text
- result/imported-block rendering
- diagnostics and help text

Current homes include:

- `cli.py`
- `cli_dispatch.py`
- `cli_*_commands.py`
- `cli_session_views.py`
- `runtime/rendering_edges.py`
- `runtime/presentation_edges.py`
- `tools_cluster/rendering.py`

Target pressure:

- CLI remains thin
- presentation chooses wording and shape, not durable or semantic meaning
- imported/result projection stays explicit about provenance and potency

## Public Service Vocabulary

Do not conflate these terms:

- `daemon`: compatibility RPC service process
- `host`: session-owned local runtime transport process
- `backend`: model/provider lifecycle target
- `server`: internal implementation word

Current aliases:

- `toas service ...` aliases `toas daemon ...`
- `toas transport ...` aliases `toas host ...`

Direction:

- keep `daemon` available for compatibility
- make `host` the primary local persistent runtime path
- make `backend` runtime-owned as model/provider lifecycle
- avoid adding public `toas server` unless a future product shape needs a
  separate concept

## Dependency Injection Discipline

Dependency injection should cross domain or environmental boundaries.

Good injection examples:

- process spawning
- filesystem/event writer
- clock and sleep
- health probe
- active-run query
- model HTTP client
- transport send/receive
- stdout/stderr presenter

Suspicious injection examples:

- passing every phase of a workflow as a callback
- caller assembling a behavior graph because no domain object owns it
- request handler assembly becoming a service locator
- tests proving wiring details instead of domain contracts

Rule of thumb:

> Inject ports, not implementation steps.

When injection becomes noisy, first ask whether a domain object, controller, or
policy object is missing.

## Backend Lifecycle As First Proof Slice

The backend lifecycle gap is a good test case because it touches the exact
boundaries this proposal cares about.

Target shape:

```text
Model/backend domain
  BackendLifecycleController
  BackendLifecycleRegistry
  BackendProcessState
  BackendLifecycleResult

Ports
  ProcessSpawner
  HealthProbe
  EventWriter
  ActiveRunQuery

Adapters
  CLI output adapter
  daemon RPC compatibility adapter
  host/local request adapter
```

Success would mean:

- `toas backend ...` can operate locally when daemon RPC is off
- daemon backend operations preserve legacy/envelope response compatibility
- managed backend process state is explicit and workspace-scoped
- tests target backend lifecycle contracts before daemon adapter wiring
- `runtime/` does not absorb a large unstructured process-control module

## Anti-Goals

This proposal does not require:

- an immediate package rename
- a public `toas server` command
- removing daemon compatibility
- forcing every subsystem through one host process
- introducing a framework-style service container
- turning every helper into a class

## Migration Strategy

1. Use this document as a critique artifact.
2. Classify existing modules by proposed domain before moving more code.
3. Apply the model to backend lifecycle first.
4. Update `docs/runtime-direction.md` with accepted target-shape language.
5. Update `docs/runtime-ownership.md` with accepted contribution guidance.
6. Continue `400` decomposition only where slices can name their owning domain.

## Open Critique Questions

- Is "operator semantics" too broad, or should frontier resolution, slash
  commands, and consequence execution be separate domains?
- Should transcript alignment be its own package, or is it part of operator
  semantics?
- Should activities/streams be independent of host supervision, or is that
  separation artificial?
- Should model-call transport and managed backend lifecycle live under one
  model/backend domain, or should process lifecycle be separate from model
  invocation?
- Is request dispatch a transport concern, an application concern, or a thin
  boundary between them?
- What domain owns configuration precedence after values are loaded?
- Where should presentation rendering stop and projection semantics begin?
- Which current `runtime/` modules are already in the wrong future domain?
- Where is current dependency injection proving good boundaries, and where is it
  hiding missing objects?
