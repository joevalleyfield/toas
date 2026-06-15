# TOAS Runtime Direction

Status: DIRECTIONAL
Normative Scope: non-normative target architecture and sequencing
Task Links: `515`, `516`, `470`, `484`, `260614-toas-architecture-masterplan-draft`
Protocol Reference: `docs/protocol-notes.md` -> "Envelope V0 (Draft)"

## Status

This document captures the emerging runtime architecture direction for TOAS after latency investigation, IPC discussion, persistent-runtime experiments, and supervision/lifecycle analysis.

This is not a finalized specification.
It is a direction-setting architecture document intended to:

- align future implementation decisions
- reduce accidental architectural drift
- identify stable primitives
- define near-term engineering tasks
- clarify which constraints are intentional

## Core Architectural Direction

TOAS is converging toward:

- a durable transcript/event substrate as the semantic center
- session-rooted runtime hosts
- persistent warm runtimes
- event-stream semantics
- explicit supervision trees
- stdio-first IPC
- minimal ambient infrastructure
- selective isolation boundaries
- durable transcript semantics separated from live runtime semantics

The architecture is increasingly:

- runtime-oriented
- conversational
- event-driven
- supervision-oriented

and decreasingly:

- command-oriented
- stateless
- request/response-centric
- service-mesh-oriented

Durable target-shape guidance promoted from
`docs/architecture-masterplan.md`:

- TOAS is centered on transcript/event durability, not on CLI, daemon, host, or
  daemon legacy behavior as a product center.
- Domains are justified by ownership forces: durable state, transcript
  reconciliation, consequence selection, activity liveness, authority,
  transport, presentation, model invocation, and model-serving lifecycle.
- Legacy surfaces are transition surfaces and should shrink toward removal.
- Fidelity-lowering adapters may exist at real interface edges, but internal
  streams and domain results should retain full semantic fidelity until that
  edge.
- Transport adapters may carry requests and preserve response shapes, but must
  not become semantic owners.
- Dependency injection should expose ports at environmental or domain
  boundaries, not replace workflow ownership with callback assembly.
- Rendered or transported representations must not become canonical state.

## Key Constraints and Drivers

### 1. Interactive latency matters

Observed benchmark behavior:

- spawned CLI path: ~200ms p50
- persistent RPC path: ~2.7ms p50

Implication:

The architecture should optimize for:

- persistent runtimes
- warm interpreters
- long-lived channels
- reduced startup/import overhead

rather than:

- disposable subprocess execution
- stateless CLI invocation

### 2. Session-rooted ownership is preferred

TOAS should not require ambient daemon/service infrastructure as the primary operating model.

Preferred model:

```text
client/editor/web-session
    └── runtime host
          ├── shell runtime
          ├── python runtime
          ├── tool runtimes
          └── model client/runtime
```

Standalone daemon mode may still exist as an optional legacy surface, but should
not define the architecture.

### 3. STIG/security posture matters

TOAS should avoid assuming `localhost == trusted boundary`.

Preferred communication semantics:

- explicit process ownership
- inherited handles/capabilities
- private channels
- minimal ambient discoverability

This favors stdio pipes and explicit subprocess trees over open localhost listeners.

### 4. Conversational runtimes are first-class

TOAS increasingly operates on warm conversational state and incremental event streams, not isolated request/response calls.

### 5. Runtime needs internal ownership boundaries

The runtime direction is still a correction away from localized abuses: broad
CLI wrappers, daemon-owned semantics, repeated cold starts, and request/response
orchestration that hides transcript state.

The next risk is second-order. Once behavior moves below CLI and daemon
surfaces, `runtime/` can become another broad owner unless runtime modules name
their internal force: transcript reconciliation, operator semantics, activity
lifecycle, policy/authority, model invocation, model backend lifecycle,
transport/protocol, or projection/rendering.

Future work should still prefer runtime-owned semantics over CLI-owned or
daemon-owned semantics. It should also be able to name the runtime domain that
owns the behavior before deciding where code or tests belong.

## Architectural Model

### Runtime Philosophy

TOAS should be viewed as an interactive runtime substrate more than a collection of RPC services.

Useful analogies:

- notebook kernels
- language servers
- tmux
- actor systems
- supervision trees

## Runtime Layers

### Layer 1: External Clients

Examples:

- Vim plugin
- web UI
- shell wrapper
- future editor integrations

Responsibilities:

- session ownership
- runtime attachment/spawn
- event rendering
- transcript editing/projection

### Layer 2: Runtime Host

The runtime host is the primary live coordinator for session-rooted work. It is
not the semantic owner of every behavior it carries.

Responsibilities:

- supervision
- routing
- event coordination
- transcript projection
- async activity management
- cancellation propagation
- runtime lifecycle management

The host may carry requests/events for domains such as Activity Lifecycle,
Operator Semantics, Capabilities, Model Invocation, or Model Backend Lifecycle.
Those domains still own their semantics.

### Layer 3: Persistent Runtime Workers

Examples:

- shell sessions
- Python runtimes
- Node runtimes
- tool workers
- model-serving backends

These are stateful, conversational, event-oriented, restartable, and supervised.

## IPC Direction

### Preferred IPC Model

Primary direction: persistent framed stdio streams.

### Transport Abstraction

Define a transport interface with optional transports:

- stdio
- Unix sockets
- Windows named pipes
- websocket (future)

Stdio remains the default/primary path.

### Framing

Preferred framing direction: `Content-Length` style framing (LSP-like), not newline-delimited payloads.

## Event Model

TOAS interaction should model:

`activity -> event stream -> completion/cancellation`

more than:

`request -> response`.

Current runtime streams use explicit lanes for independent child lifecycles:

- `llm_answer`: model answer deltas, closed by `llm_done`
- `tool`: tool/action progress, closed per invocation by `tool_done`
- `projection`: transcript/graph/run projection deltas, closed by `projection_done`
- `run`: outer activity lifecycle, closed by `run_done`

Only `run_done` means the whole activity is complete. Child-lane done markers
are useful ordering and rendering signals, but they are not whole-run
terminality.

Likely event categories:

- request
- accepted
- progress
- stdout
- stderr
- telemetry
- warning
- status
- result
- error
- cancel
- cancelled
- heartbeat
- capability

Likely primitives:

- session
- activity
- event
- supervisor
- stream
- projection
- anchor

## Supervision Model

Prefer explicit ownership trees:

```text
owner
 └── owned runtime
      └── owned worker
```

Cancellation should propagate downward and be event-visible.

## Isolation Philosophy

Subprocess boundaries should exist where they provide value:

- shell/language runtimes
- model backends
- crash-prone or untrusted execution

Avoid subprocess/RPC boundaries for internal Python decomposition that can be in-process async coordination.

## Durable vs Ephemeral Semantics

Maintain explicit separation between:

- durable transcript/history semantics
- ephemeral runtime event semantics

Not all runtime events belong in durable history.

Current activity streams are live runtime state unless explicitly recorded as
durable facts. Watch/subscribe replay is a reconnect feature over the live
activity store; it should not be described as crash-surviving stream replay
until a durable activity event contract exists.

Stable guardrails:

- prior durable history is never mutated
- rendered transcript text is never canonical durable truth
- transport envelopes, edge views, and legacy fields never define semantic
  success
- direct user intent and model-addressable authority remain distinct
- host loss alone never marks an activity succeeded, failed, or cancelled
- backend health success never becomes a durable availability guarantee
- config changes never silently restart or reconfigure an already-running model
  backend
- model provider failure never mutates backend lifecycle state without explicit
  lifecycle observation or policy

## Model Backend Lifecycle Direction

`backend` means model-serving/provider lifecycle. It does not mean the TOAS
daemon, and it should not become a generic worker supervisor.

Direction:

- model invocation owns provider request shaping, normalized responses, and
  model-call audit facts
- model backend lifecycle owns the managed-local backend command contract:
  managed process state, health, start/stop/status/restart,
  stale/restart-required diagnostics, and lifecycle facts
- external remote APIs and pre-started local servers are not TOAS-owned
  processes; TOAS may configure, call, observe, and report against them, but it
  does not own their process lifetime
- daemon RPC and future host/local surfaces should act as adapters over a common
  lifecycle command/result contract
- a TOAS-managed running backend should be identified by workspace plus startup
  configuration identity, or by an equivalent stale marker
- provider failure is a model invocation failure unless lifecycle explicitly
  observes or records backend process failure

## Near-Term Engineering Priorities

1. Keep accepted architecture guidance synchronized between ownership and
   direction docs as implementation evidence lands.
2. Follow runtime-owned backend lifecycle evidence into focused follow-ups only
   where concrete gaps remain.
3. Strengthen persistent-session and stdio host paths without making host
   liveness semantic truth.
4. Keep legacy transport/envelope shapes and fidelity-lowering edge adapters
   adapter-owned rather than domain-owned.
5. Continue module decomposition only where a slice can name its owning domain.
6. Preserve durable vs live event separation.

## Anti-Goals

Avoid accidentally evolving into:

- localhost microservice mesh
- mandatory ambient daemon platform
- REST-first architecture
- unnecessary process fragmentation

unless future requirements justify it.
