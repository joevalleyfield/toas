# Runtime Ownership And Module Boundaries

Status: CURRENT
Normative Scope: contribution guidance for where runtime, tool, CLI, and transport semantics should live
Task Link: `675`
Related: `400`, `525`, `572`, `674`, `260614-toas-architecture-masterplan-draft`, `260614-runtime-owned-backend-lifecycle-architecture`

## Purpose

This note describes the current ownership map while TOAS continues the `400`
decomposition arc.

Several historical files remain as public import surfaces or legacy facades.
New behavior should follow the ownership boundaries below rather than the older
habit of placing broad logic in `step.py`, `tools.py`, `cli.py`, or `daemon.py`.

## Ownership Principles

- Keep durable storage and graph append/query concerns in `graph.py` and
  focused `graph_*_edges.py` / `graph_*_writers.py` helpers.
- Keep transcript parsing, transcript-shape mechanics, and transcript
  reconciliation separate from consequence selection.
- Keep semantic execution ownership in focused domain modules. `src/toas/runtime/`
  is a current home for much of this behavior, not a blanket owner for all new
  semantics.
- Keep tool capability behavior in `src/toas/tools_cluster/`.
- Keep CLI modules thin: argument parsing, local orchestration calls, rendering,
  legacy wrapping, and fidelity-lowering edge views.
- Keep daemon modules transport-adapter oriented. Daemon/RPC can carry runtime
  requests, but should not define semantic behavior.
- Keep model transport in `llm.py` and prompt library behavior in `prompts.py`
  plus file-backed prompt assets.
- Keep model invocation separate from model backend lifecycle: provider request
  shaping and response normalization are not managed process ownership.
- Prefer focused helpers over new legacy shims. Add or keep facade symbols only
  when they preserve an existing public/import contract, and retire those
  facades when the contract no longer needs them.
- Keep internal streams and domain results full-fidelity until an explicit edge
  adapter must lower fidelity for a real interface constraint.
- Inject ports at environmental or domain boundaries. Do not inject internal
  implementation steps when a domain object should own the workflow.

## Domain-Oriented Ownership

Use the architecture domains below when deciding where code and tests belong.
Current module names may lag the target shape; the force is more important than
the package name.

| Domain | Owns | Should not own |
| --- | --- | --- |
| Durable State | append-only record schemas, graph append/query APIs, rebuildable indexes | transcript frontier meaning, tool authority, model policy, transport fallback, presentation wording |
| Transcript Reconciliation | alignment between user-edited transcript text and durable message/control history | generation, tool execution, cancellation, model invocation, activity terminality |
| Operator Semantics | unresolved frontier meaning and next consequence selection | CLI argv, daemon request handlers, transport envelopes, process handles, rendered text |
| Activity Lifecycle | run ids, status, stream events, offsets, cancellation state, terminality, replay windows | host attachment identity, tool authority, model request shape, presentation wording |
| Capabilities | model-addressable tool definitions, validation, execution, denials, progress, tool facts | transcript alignment, model invocation policy, activity terminality, durable graph schema |
| Model Invocation | provider config, request shaping, retry policy, response normalization, model-call audit | managed backend process state, host lifecycle, prompt library ownership |
| Model Backend Lifecycle | model-serving process start/stop/status/restart, health, workspace/config identity, stale diagnostics | model prompts, provider response normalization, generic worker supervision |
| Session Host Supervision | host process liveness, owner identity, attachment records, stdio loop state | activity terminality, step semantics, backend lifecycle truth, durable transcript meaning |
| Effective Policy And Authority | config defaults/files, durable overrides, env inputs, owner identity, grants, precedence, provenance | executing capabilities, invoking models, mutating backend processes, deciding parentage |
| Transport And Protocol | framing, request ids, envelopes, legacy payloads, fidelity-lowering edge views, carrier errors, protocol validation | semantic success, activity terminality, transcript branch parentage, backend lifecycle truth |
| Surface Adapters | CLI/editor/web command shapes, stdout conventions, user-facing wording | durable meaning, operator consequences, activity terminality, process ownership |
| Projection And Rendering | display-safe text, projection policy, provenance/potency markers | durable mutation, tool authorization, model calls, transcript branch decisions |

When a change crosses domains, keep the semantic change in the owning domain and
let outer surfaces call into it. Legacy response shapes and fidelity-lowering
edge views should be derived from domain results or stream events, not treated
as the source of truth.

## Current Module Map

### Semantic Runtime

`src/toas/runtime/` currently owns several runtime-domain implementations. Keep
new modules focused so `runtime/` does not become the next broad module.

- `step_runtime.py`, `frontier_resolution.py`, and `step_*_runtime.py` own the
  step/consequence path.
- `operator_commands.py` and `operator_command_*` modules own slash-command
  runtime behavior.
- `result_nodes.py`, `rendering_edges.py`, and `presentation_edges.py` own
  runtime/projection result-node boundaries.
- `async_activity_store*`, `stream_subscribe_runtime.py`,
  `session_host_process.py`, and transport contract modules own runtime-host and
  async lifecycle semantics.
- `session_step_edges.py`, `session_file_edges.py`, and related edge modules own
  cross-surface runtime glue that is semantic rather than CLI-specific.

Before adding new runtime code, name the domain it belongs to. If the behavior
is process lifecycle, model invocation, legacy transition, fidelity-lowering
adapter projection, transport, or policy precedence, keep that distinction
visible in the module name, tests, and dependencies.

### Tool Capabilities

`src/toas/tools_cluster/` owns model-addressable tool behavior:

- `registry.py` owns validation/dispatch mechanics.
- `execution.py` owns plan execution orchestration.
- `basic_ops.py`, `file_ops.py`, `apply_patch_ops.py`, `shell_ops.py`, and
  `shell_streaming.py` own concrete capabilities.
- `rendering.py` owns tool-result projection shaping.
- `capability_help_ops.py` and `survey_ops.py` own introspection helpers.

`src/toas/tools.py` remains the registry-facing public facade and legacy import
surface. New tool behavior should normally land in `tools_cluster/` and be
wired through `tools.py` only as needed for the established public registry.

### CLI And Operator API

CLI ownership is split across focused modules:

- `cli.py` is a legacy-facing entry surface and should stay thin.
- `cli_dispatch.py` and `cli_dispatch_ops.py` own top-level argument routing.
- `cli_session_commands.py`, `cli_async_commands.py`, `cli_host_commands.py`,
  `cli_runtime_commands.py`, `cli_session_views.py`, `cli_analysis_commands.py`,
  and `cli_streaming.py` own command-family wrappers and rendering.
- `operator_api.py` is the in-process API seam for local operator workflows.

New semantic behavior should usually move below these wrappers into
`runtime/`, `tools_cluster/`, `graph*`, or config/prompt modules.

### Daemon, Host, And Transport

`src/toas/daemon/` owns daemon transport/server legacy adaptation:

- request parsing, dispatch adapters, process lifecycle, backend lifecycle, and
  run-store transport state live here.
- Runtime semantics consumed by daemon paths should come from `runtime/` or
  `operator_api.py`.

The session host direction is runtime-owned and stdio-first. See
`docs/runtime-direction.md` for the broader target architecture.

Daemon, host, and protocol code may carry requests, preserve legacy payloads,
lower fidelity at explicit interface edges, and report carrier errors. They
should not decide semantic success, activity terminality, transcript branch
parentage, capability authority, or backend lifecycle truth.

Backend lifecycle used to be the important daemon-owned exception. The selected
code-ownership target has landed: a runtime-owned model backend lifecycle core
now sits behind daemon/RPC, local CLI, and host adapters for the managed-local
backend command contract.

This does not mean TOAS owns every model server process it uses. In external
mode, including remote APIs and pre-started local servers such as Ollama or a
manually launched llama.cpp server, TOAS is a client/observer. It may resolve
configuration, issue provider calls, check health, or display status, but it
does not own start/stop process lifetime.

Backend lifecycle contribution guidance:

- keep the scope to model-serving/provider lifecycle contracts, not generic
  worker supervision
- distinguish TOAS-managed local processes from external/pre-started providers
- keep provider request shaping and model-call failure handling in Model
  Invocation
- preserve current legacy plus envelope backend response shapes only while
  callers still need them
- make adapters derive legacy payloads from the lifecycle domain result
- treat backend health as an observation, not durable availability
- treat config changes as stale/restart-required unless an explicit
  restart/apply occurs
- block stop/restart from active-run evidence without making backend lifecycle
  own activity terminality

Activity lifecycle contribution guidance:

- treat `_RUNS`/`AsyncRun` state as live runtime truth unless a specific fact is
  written durably
- keep reconnect replay (`offset`, `since_seq`, stream events) separate from
  crash recovery
- treat subscriber cursors and transport envelopes as carriers, not terminality
  owners
- keep session host liveness as attachment state; it must not decide activity
  success, failure, or cancellation
- define a durable cancellation-intent or stream-event contract before making
  cancellation or stream replay survive restart

### Historical Facades

These files are important but should not attract unrelated new logic:

- `step.py`: legacy/session-help facade plus public exports around
  runtime-owned step and operator-command behavior.
- `tools.py`: public registry facade around `tools_cluster/`.
- `cli.py`: top-level legacy entry surface around focused CLI modules.
- `daemon/__init__.py`: package facade around daemon adapter modules.

When editing these files, prefer delegation, public-contract preservation, and
small wrapper cleanup over adding new ownership. Treat legacy preservation as a
temporary constraint, not a reason to keep stale paths indefinitely.

## Routing Questions

Use these defaults when choosing where to edit:

- Does it change what a transcript frontier means or what consequence is
  produced? Use Operator Semantics in `runtime/`.
- Does it change how edited transcript text aligns to durable history? Use
  Transcript Reconciliation helpers, not tool/model execution paths.
- Does it change durable record storage/query behavior? Use `graph.py` or a
  focused `graph_*` helper.
- Does it change a model-addressable tool? Use `tools_cluster/`, then wire the
  registry facade.
- Does it change user CLI parsing or stdout presentation only? Use focused
  `cli_*` modules.
- Does it change daemon/RPC/stdio carrying behavior without changing semantics?
  Use daemon, protocol, transport, or host adapter modules.
- Does it change backend HTTP/model-call transport? Use `llm.py` or related
  generation runtime seams.
- Does it change managed model-serving process start/stop/status/restart or
  health? Use the Model Backend Lifecycle owner.
- Does it change config, grants, owner identity, or authority precedence? Use
  Effective Policy And Authority seams, and keep provenance observable.
- Does it change rendered transcript/result text? Use Projection And Rendering;
  rendered text must not become canonical state.
- Does it change prompt asset discovery/rendering? Use `prompts.py` or prompt
  assets.

When a change crosses these boundaries, keep the semantic change in the owning
layer and let outer surfaces call into it.

## Projection Boundary Notes

These notes are here to prevent future surveys from treating intentional
projection asymmetries as fresh architecture alarms.

- `step` remains transcript-first by design. The operator-edited working
  transcript is the authoritative frontier input for progression.
- `toas transcript` is intentionally asymmetric with `step`: it reconstructs a
  usable transcript projection from durable history when the working transcript
  is absent, stale, or intentionally discarded.
- That asymmetry alone is not drift. The fidelity seam to protect is whether
  durable message content round-trips coherently between transcript
  reconciliation and later history-backed transcript reprojection.
- History-backed transcript reprojection and fresh step-time transcript-shaped
  projection may share transcript marker/escaping primitives without sharing
  one top-level renderer. Fresh projection can legitimately include
  transient/result material that is not just durable message history rendered
  again.
- `toas llm-input` should be understood as the shared core model-visible
  conversation-body projection unless an explicit envelope-inclusive mode says
  otherwise.
- Actual model requests may still wrap that shared core body in deterministic
  packet/envelope/system material before provider invocation.

## Must Not Regress

- Prior durable history is never mutated.
- Rendered transcript text is never canonical durable truth.
- Transport envelopes, fidelity-lowering edge views, and legacy fields never
  define semantic success.
- Direct user intent and model-addressable authority remain distinct.
- Host loss alone never marks an activity succeeded, failed, or cancelled.
- Backend health success never becomes a durable availability guarantee.
- Config changes never silently restart or reconfigure an already-running model
  backend.
- Model provider failure never mutates backend lifecycle state without explicit
  lifecycle observation or policy.
