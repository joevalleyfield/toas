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

## How To Read This Draft

If you are new to this part of TOAS, read the document as a map from the
current transition state to a proposed target shape.

Current transition state:

```text
CLI, host, and daemon surfaces
  -> call a mix of runtime modules, compatibility facades, and focused helpers
    -> append/query graph state
    -> execute tools and model calls
    -> render stdout/transcript/protocol responses
```

Target shape:

```text
operator surfaces and transport adapters
  -> named domains with explicit owners
    -> durable state, activities, capabilities, model invocation and model-serving workers
    -> presentation adapters for humans and protocols
```

The proposal is less about renaming packages and more about making ownership
recoverable. A maintainer should be able to answer "who owns this behavior?"
before deciding where code or tests belong.

## Terms Used Here

- `transcript`: the user-controlled working text surface, usually
  `.toas/session.md`.
- `durable event graph`: append-only canonical history, usually
  `.toas/events.jsonl`.
- `consequence layer`: one step of work produced from the current unresolved
  transcript frontier, such as generation, tool execution, or an operator
  command result.
- `runtime host`: a live process that carries local interaction for a session;
  today this is primarily `toas host serve`.
- `activity`: a live async run with status, stream events, cancellation, and a
  terminal outcome.
- `transport adapter`: a carrier such as stdio host or daemon RPC that forwards
  requests/events without owning their meaning.
- `model backend`: the LLM/model-serving endpoint or managed local process used
  for generation; it is not the TOAS daemon and not a generic worker supervisor.

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
      -> tools/model-serving workers do bounded work
```

The core invariant remains:

> `toas step` accepts transcript state, synchronizes it into durable history,
> and resolves one layer of consequence.

Everything else should support that substrate without hiding ownership behind
ambient service state.

## Two Example Flows

For `toas step`, the target domain responsibilities look like this:

```text
surface adapter
  parses arguments and renders stdout

transcript reconciliation
  reads the working transcript and aligns it with durable history

operator semantics
  classifies the frontier and chooses the next consequence

capabilities or model invocation
  executes a tool or calls the model when the consequence requires it

durable state
  records message/control/tool/model-call facts

projection and rendering
  projects only newly produced consequence output
```

For `toas backend status`, the intended future path is different:

```text
surface adapter
  parses `backend status` and renders the status line

model backend lifecycle
  answers workspace-scoped model-serving process state

transport adapter, optionally
  carries the same operation through daemon RPC or host stdio

durable state, when a lifecycle fact is produced
  records backend lifecycle events under the requested workdir
```

These examples are deliberately small. They are here to show how a single user
operation should cross domains without any adapter becoming the semantic owner.

## Domain Map

| Domain | Force | Current homes include | Guardrails |
| --- | --- | --- | --- |
| Durable State | Preserve append-only canonical facts and rebuildable derived views | `graph.py`, `graph_*_edges.py`, `graph_*_writers.py` | Mutations go through graph append/query APIs; indexes and projections must not become competing truth. |
| Transcript Reconciliation | Reconcile user-edited working text with canonical history | `transcript.py`, `runtime/frontier_resolution.py`, `runtime/session_file_edges.py`, parts of `operator_api.py` | Keep "what text says" separate from "what action happens"; make branch ambiguity explicit. |
| Operator Semantics | Decide what unresolved frontier state means and which consequence happens next | `runtime/step_runtime.py`, `runtime/step_*_runtime.py`, `runtime/operator_commands.py`, `runtime/result_nodes.py` | Surface and transport adapters must not decide step meaning. |
| Activity Lifecycle | Manage live work over time: status, events, cancellation, terminality, resubscription | `runtime/async_activity_store*`, `runtime/stream_subscribe_runtime.py`, `runtime/event_classification.py`, envelope adapters | Terminality belongs here; child-lane completion, subscribers, and envelopes do not define whole-run completion. |
| Capabilities | Execute bounded operations under explicit authority policy | `tools_cluster/`, `tools.py` facade | Keep direct user intent distinct from model-addressable tool authority. |
| Model Invocation | Call model providers and normalize generation responses | `llm.py`, `backend_policy.py`, `config.py`, parts of `runtime/operator_config_backend_ops.py` | Keep provider request shaping and model-call audit separate from managed process lifecycle. |
| Model Backend Lifecycle | Manage local model-serving process start/stop/status/restart and health | currently `daemon/backend_lifecycle.py`, `cli_async_commands.py` routing/output | Scope is model-serving, not generic worker supervision; daemon and host are adapters. |
| Session Host Supervision | Own session-rooted process attachment, owner identity, and stdio liveness | `cli_host_commands.py`, `runtime/session_host_process.py`, `runtime/session_host_state.py`, `runtime/request_handler_assembly.py` | Host loss is attachment loss, not automatic activity terminality. |
| Effective Policy And Authority | Resolve config, overrides, grants, owner identity, and lane authority before use | `config*.py`, `shell_grants.py`, `runtime/policy_edges.py`, parts of `step.py` and operator commands | Resolution should be centralized enough that provenance is observable and precedence is not scattered. |
| Transport And Protocol | Carry requests/events across process boundaries without owning meaning | `rpc_protocol.py`, `rpc_transport.py`, `rpc_unix.py`, `rpc_windows.py`, `rpc_tcp.py`, `runtime/request_dispatch*.py`, `runtime/request_contract.py` | Envelopes and legacy response fields are carriers, not semantic truth. |
| Surface Adapters | Parse user-facing commands and adapt to CLI/editor/web surfaces | `cli.py`, `cli_dispatch.py`, `cli_*_commands.py`, `cli_session_views.py` | Keep wrappers thin; choose wording and command shape, not durable or semantic meaning. |
| Projection And Rendering | Render semantic state into display-safe text | `runtime/rendering_edges.py`, `runtime/presentation_edges.py`, `tools_cluster/rendering.py` | Projection is display state; it must not invent durable meaning. |

## Boundary Invariants

These are candidate hard guardrails for future implementation and review.

Durable State:
- May know record schemas, append order, ids, parentage, indexes, and query
  rules.
- Must not decide transcript frontier meaning, tool authority, model policy,
  transport fallback, or presentation wording.
- Durable facts and derived query results may cross out; rendered transcript
  text, transport envelopes, and mutable process state must not cross in as
  canonical truth.
- The boundary has failed if any renderer, daemon, host, or tool path creates
  competing durable meaning outside graph append/query APIs.

Transcript Reconciliation:
- May know working transcript text, durable message/control history, selected
  surface/session precedence, and parentage rules.
- Must not decide whether a frontier should generate, execute, cancel, call a
  model, or run a capability.
- Reconciled nodes, selected frontier, parentage/branch decisions, and
  reconciliation diagnostics may cross out.
- Tool authorization, model generation policy, activity terminality, and
  rendered projection text must not cross in as reconciliation truth.
- The boundary has failed if edited prior content mutates history or branch
  ambiguity is hidden inside consequence execution.

Operator Semantics:
- May know reconciled frontier state, effective policy inputs, lane roles, and
  consequence rules.
- Must not own durable storage mechanics, model transport, tool implementation,
  host liveness, or CLI wording.
- Consequence requests, command results, model invocation requests, capability
  invocation requests, and durable-record intents may cross out.
- Raw transport envelopes, CLI argv, mutable backend process handles, and
  rendered text must not cross in as semantic inputs.
- The boundary has failed if CLI, host, or daemon code determines what `step`
  means.

Activity Lifecycle:
- May know run ids, status, stream events, offsets, cancellation state,
  terminality, and replay windows.
- Must not decide host attachment identity, capability permission, model request
  shape, or presentation wording.
- Activity commands, events, status snapshots, and terminal outcomes may cross
  the boundary.
- Child-lane completion must not cross as whole-run terminality; transport
  disconnect must not cross as run failure by itself.
- The boundary has failed if subscribers, envelopes, host death, or child
  `*_done` events can redefine run terminality.

Capabilities:
- May know tool definitions, argument validation, execution mechanics, and
  resolved authority inputs.
- Must not decide transcript alignment, model invocation policy, activity
  terminality, or durable graph schema.
- Capability requests, results, denials, progress events, and tool facts may
  cross out.
- Unresolved policy provenance, raw user/model authority ambiguity, and
  transport fallback must not cross in as implicit permission.
- The boundary has failed if a denied action can run through another lane or if
  direct user intent and model-addressable capability authority merge silently.

Model Invocation:
- May know provider config, selected model/backend intent, request shaping,
  retry policy, response normalization, and model-call audit payloads.
- Must not own managed backend process state, host lifecycle, tool authority, or
  transcript reconciliation.
- Model requests, normalized responses, model-call records, and provider errors
  may cross the boundary.
- Process handles, backend health as durable availability, and transport adapter
  fallback must not cross in as invocation truth.
- The boundary has failed if provider call failure automatically becomes backend
  lifecycle failure or backend process state changes model-call audit semantics.

Model Backend Lifecycle:
- May know model-serving process state, lifecycle config, health probes,
  workspace/config keying, active-run blocking, and lifecycle records.
- Must not shape model prompts, normalize model responses, decide operator
  consequences, or own generic worker supervision.
- Lifecycle commands, process status, health observations, stale/restart-required
  diagnostics, and lifecycle record intents may cross the boundary.
- Generic worker process state, model-call request bodies, and implicit config
  changes must not cross in as lifecycle commands.
- The boundary has failed if changing config silently restarts a backend, health
  success is treated as durable availability, or backend becomes a generic
  process supervisor.

Session Host Supervision:
- May know host process liveness, owner identity, attachment records, stdio loop
  state, and host stop/start behavior.
- Must not decide activity terminality, step semantics, model/backend lifecycle
  state, or durable transcript meaning.
- Attachment status, owner identity, host request frames, and host loss
  diagnostics may cross out.
- Activity outcome, durable facts, and capability authority must not cross as
  consequences of host liveness alone.
- The boundary has failed if host death marks a run failed, succeeded, or
  cancelled without Activity Lifecycle policy.

Effective Policy And Authority:
- May know config defaults/files, durable overrides, env inputs, owner identity,
  grants, transcript/control modifiers, and precedence rules.
- Must not execute capabilities, invoke models, mutate backend processes, or
  decide transcript parentage.
- Resolved policy values, authority grants/denials, provenance, and diagnostics
  may cross out.
- Raw scattered precedence assumptions must not cross into consumers; consumers
  must not recompute policy ad hoc.
- The boundary has failed if permissions widen silently or two consumers resolve
  the same policy differently.

Transport And Protocol:
- May know framing, request ids, envelopes, compatibility payloads, carrier
  errors, and protocol validation.
- Must not decide semantic success, activity terminality, transcript branch
  parentage, capability authority, or backend lifecycle truth.
- Requests, responses, envelopes, carrier errors, and protocol diagnostics may
  cross the boundary.
- Domain state, process handles, durable graph facts, and semantic fallback
  decisions must not cross as transport-owned truth.
- The boundary has failed if legacy fields, envelopes, or RPC fallback define
  domain meaning.

Surface Adapters:
- May know CLI args, editor/web command shapes, stdout conventions, user-facing
  wording, and adapter compatibility.
- Must not decide durable meaning, operator consequences, activity terminality,
  or lifecycle/process ownership.
- Parsed commands, rendered messages, diagnostics, and presentation requests may
  cross the boundary.
- Raw argv must not cross deep into semantic domains; rendered text must not
  cross back as canonical state.
- The boundary has failed if changing CLI wording changes system behavior.

Projection And Rendering:
- May know semantic records, projection policy, provenance/potency markers, and
  display-safe text rules.
- Must not mutate durable state, authorize tools, decide model calls, or resolve
  transcript branches.
- Rendered text, projection diagnostics, and display metadata may cross out.
- Rendered text must not cross as canonical durable fact; projection repair must
  not mutate source records.
- The boundary has failed if projection output becomes source of truth or
  rendering failure changes semantic outcome.

## Public Service Vocabulary

Do not conflate these terms:

- `daemon`: compatibility RPC service process
- `host`: session-owned local runtime transport process
- `backend`: model-serving/provider lifecycle target
- `server`: internal implementation word

Current aliases:

- `toas service ...` aliases `toas daemon ...`
- `toas transport ...` aliases `toas host ...`

Direction:

- keep `daemon` available for compatibility
- make `host` the primary local persistent runtime path
- make `backend` runtime-owned as model-serving lifecycle
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

The detailed per-domain port critique is preserved under `Critique Notes`.

## Model Backend Lifecycle Proof Slice

The model backend lifecycle gap is a good test case because it touches the exact
boundaries this proposal cares about while staying scoped to model-serving
processes.

Status: landed as the first proof slice.

Target shape:

```text
Model backend lifecycle domain
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

Landed evidence:

- `toas backend ...` can operate locally when daemon RPC is off
- daemon backend operations preserve legacy/envelope response compatibility
- the lifecycle domain has an explicit request/result contract
- tests target backend lifecycle contracts as well as adapter behavior
- CLI, daemon/RPC, and stdio-host request paths adapt to the lifecycle domain
- `runtime/` did not absorb a large unstructured process-control module

Remaining gaps:

- managed backend process state is explicit but not yet registry-keyed by
  workspace plus startup configuration identity
- stale/restart-required status from changed startup config remains a follow-up
- model invocation to backend lifecycle failure handoff remains a follow-up
- durable lifecycle record semantics are minimal and should be expanded only
  from concrete evidence

## Anti-Goals

This proposal does not require:

- an immediate package rename
- a public `toas server` command
- removing daemon compatibility
- forcing every subsystem through one host process
- introducing a framework-style service container
- turning every helper into a class

## Maintenance Boundary

This document should still help after the initial backend lifecycle slice has
landed. Keep durable architecture separate from migration notes.

Durable architecture:

- TOAS is centered on transcript/event durability, not on CLI, daemon, host, or
  `runtime/` as a package.
- Domains are justified by ownership forces: state, consequence selection,
  liveness, authority, transport, presentation, and model-serving lifecycle.
- Compatibility adapters may carry requests and preserve response shapes, but
  must not become semantic owners.
- Dependency injection should expose ports at environmental or domain
  boundaries, not replace workflow ownership with callback assembly.
- Rendered or transported representations must not become canonical state.

Current follow-through plan:

- keep the landed lifecycle domain narrow and model-serving scoped
- treat daemon/RPC, CLI, and host lifecycle paths as adapters over the domain
  contract
- reconcile remaining backend lifecycle gaps through focused follow-ups rather
  than reopening the ownership decision
- use `tasks/open/260614-architecture-follow-through-coordination.md` to track
  follow-through and child-task extraction

Stale-prone content:

- exact current module homes in the `Domain Map`
- current aliases and command names
- candidate module paths for backend lifecycle
- task ids and sequencing notes
- open questions tied to a single migration slice

Update expectations:

- When implementation accepts a decision from this document, either promote it
  into runtime direction/ownership docs or mark it accepted here with evidence.
- When a migration slice closes, remove or downgrade any temporary plan that no
  longer guides work.
- When a new subsystem does not fit a domain, add the force or record why the
  existing domain map is insufficient.
- When a new compatibility path appears, name the semantic owner separately from
  the adapter.

## Migration Strategy

1. Use this document as a critique artifact.
2. Classify existing modules by proposed domain before moving more code.
3. Apply the model to model backend lifecycle first. Done.
4. Update `docs/runtime-direction.md` with accepted target-shape language. Done
   for the initial lifecycle proof slice.
5. Update `docs/runtime-ownership.md` with accepted contribution guidance. Done
   for the initial lifecycle proof slice.
6. Continue architecture follow-through only where slices can name their owning
   domain, evidence obligations, and coordination task.

## Exit Criteria

This draft is good enough to stop broad architecture review when:

- durable target-shape guidance is separated from current migration notes
- remaining uncertainties are either in the decision ledger, `Not
  Decision-Ready Yet`, or a follow-up task
- accepted guidance has an obvious destination in `docs/runtime-direction.md` or
  `docs/runtime-ownership.md`
- the first backend lifecycle implementation slice can name its owning domain,
  ports, state owner, failure owner, and evidence obligations
- no critique note is required as warm context to understand the next task

At that point, stop expanding this document. Promote accepted guidance, split
implementation work, and let future slices update the architecture only when
they produce new evidence.

Current status: the broad review exit criteria have been met for the first
backend lifecycle proof slice. Future architecture work should use the
coordination task and focused follow-ups, not expand this draft as the primary
todo surface.

## Verification Evidence

The architecture is doing its job only if future changes become easier to place
and harder to mis-own.

Evidence needed:

- Test: backend lifecycle domain tests cover external mode, managed-local
  start, health failure, status, stop blocked by active runs, restart, stale
  config, and provider-failure handoff before daemon adapter tests assert
  compatibility shapes.
- Test: daemon/RPC backend operations preserve legacy and envelope response
  compatibility while deriving both from the same lifecycle command/result
  contract.
- Test: `toas step` behavior remains owned by transcript reconciliation,
  operator semantics, durable state, model invocation/capabilities, and
  projection rather than by CLI, host, or daemon wrappers.
- Test: host-death scenarios prove host liveness does not directly decide
  activity terminality.
- Test: stream reconnection after terminal events replays status/events without
  producing new consequence work.
- Test: projection/rendering failures do not mutate durable graph records.
- Manual scenario: run `TOAS_RPC_MODE=off toas backend status` once local
  backend support exists and confirm the local path does not require daemon
  ownership.
- Manual scenario: run a backend through daemon compatibility and confirm
  operator-visible output stays compatible while the lifecycle domain remains
  the semantic source.
- Trace/example: show config changes while a backend is alive and confirm status
  reports stale/restart-required instead of silently applying or restarting.
- Trace/example: show provider failure and process death as separate facts unless
  lifecycle explicitly observes the process failure.

Must not regress:

- prior durable history is never mutated
- rendered transcript text is never canonical durable truth
- transport envelopes and legacy fields never define semantic success
- direct user intent and model-addressable authority remain distinct
- host loss alone never marks an activity succeeded, failed, or cancelled
- backend health success never becomes a durable availability guarantee
- config changes never silently restart or reconfigure an already-running model
  backend
- model provider failure never mutates backend lifecycle state without explicit
  lifecycle observation or policy

## Risk Register

These risks should stay visible while moving from proposal to implementation.

| Risk | Why brittle | Mitigation |
| --- | --- | --- |
| `runtime/` becomes the new broad module | Domain names can be documented while code still accretes in one package | Require each new slice to name its owning domain and tests before moving code |
| Architecture vocabulary hides ordinary code | Terms like domain, port, lifecycle, and policy can become ceremony | Prefer narrow modules and functions until a real ownership force needs an object |
| Dependency injection becomes callback assembly | Injected workflow steps can make callers own behavior indirectly | Inject environmental/domain ports; let controllers own command policy |
| Backend lifecycle overfits the current LLM backend | The current model-serving shape may not match future provider/process needs | Keep scope model-serving, name non-LLM supervision pressure as a new force |
| Hidden global process state survives in adapters | Daemon/host compatibility can keep cached process truth by accident | Give adapters transport/cache state only; lifecycle registry owns live process truth |
| Transcript/state ambiguity leaks into execution | Rendered text, branch alignment, and durable graph facts can blur | Preserve reconciliation handoff and test branch-or-refuse behavior |
| Activity durability is under-specified | Live stream state and durable activity facts can be mistaken for each other | Split live-only, crash-surviving, and replayable facts before broad activity changes |
| Human recovery path is unclear | If reconciliation, lifecycle, or policy refuses, operators need a repair route | Surface diagnostics that name the owner and preserve durable state for manual repair |
| Agent misuse risk | Agents may optimize for passing local tests by routing around authority or adapters | Add must-not-regress tests for authority lanes, transport truth, and durable mutation |
| Token/cost risk | More architecture ceremony can cause agents to over-read or over-refactor | Use the domain map to choose the smallest slice and stop after evidence obligations are met |
| Compatibility path masks domain failure | Legacy response fields may appear successful while the domain result failed | Generate compatibility payloads from domain results and test mismatch handling |
| Decision drift | Proposed decisions may become de facto accepted without evidence | Require decision status updates when implementation lands or when follow-up tasks are split |

## Remaining Questions

- Is "operator semantics" too broad, or should frontier resolution, slash
  commands, and consequence execution be separate domains?
- Should transcript alignment be its own package, or is it part of operator
  semantics?
- Should activities/streams be independent of host supervision, or is that
  separation artificial?
- Is the split between model invocation and model backend lifecycle sufficient
  to keep "backend" model-serving scoped?
- Is request dispatch a transport concern, an application concern, or a thin
  boundary between them?
- What domain owns configuration precedence after values are loaded?
- Where should presentation rendering stop and projection semantics begin?
- Which current `runtime/` modules are already in the wrong future domain?
- Where is current dependency injection proving good boundaries, and where is it
  hiding missing objects?

## Decision Ledger

This section extracts decisions implied by the draft and critique passes. It is
not yet an accepted architecture decision record; statuses show how settled each
item currently is.

Decision status meanings:

- `Accepted by implementation`: use as accepted guidance; implementation
  evidence has landed, though follow-up gaps may remain.
- `Accepted in draft`: use as working guidance unless implementation evidence
  disproves it.
- `Proposed`: plausible and actionable, but still needs evidence from a slice or
  another focused review pass.
- `Unresolved`: do not implement as if settled; keep the question visible or
  split a task to settle it.
- `Rejected`: keep only when the rejected path is likely to be suggested again.

| Decision | Status | Forces | Consequences | Rejected alternatives | Evidence needed | Follow-up owner/pass |
| --- | --- | --- | --- | --- | --- | --- |
| Frame TOAS as a durable transcript/event substrate with live runtime hosts around it | Proposed | Avoid CLI/daemon/runtime-package as accidental center; preserve transcript/event invariants | Future refactors should orient around state and consequence semantics, not entrypoints | CLI-first, daemon-first, or generic runtime-package-first framing | Whether future implementation slices become easier to place | Author / Architect |
| Prevent `runtime/` from becoming the next broad module | Proposed | Runtime bloat by accretion would repeat the old CLI/daemon problem | New work should name a domain before moving code | Continue moving semantic code into `runtime/` without finer domains | Backend lifecycle extraction pressure | `400` / Architecture critique |
| Use force-based domain boundaries rather than noun buckets | Proposed | Noun buckets hide ownership and failure semantics | Domain names should expose why the boundary exists | Package/file grouping by current names alone | Whether module classification exposes clearer owners | Force Mapper |
| Rename `Transcript And Alignment` to `Transcript Reconciliation` | Accepted in draft | Force is reconciling edited working text with canonical history | Branch ambiguity and edited prior content get clearer ownership | Keep alignment-focused name | Validate against step/alignment tests and handoff shape | Split/Merge / Flow |
| Keep Transcript Reconciliation separate from Operator Semantics | Proposed | Mapping edited text to history differs from choosing the next consequence | Needs explicit handoff: reconciled nodes, selected frontier, parentage decision | Merge alignment/frontier/consequence into one operator domain | Handoff object and branch ambiguity tests | State Ownership / Flow |
| Keep Operator Semantics as owner of step meaning | Proposed | Frontier consequence policy must not live in surfaces or transports | Operator owns consequence selection; Durable State owns recorded facts | Let CLI/host/daemon decide execution meaning | Concrete `toas step` flow tests | Flow Architect |
| Split Model Invocation from Model Backend Lifecycle | Accepted in draft | Provider calls and model-serving process supervision have different state and failure forces | Model call failure is not automatically lifecycle failure; lifecycle remains model-serving scoped | One broad `Model And Backend` domain | Backend lifecycle implementation slice | Split/Merge / Failure |
| Scope `backend` to LLM/model-serving, not generic worker supervision | Accepted in draft | Current shape is LLM-focused; broader scope collides with host/activity supervision | Future generic worker lifecycle needs another domain | Treat backend as generic process/service supervisor | Watch for non-LLM backend pressure | Force Mapper |
| Keep Session Host Supervision separate from Activity Lifecycle | Proposed | Host owns attachment/liveness; activities own run terminality | Host death is not automatically run failure | Merge host process state with run state | Host-dies-mid-activity policy/tests | Failure Ownership |
| Evaluate invariant: host liveness is not activity terminality | Proposed | Attachment loss should not rewrite run outcome | Activity Lifecycle must decide continue/cancel/fail/orphan | Host death directly marks run failed/cancelled | Explicit host-loss behavior | Failure Ownership |
| Split Surface Adapters from Projection And Rendering | Proposed | Parsing/user wording differs from semantic-safe projection | Projection text remains display state, not canonical state | Keep CLI parsing/render/projection as one presentation bucket | Projection contract tests independent of CLI | Split/Merge |
| Add Effective Policy And Authority as a domain | Proposed | Config, owner identity, grants, and authority provenance are scattered | Need one resolved-policy path; policy consumption remains separate | Leave precedence scattered across CLI/operator/tools/host | Inventory current policy resolution paths | State Ownership |
| Transport and protocol carry meaning but do not own it | Proposed | RPC/envelope compatibility must not become semantic truth | Envelopes and legacy fields stay adapter concerns | Let daemon/RPC response shapes define domain meaning | Compatibility handling rules | Failure Ownership |
| Prefer stdio/session host as primary local persistent path while daemon remains compatibility | Proposed | Session-rooted ownership and low ambient service reliance | Daemon should shrink toward adapter role | Daemon as architectural center | Continued local-host parity | Runtime Direction / `525` follow-ons |
| Move model backend lifecycle to a runtime-owned workspace/domain boundary with daemon/host adapters | Accepted by implementation | Backend lifecycle is primary enough not to be daemon-owned; process state needs explicit ownership | The first proof slice landed; daemon/RPC, CLI, and stdio-host paths now adapt to the lifecycle domain | Keep daemon-owned backend lifecycle singleton | Landed `ModelBackendLifecycle` and adapter tests; remaining registry/keying questions tracked separately | Architecture coordination / backend lifecycle follow-ups |
| Use a common backend lifecycle command/result contract behind CLI, daemon, and later host adapters | Accepted for current backend commands | Compatibility adapters must not become semantic owners; local and RPC paths need parity | Adapter response shapes should continue deriving from lifecycle request/result objects | Let each adapter assemble lifecycle behavior independently | Current request/result contract and adapter wiring landed; revisit if new backend operations appear | Flow Architect / Transport And Protocol |
| Decide explicit keying for model backend process state | Unresolved | Avoid singleton leakage while preserving compatibility | Must choose workspace-only or workspace plus backend configuration identity | Retain daemon global singleton | Usage expectations and compatibility risk | State Ownership / backend lifecycle task |
| Include startup-config identity or stale marker in backend process state | Proposed | Workspace-only running state cannot prove which startup config produced the live process | `backend status` needs stale/restart-required vocabulary; config changes do not silently apply | Workspace-only key with no stale marker; silent restart/apply on config change | Config-change-while-running status tests | State Ownership / Failure Ownership |
| Treat config change as not backend restart | Accepted as invariant; stale reporting unresolved | Startup-only lifecycle config differs from runtime-adjustable invocation policy | Live backend must not silently adopt config changes; stale/restart-required status remains a follow-up | Auto-restart/apply on config change | Current code has no silent restart/apply path; needs stale status tests | Failure Ownership / backend lifecycle follow-up |
| Treat backend health as observation, not durable availability | Accepted for current lifecycle slice | Health can pass and process can later die | Lifecycle owns status; Model Invocation owns call failure | Treat successful health check as durable proof | Start health and process-exit status behavior are tested; durable availability is not inferred | Failure Ownership |
| Treat provider failure as Model Invocation failure unless lifecycle explicitly observes backend failure | Proposed | Provider/client errors and managed process lifecycle observations have different causes | Model Invocation may query lifecycle, but must not mutate lifecycle state implicitly | Automatically restart or mark backend failed from model-call errors | Provider-failure and process-death handoff tests | Failure Ownership / Model Invocation |
| Inject ports, not implementation steps | Accepted as guidance; monitor for regressions | DI should expose environment/cross-domain boundaries, not replace ownership | Avoid callback soup; introduce domain objects/controllers when wiring gets noisy | Service-locator/request-assembly as architecture | Backend lifecycle port design landed with process/health/event/active-run/time ports | Port / DI Architect |
| Keep critique sections as notes until decisions are accepted | Accepted process decision | Avoid premature law while preserving discoveries | Later pass can promote accepted decisions into runtime-direction/ownership docs | Immediately promote every critique note to normative guidance | Completion of critique loop | Architecture Decision Extractor |

Decision recording follow-up:

- Promote accepted-in-draft decisions into `docs/runtime-direction.md` only when
  they describe durable target shape rather than temporary migration sequence.
- Promote accepted contribution guidance into `docs/runtime-ownership.md` only
  when it can tell a future contributor where code/tests belong.
- Keep package placement and host exposure unresolved until the backend
  lifecycle implementation slice supplies evidence.
- Split a follow-up task when a decision needs implementation discovery before
  it can be accepted; do not let it remain hidden as prose.
- Downgrade a proposed decision if tests require broad adapter ownership,
  callback assembly, or silent state duplication to make it pass.

### Not Decision-Ready Yet

These items are important but do not yet fit as decisions:

- Active async run durability boundary: needs a clearer inventory of which run
  facts survive crash and which are live-only.
- Effective policy resolution path: the force is identified, but the concrete
  resolver shape is not.
- Compatibility response precedence: the draft implies envelope/domain truth
  should win, but exact legacy fallback rules need protocol-specific review.
- Cancellation idempotency and terminal convergence: the need is clear, but the
  policy shape belongs in Activity Lifecycle work.
- Transcript reconciliation handoff object: the split is recommended, but the
  handoff shape still needs design.
- Model Invocation / Model Backend Lifecycle failure handoff: provider failure
  is not automatically lifecycle failure, but the query/escalation path is not
  specified.

## Critique Notes

The following sections preserve raw findings from focused review passes. They
are intentionally not final contracts; use them as source material for future
decisions and implementation tasks.

### State Ownership

This section records state-ownership concerns raised during critique. It is not
yet the final ownership table.

| State | Current or likely home | Ownership concern |
| --- | --- | --- |
| Durable event graph | `.toas/events.jsonl`, graph append/query APIs | Canonical facts must remain append-only and replayable; indexes and projections must not become competing truth. |
| Message/control/tool/model-call records | durable event graph | Prior records must not be mutated; derived views must preserve parentage, role, and record-kind boundaries. |
| Backend lifecycle records | durable event graph | Lifecycle facts should survive even when live model-serving process state is lost. |
| Working transcript | `.toas/session.md` or selected surface | It is user proposal text, not canonical truth; reconciliation must own branch creation from edited prior content. |
| Selected surface/session binding | durable records plus explicit request/host overrides | Precedence must be deterministic after restart and must not be hidden in adapter state. |
| Effective config and authority | config files, durable overrides, env, grants, owner identity, transcript/control modifiers | The architecture needs one resolved-policy path; scattered precedence rules are a correctness risk. |
| Active async runs | activity lifecycle/store | The draft must distinguish crash-surviving durable facts from live in-memory activity state. |
| Stream events and offsets | activity store plus transport envelopes | Event order and terminality must not be duplicated by subscribers or protocol envelopes. |
| Cancellation state | activity lifecycle | Cancellation must converge to an explicit terminal meaning; host/daemon loss should not decide it ad hoc. |
| Host records and host process state | `.toas` host state plus live `toas host serve` process | Host death may end attachment, but should not silently redefine durable activity meaning. |
| Daemon process state | pid/socket files plus live daemon process | Compatibility state must remain adapter-only and must not become semantic source of truth. |
| Model backend process state | currently daemon global; target model backend lifecycle domain | Needs explicit keying: workspace only, or workspace plus backend configuration identity. |
| Model backend health | external probe result | Health is short-lived observation unless explicitly recorded as a lifecycle fact. |
| Capability grants | config/durable grant records/transcript/control lanes | Authority provenance must remain visible and recomputable. |
| Imported/result projection blocks | stdout/transcript projection | Projection text is display state; durable tool/result facts remain source of truth. |
| Indexes and caches | graph/index helpers, runtime caches, client offsets | Must be safely discardable or explicitly invalidated; never canonical. |
| Request/response envelopes | protocol adapters and clients | Envelopes carry semantic results but are not themselves durable truth. |

Top unresolved ownership risks:

- Active async run state is only partly durable in the architecture story.
- Model backend process state needs explicit keying.
- Effective policy/authority is newly named but not yet specified as a single
  resolution path.
- Projection and transcript reconciliation can still blur if rendered text is
  treated as canonical.
- Session host supervision and activity lifecycle need a hard restart/loss rule.
- Daemon compatibility globals and pid/socket files must stay adapter-only.

### Flow

This section records cross-domain flow concerns raised during critique. It is
not yet the final flow contract.

| Flow | Participating domains | Boundary crossings | Final consequence owner | Ambiguity risk |
| --- | --- | --- | --- | --- |
| User edits transcript, then steps | Surface Adapter, Transcript Reconciliation, Operator Semantics, Effective Policy And Authority, Capabilities or Model Invocation, Durable State, Projection And Rendering | `step` request enters through CLI/host; reconciliation aligns transcript with history; operator chooses consequence; capability/model invocation performs work; durable state records facts; projection emits output | Operator Semantics owns what the step means; Durable State owns recorded facts | Frontier classification can blur with reconciliation; projection must not become canonical truth |
| Model starts an async tool run | Operator Semantics, Activity Lifecycle, Capabilities, Effective Policy And Authority, Durable State, Projection And Rendering, optional Transport And Protocol | async consequence creates activity; capability execution runs under resolved policy; stream/status events emit; durable tool/activity facts are recorded where required | Activity Lifecycle owns live status/terminality; Capabilities own tool result; Durable State owns persistent facts | Model-addressable authority vs user/operator authority can blur; stream events can be mistaken for durable facts |
| Subscriber reconnects after terminal event | Transport And Protocol, Activity Lifecycle, Projection And Rendering | subscriber sends run id plus offset/sequence; transport carries request; activity lifecycle returns replayable events and terminal status; projection renders final state | Activity Lifecycle owns terminality and replay semantics | Transport envelopes or clients may reinterpret child-lane completion as whole-run terminality |
| Host dies mid-activity | Session Host Supervision, Activity Lifecycle, Transport And Protocol, Durable State, Projection And Rendering | process liveness changes; host record becomes stale or cleared; activity lifecycle decides continue/cancel/fail/orphan policy; clients reconnect through another adapter if available | Activity Lifecycle owns activity outcome; Session Host Supervision owns attachment/liveness only | Host loss can be mistaken for run failure without an explicit activity policy |
| Config changes while backend is alive | Effective Policy And Authority, Model Invocation, Model Backend Lifecycle, Durable State, Surface Adapter | config file or durable override changes; effective policy recomputes; future model calls consume applicable policy; backend lifecycle decides whether process state is stale or requires explicit restart/apply | Effective Policy owns resolved config; Model Backend Lifecycle owns running process applicability | Runtime-adjustable invocation policy can blur with startup-only backend process policy |
| Backend health passed, then process dies | Model Backend Lifecycle, Model Invocation, Durable State, Surface Adapter, optional Transport And Protocol | process exits; status/health probe observes state; lifecycle reports failed/stopped detail; durable lifecycle fact may be recorded; model invocation may fail if a call hits the dead backend | Model Backend Lifecycle owns process status/health interpretation; Model Invocation owns generation failure semantics | Health success can be mistaken for durable availability guarantee; provider call failure can be mistaken for lifecycle decision |

Flow-derived invariants to evaluate:

- Host liveness is not activity terminality.
- Transport envelopes are not semantic truth.
- Projection is not durable state.
- Config change is not backend restart.
- Backend health is observation, not ownership.
- Activity terminality belongs to Activity Lifecycle, not subscribers or
  adapters.

### Failure Ownership

This section records failure-mode ownership concerns raised during critique. It
is not yet the final failure contract.

| Failure mode | Detects | Records | Decides recovery | Exposes to operator | Durable meaning changes | Must not hide |
| --- | --- | --- | --- | --- | --- | --- |
| Host dies mid-activity | Session Host Supervision via process/owner liveness; clients via broken stdio | Host state may clear or stale records; Activity Lifecycle records only if policy emits terminal event | Activity Lifecycle decides run outcome; Session Host Supervision decides attachment loss | Surface Adapter, Transport error, or watch/status view | None unless Activity Lifecycle records cancel/fail/orphan terminality | Host death must not silently become run success or failure |
| Daemon/RPC stale endpoint | Transport And Protocol health check or request failure | Adapter may clean pid/socket; no semantic durable record by default | Transport decides reconnect/fallback; domain decides semantic retry if any | CLI daemon status or RPC error | None | Transport fallback must not mask semantic failure |
| Stale daemon compatibility response shape | Transport/adapter schema handling | Usually diagnostic only | Compatibility adapter chooses legacy/envelope fallback; domain meaning should not change | Surface Adapter if response cannot be consumed | None | Legacy fields must not incorrectly override envelope/domain truth |
| Transcript branch ambiguity | Transcript Reconciliation during alignment | Durable State records branch/head/control only if operation proceeds | Transcript Reconciliation and Operator Semantics choose branch parent or refuse | CLI/stdout diagnostic or transcript projection | New branch/head records if accepted; otherwise none | Prior history must never be mutated or silently reparented |
| Edited prior aligned content | Transcript Reconciliation | Durable State appends branch content | Transcript Reconciliation owns branch creation semantics | Projection/stdout/history | New branch/head facts | Edit must not be treated as undo or mutation |
| Subscriber reconnects after terminal event | Transport receives watch/subscribe; Activity Lifecycle checks run/event state | No semantic record unless reconnect diagnostics exist | Activity Lifecycle returns replay/terminal response | Watch/subscribe output | None | Terminal consequence must not be replayed as new work |
| Child lane done mistaken for run done | Activity Lifecycle and event classification | No durable change if handled correctly | Activity Lifecycle owns whole-run terminality | Surface rendering | None if correct; wrong terminal state if bug | `tool_done` or `llm_done` must not imply `run_done` |
| Cancellation requested during active run | Surface/Transport accepts cancel; Activity Lifecycle checks run state | Activity Lifecycle records cancellation intent/status/terminality where designed | Activity Lifecycle decides transition and escalation | `cancel`, `watch`, stream events | Cancel/cancelling/cancelled/failure facts if durable | Cancel must not be dropped or reported terminal before convergence |
| Cancellation after terminal event | Activity Lifecycle detects terminal run | Usually no new durable change, unless policy records idempotent no-op | Activity Lifecycle decides idempotent response | Surface status | None | Terminal activity must not be revived or mutated |
| Config changes while backend alive | Effective Policy And Authority detects config/override change; Model Backend Lifecycle detects mismatch if queried | Durable config override if changed through operator; lifecycle record only on lifecycle action | Effective Policy owns resolved values; Model Backend Lifecycle decides stale/restart-required status | `/config`, backend status, diagnostics | Config meaning changes; live process meaning does not unless restarted/applied | Live backend must not silently restart or inherit startup-only changes |
| Backend startup config changed | Effective Policy And Authority; Model Backend Lifecycle | Config change durable; lifecycle record only on explicit restart/apply | Model Backend Lifecycle decides whether running process is stale | Backend status/detail | Config changes; process state unchanged | Status must not pretend running process has new startup settings |
| Backend health passed then process dies | Model Backend Lifecycle via poll/health/status; Model Invocation via failed call | Lifecycle may record failed/stopped status; Model Invocation records call failure if generation was attempted | Model Backend Lifecycle owns lifecycle state; Model Invocation owns generation failure semantics | Backend status/detail or generation error | Lifecycle failure fact if recorded; model-call failure if call attempted | Earlier health success must not be treated as durable availability |
| Model call fails because backend died | Model Invocation detects provider/client failure | Model-call failure record | Model Invocation decides retry policy; Model Backend Lifecycle may be queried explicitly | Step output/result/error | Model-call failure fact | Failure must not be hidden behind backend restart unless explicit retry policy says so |
| Effective authority cannot be resolved | Effective Policy And Authority | Diagnostic; durable only if bad config/control was appended | Effective Policy refuses or falls back by explicit rule | Surface diagnostic | None unless config/control record already exists | Permissions must not silently widen |
| Capability denied by policy | Capabilities using Effective Policy And Authority | Tool result/failure record where attempted consequence is durable | Capabilities decide denial result; Operator Semantics owns consequence shape | Result/projection/watch stream | Tool denial fact if attempted | Denied command must not run through another lane |
| Projection/rendering failure | Projection And Rendering | Diagnostic only unless explicit operator result is recorded | Projection/surface chooses fail-safe display | Surface diagnostic | None | Durable state must not mutate to repair display failure |

Top unresolved failure ownership gaps:

- Host death policy for active activities is not explicit enough.
- Config changes must not apply to already-running model backend processes
  unless explicit restart/apply occurs.
- Compatibility response handling needs a rule that envelope/domain truth wins
  over stale legacy fields.
- Transcript branch ambiguity needs an explicit fail-safe: branch or refuse,
  never mutate.
- Cancellation needs documented idempotency and terminal convergence rules.
- Model Invocation and Model Backend Lifecycle need a failure handoff rule:
  provider failure is not automatically lifecycle failure.

### Split/Merge

This section records soft-boundary critique. These are recommendations to test
against implementation slices, not final package-layout decisions.

| Boundary | Keep split because | Merge because | State implication | Failure implication | Testability implication | Naming implication | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Transcript Reconciliation vs Operator Semantics | Reconciliation answers what edited text corresponds to in durable history; operator semantics answers what unresolved frontier means next | Frontier classification depends on transcript shape and parentage, so the handoff can become awkward | Split keeps proposal/alignment state separate from consequence state | Split gives branch ambiguity a clear owner | Reconciliation can be tested without model/tool consequence logic | `Transcript Reconciliation` is clearer than `Transcript And Alignment` | Keep split; define handoff as reconciled working nodes, selected frontier, and parentage decision |
| Model Invocation vs Model Backend Lifecycle | Invocation owns provider calls/request shaping/response normalization; lifecycle owns managed model-serving process state and health | Both share backend/model config and failures can appear together operationally | Split keeps live process state out of model-call audit state | Provider failure is not automatically lifecycle failure | Model calls and process lifecycle can be tested independently | Use `Model Invocation` and `Model Backend Lifecycle` | Keep split |
| Session Host Supervision vs Activity Lifecycle | Host owns attachment, owner identity, and process liveness; activities own run state, stream events, cancellation, and terminality | Local host physically carries activity streams, so implementation can feel coupled | Split prevents host process state from becoming activity truth | Host death is attachment loss; Activity Lifecycle decides run outcome | Host liveness and activity terminality can be tested separately | Prefer `Session Host Supervision` and `Activity Lifecycle` | Keep split; add invariant that host liveness is not activity terminality |
| Surface Adapters vs Projection And Rendering | Surface adapters parse commands and choose user-facing wording; projection renders semantic state safely | CLI code often parses and renders in the same wrapper | Split keeps projected text from becoming canonical state | Rendering failure should not alter semantic outcome; parse failure is a surface concern | Projection can be contract-tested independently of CLI parsing | Use `Surface Adapters` and `Projection And Rendering` | Keep conceptual split; package split can follow later |

Split/merge recommendations to evaluate:

- Keep Transcript Reconciliation separate from Operator Semantics, but make the
  handoff object explicit.
- Keep Model Invocation separate from Model Backend Lifecycle.
- Keep Session Host Supervision separate from Activity Lifecycle.
- Keep Surface Adapters separate from Projection And Rendering, even if the
  first implementation remains in nearby modules.

### Port / DI

This section records dependency-boundary critique using the rule: inject ports,
not implementation steps.

| Domain | Acceptable ports | Do not inject | Smell | Easy fake | Semantic leakage risk |
| --- | --- | --- | --- | --- | --- |
| Durable State | Filesystem/append stream, lock/atomic-write primitive, clock/id source if needed | Record interpretation phases, projection builders, operator consequence callbacks | CLI/output/render functions passed into graph append/query | In-memory event log | Transport envelope or rendered transcript becomes graph input |
| Transcript Reconciliation | Durable state reader, transcript text reader, selected-surface resolver | Model generation, tool execution, operator consequence selection | Injecting `execute_plan`, `generate_assistant_message`, or activity store | Fixed transcript text plus in-memory event log | Effective tool permission or model policy influences branch alignment |
| Operator Semantics | Reconciliation result, effective policy resolver, capability port, model invocation port, durable write port, activity lifecycle port | CLI argv parsing, daemon request handlers, raw filesystem transcript paths, low-level HTTP client | Many phase callbacks passed separately instead of a cohesive consequence runner | Fake capability executor, model invoker, durable recorder | Transport response shape decides consequence semantics |
| Activity Lifecycle | Activity store, clock/sleep, worker runner, stream emitter, durable event writer for durable facts | Host liveness as terminality decision, CLI renderer, capability authorization internals | Host process object or daemon store global as activity truth | In-memory activity store with deterministic clock | Subscriber offset or transport disconnect decides run status |
| Capabilities | Resolved authority/policy, filesystem/process execution ports, workspace boundary checker, progress/event emitter | Transcript reconciliation, model invocation, CLI/daemon fallback path | Tools read raw config/env and resolve permissions themselves | Fake shell/process runner, fake file system, fake authority decision | Denied model-addressable command reroutes through user-intent shell lane |
| Model Invocation | Resolved model config, provider client, clock/retry policy, model-call recorder | Backend process controller internals, daemon RPC client as semantic path, operator prompt-rendering phases | Model invocation calls `backend_start` automatically on provider failure | Fake provider client returning normalized responses/errors | Health probe result treated as model-call success guarantee |
| Model Backend Lifecycle | Process spawner, health probe, active-run query, lifecycle event writer, clock/sleep, workspace/config key resolver | Model request shaper, prompt builder, generic worker supervisor, CLI output formatter | `subprocess.Popen` globals and daemon `_MANAGED_BACKEND` state used as domain model | Fake process table, health probe, event writer, active-run query | Config change implicitly restarts backend; model invocation failure mutates process state |
| Session Host Supervision | Process liveness checker, host record store, stdio reader/writer, request handler port, owner identity provider | Activity terminality policy, model backend process state, durable graph append semantics | Host stop code directly cancels runs or marks them terminal | Fake owner liveness, host record store, stdio frames | Host death decides activity outcome |
| Effective Policy And Authority | Config file reader, durable override reader, env provider, owner identity provider, grant records | Capability execution, model HTTP calls, backend process mutation, transcript branch decision | Consumers pass execution callbacks into policy resolver | Fixed config/env/grants/owner identity sources | Consumers recompute precedence differently |
| Transport And Protocol | Byte stream/socket/named-pipe ports, encoder/decoder, request router port, compatibility schema handlers | Domain operation internals, graph appenders, model/capability implementations | Request assembly constructs application behavior from many callbacks | In-memory transport frames and fake request router | Envelope/legacy response fallback chooses semantic truth |
| Surface Adapters | Argument parser, domain command ports, presenter/renderer ports, environment/cwd provider | Graph storage internals, model HTTP client, backend process registry, activity store internals | CLI wrapper imports daemon, or host request handling imports broad `toas.cli` | Fake command port plus captured output | Command wording or stdout shape changes domain behavior |
| Projection And Rendering | Semantic records/views, projection policy, escaping/fence formatter, display style if needed | Durable append, tool execution, model invocation, backend lifecycle mutation | Renderer repairs missing provenance by mutating source records | Fixed semantic record list | Rendered text feeds back as canonical state without reconciliation |

Cross-cutting DI rules:

- Inject environmental ports: time, filesystem, process, network, byte streams.
- Inject domain ports: capability executor, model invoker, lifecycle controller,
  durable recorder.
- Do not inject internal steps of a workflow when a domain object should own the
  workflow.
- If a constructor or function takes many same-level callbacks, ask which
  controller or policy object is missing.
- Test doubles should fake ports, not private phases.

### Implementer Continuity

This section records what an implementer still needs before turning the proposal
into code. It is not yet a final API contract.

The clearest actionable implementation path is `Model Backend Lifecycle`.

First implementation slice sketch:

- extract model-serving process state and lifecycle mechanics out of
  `toas.daemon.backend_lifecycle`
- keep daemon as a compatibility adapter
- preserve `toas backend ...` output
- preserve daemon RPC legacy plus envelope response compatibility
- add domain tests before adapter tests

Probable module target:

```text
src/toas/runtime/model_backend_lifecycle.py
```

Alternative module target if avoiding further `runtime/` accretion becomes more
important:

```text
src/toas/model_backend_lifecycle.py
```

Contract shape to design:

```python
@dataclass(frozen=True)
class BackendLifecycleRequest:
    workdir: Path
    mode: str
    command: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]
    health_url: str
    health_timeout_s: float


class ModelBackendLifecycle:
    def status(self, request: BackendLifecycleRequest) -> BackendLifecycleResult: ...
    def start(self, request: BackendLifecycleRequest) -> BackendLifecycleResult: ...
    def stop(self, request: BackendLifecycleRequest) -> BackendLifecycleResult: ...
    def restart(self, request: BackendLifecycleRequest) -> BackendLifecycleResult: ...
```

Candidate ports:

- `ProcessSpawner`
- `HealthProbe`
- `LifecycleEventWriter`
- `ActiveRunQuery`
- clock/sleeper
- backend state registry

Expected first tests:

- external mode returns external/skipped behavior
- managed-local start success and health failure
- status running/stopped/failed
- stop blocked by active runs
- restart stop-then-start behavior
- lifecycle event writer called for lifecycle facts
- daemon adapter preserves legacy plus envelope shape
- CLI local path preserves current output if local backend command support lands
  in the same slice

Questions still too hand-wavy for implementation:

- Do new domains become packages now, later, or never?
- Should `Model Backend Lifecycle` live under `runtime/`, top-level `toas/`, or
  a future `toas/backends/` package?
- Is backend process state keyed by workspace only, or workspace plus backend
  configuration identity?
- Does local `toas backend ...` land with the domain extraction or as a follow-up
  adapter slice?
- Should host exposure be status-only first, all lifecycle operations, or
  deferred?
- What exactly counts as a lifecycle record for status observation, health
  failure, start/stop/restart, and stale config detection?

Implementation guardrails for the first slice:

- no package-wide rename
- no generic worker supervisor hidden behind `backend`
- keep API narrow
- use ports only for environment and cross-domain dependencies
- keep daemon as an adapter shell
- defer host exposure unless required by the local CLI path
- avoid creating a new broad process-control module with architecture language
  around it

Architectural follow-up prompts:

- `Boundary Invariant Architect`: decide whether `Model Backend Lifecycle`
  belongs under `runtime/`, top-level `toas/`, or a future backend package, and
  name the dependency that would prove that placement wrong.
- `State Ownership Architect`: settle the backend process identity key and the
  durable meaning of lifecycle observations before adding new status records.
- `Flow Architect`: walk CLI local, daemon RPC, host exposure, and model
  invocation flows separately so compatibility adapters do not become the
  semantic owner.
- `Failure Ownership Architect`: decide which start, health, process death,
  active-run, and stale-config failures change durable meaning and which only
  affect operator presentation.
- `Port / DI Architect`: turn the candidate ports into a narrow dependency
  contract and reject any injected callback that is really an implementation
  step of lifecycle policy.
- `Architecture Decision Extractor`: pull only the settled parts into the
  decision ledger; leave module placement and host exposure unresolved until the
  flow and ownership passes agree.

### Backend Lifecycle Architecture Revisit

This section revisits the implementer prompts with one architecture hat at a
time. It is scoped to `Model Backend Lifecycle`, not the whole architecture.

Boundary Invariant Architect:

- Place the first implementation where it makes semantic ownership obvious, not
  where current callers happen to live. `runtime/` is acceptable only if the
  module remains a narrow model-serving lifecycle domain; a future
  `toas/backends/` package becomes attractive once there is more than one
  backend-facing domain to group.
- Daemon code may adapt backend lifecycle requests and compatibility responses,
  but must not retain the process registry as the source of truth.
- Host exposure is not part of the first boundary unless it can reuse the same
  lifecycle command/result contract without adding host-only semantics.
- The placement is wrong if model request shaping, prompt construction, generic
  worker supervision, or daemon compatibility response rules become reasons to
  edit the lifecycle domain.

State Ownership Architect:

- The backend process identity should be at least workspace-scoped and should
  carry a startup-configuration fingerprint or equivalent stale marker. A
  workspace-only key is simpler but risks pretending that a running process
  reflects changed startup config.
- Live process handles are ephemeral and may be cached only by the lifecycle
  registry. Durable lifecycle records may describe observed facts, commands, and
  outcomes; they must not claim the process is still alive after restart unless
  re-observed.
- Effective policy may derive backend command/config inputs, but it must not
  cache or mutate live process state.
- Active-run state may block stop/restart, but Activity Lifecycle remains the
  owner of run terminality.
- Never duplicate the process registry in daemon, host, and CLI adapters. They
  may cache transport availability, not lifecycle truth.

Flow Architect:

- CLI local flow: Surface Adapter parses `toas backend ...`; Effective Policy
  resolves backend config; Model Backend Lifecycle executes status/start/stop;
  Surface Adapter renders the result. Durable State records only explicit
  lifecycle facts chosen by the lifecycle domain.
- Daemon RPC flow: Surface Adapter sends a compatibility request; Transport
  carries it; daemon adapter translates to the same lifecycle command/result;
  compatibility fields are rendered from the domain result, not vice versa.
- Host exposure flow: host may carry lifecycle requests only after the command
  contract exists. Host identity/liveness must not alter backend lifecycle
  meaning.
- Model invocation flow: Model Invocation may observe provider failure and may
  ask lifecycle for status, but it must not start, stop, restart, or mark a
  backend failed unless an explicit lifecycle policy says so.
- Responsibility becomes ambiguous if config resolution, process registry,
  health probing, and response rendering are assembled separately by each
  adapter.

Failure Ownership Architect:

- Start failure: Model Backend Lifecycle detects process spawn or health
  failure, records an explicit lifecycle result/fact if recording is part of the
  command, and exposes the failure through the caller's surface.
- Process death: lifecycle detects by polling/process observation/health probe;
  it may record a stopped/failed observation, but prior successful health checks
  remain observations, not durable availability promises.
- Active-run stop/restart block: Activity Lifecycle supplies active-run
  evidence; Model Backend Lifecycle decides whether the lifecycle command is
  blocked and exposes that decision. It must not cancel runs as a side effect.
- Stale config: Effective Policy detects changed desired config; lifecycle
  compares it to the running process identity and reports stale/restart-required
  without silently applying it.
- Provider failure: Model Invocation records model-call failure. Lifecycle may
  be queried afterward, but provider failure alone must not mutate backend
  process state.
- Compatibility failure: Transport/daemon adapters detect stale RPC or schema
  mismatch. They may fall back or report compatibility errors, but must not hide
  a domain failure behind a successful legacy payload.

Port / DI Architect:

- Accept ports for process spawning, process observation, health probing,
  lifecycle event writing, active-run queries, clock/sleep, and config identity
  derivation.
- Do not inject `start_process_then_wait_for_health`, `render_backend_status`,
  daemon response builders, model HTTP request shapers, or callback sequences
  that describe the lifecycle workflow step by step.
- A lifecycle controller should own command policy: idempotency, stale handling,
  active-run blocking, health-check interpretation, and result construction.
- Easy fakes should include an in-memory process table, scripted health probe,
  capturing lifecycle writer, fixed active-run query, and deterministic clock.
- Semantic leakage is present if a fake daemon response can pass tests while the
  lifecycle domain would have returned a different result.

Architecture Decision Extractor:

- Decision, proposed: implement backend lifecycle as a narrow model-serving
  lifecycle domain with daemon/CLI/host adapters consuming a common
  command/result contract.
  Rationale: this tests the masterplan's boundaries without expanding backend
  into generic supervision.
  Rejected alternative: keep daemon-owned process globals as lifecycle truth.
  Consequence: daemon compatibility tests should sit behind domain contract
  tests.
  Open follow-up: choose exact module/package placement.
- Decision, proposed: backend process state should include workspace plus
  startup-config identity or an equivalent stale marker.
  Rationale: workspace-only state cannot distinguish "running" from "running
  with old startup config".
  Rejected alternative: silently apply config changes or silently restart.
  Consequence: `backend status` needs stale/restart-required vocabulary.
  Open follow-up: define the fingerprint inputs and durability of stale
  observations.
- Decision, proposed: provider failure is not lifecycle failure unless lifecycle
  observes or records it.
  Rationale: model-call transport and managed-process state fail for different
  reasons.
  Rejected alternative: automatically restart or mark backend failed from model
  invocation errors.
  Consequence: model invocation may query lifecycle, but recovery policy must be
  explicit.
  Open follow-up: define the query/escalation hook between the two domains.
