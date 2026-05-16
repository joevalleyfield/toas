# TOAS Runtime Direction

Status: DIRECTIONAL
Normative Scope: non-normative target architecture and sequencing
Task Links: `515`, `516`, `470`, `484`

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

Standalone daemon mode may still exist as optional compatibility, but should not define the architecture.

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

The runtime host is the architectural center.

Responsibilities:

- supervision
- routing
- event coordination
- transcript projection
- async activity management
- cancellation propagation
- runtime lifecycle management

### Layer 3: Persistent Runtime Workers

Examples:

- shell sessions
- Python runtimes
- Node runtimes
- tool workers
- model backends

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

## Near-Term Engineering Priorities

1. Probe and eliminate startup overhead.
2. Define transport abstraction.
3. Define protocol envelope v0.
4. Strengthen persistent-session path.
5. Clarify supervision tree model.
6. Separate durable vs live event handling.

## Anti-Goals

Avoid accidentally evolving into:

- localhost microservice mesh
- mandatory ambient daemon platform
- REST-first architecture
- unnecessary process fragmentation

unless future requirements justify it.
