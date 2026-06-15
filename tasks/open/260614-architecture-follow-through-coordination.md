Filed as: 260614-architecture-follow-through-coordination
FKA:
AKA: architecture coordination; architecture follow-through; domain workplan; top-down architecture
Legacy index:

keywords: docs, governance, active, architecture, coordination, boundaries, runtime, domain

# Architecture Follow-Through Coordination

## Current Reality

The broad architecture review has produced three working documents:

- `docs/architecture-masterplan.md` is the critique workbench and decision
  ledger.
- `docs/runtime-direction.md` is the direction-setting runtime north star.
- `docs/runtime-ownership.md` is the current contributor-facing ownership map.

The original masterplan and backend-lifecycle implementation tasks are closed.
Backend lifecycle, logging, coverage cleanup, and runtime ownership slices have
landed, but the architecture work now needs a coordination object to keep
follow-through visible without turning the masterplan back into a live task.

## Desired Reality

Architecture work should progress top-down from the accepted documents while
remaining operationally concrete.

This task coordinates a tree of subtasks. It should track which architecture
frontiers are being clarified, which have produced implementation evidence,
which have spawned focused work, and which are intentionally parked.

## Gap Analysis

Without this umbrella, architecture follow-through has two bad failure modes:

- new implementation slices can drift away from the architecture documents
  because there is no active task tying them together
- the closed architecture masterplan can quietly become a live planning surface
  again, mixing durable guidance with current todo state

This task exists to prevent both forms of slippage.

## Known Facts

- `docs/architecture-masterplan.md` explicitly says broad review should stop
  once accepted guidance has destinations and unresolved items are in a ledger,
  notes, or follow-up tasks.
- `docs/runtime-direction.md` already carries promoted north-star guidance:
  session-rooted hosts, stdio-first IPC, persistent runtimes, explicit
  supervision, and runtime internal boundaries.
- `docs/runtime-ownership.md` already carries contributor guidance for placing
  code and tests by domain ownership rather than by package habit.
- Backend lifecycle is no longer only an architectural proof candidate; it has
  landed as runtime-owned implementation behind CLI, daemon/RPC, and stdio-host
  adapters.

## Assumptions

- This umbrella is a coordination object, not a replacement architecture
  document.
- Subtasks should own concrete discovery, implementation, or promotion work.
- Architecture documents should change when implementation evidence, decision
  status, or contributor guidance changes.
- Closed umbrellas such as `400`, `525`, `374`, and `379` remain historical
  context, not active parents.

## Unknowns

- Which decisions in `docs/architecture-masterplan.md` should now be promoted
  from proposed to accepted based on landed backend-lifecycle work.
- Which unresolved items need a focused task before code changes resume.
- Whether Effective Policy And Authority, Activity Lifecycle, Transcript
  Reconciliation, or Transport/Protocol truth rules should receive the first
  architecture-driven implementation slice.
- Which architecture notes are stale enough to remove from the masterplan
  rather than preserve as historical critique material.

## Investigations

- Reconcile the three architecture docs against the current implementation
  state after backend lifecycle and logging landed.
- Triage the masterplan decision ledger:
  accepted by implementation, still proposed, unresolved, stale, or split to
  follow-up.
- Inventory the `Not Decision-Ready Yet` list and decide which items require
  subtasks.
- Survey open tasks for existing homes before opening new architecture-driven
  follow-ups.

### 2026-06-14 Initial Architecture Reconciliation

Read:

- `docs/architecture-masterplan.md`
- `docs/runtime-direction.md`
- `docs/runtime-ownership.md`
- `src/toas/runtime/model_backend_lifecycle.py`
- backend lifecycle adapter call sites in CLI, daemon, and host request paths
- backend lifecycle/domain and adapter-adjacent tests

Findings:

- `runtime-direction.md` and `runtime-ownership.md` already reflect the accepted
  backend-lifecycle ownership result: model backend lifecycle is runtime-owned,
  model-serving scoped, and distinct from model invocation.
- `architecture-masterplan.md` still contains proof-slice phrasing that treats
  backend lifecycle as pending in several places. That content is now stale as
  migration plan, though still useful as historical rationale.
- `ModelBackendLifecycle` is a narrow model-serving lifecycle domain with ports
  for process spawn, health probe, lifecycle event writer, active-run query,
  sleep, and clock.
- CLI local backend commands, daemon/RPC backend handlers, and stdio-host
  request handling now adapt to the lifecycle domain instead of owning the
  lifecycle semantics directly.
- Lifecycle facts can be written as durable `backend_lifecycle` records through
  the graph writer.
- Active-run blocking exists for stop/restart without making backend lifecycle
  own activity terminality.

Settled or mostly settled masterplan decisions:

| Decision area | Current read | Evidence |
| --- | --- | --- |
| Move backend lifecycle out of daemon ownership | accepted by implementation | `ModelBackendLifecycle` plus CLI/daemon/host adapters |
| Keep backend scoped to model-serving lifecycle | accepted by implementation | lifecycle request/result shape is process/health/status/restart, not generic worker supervision |
| Use common lifecycle command/result contract behind adapters | accepted for current backend commands | `BackendLifecycleRequest`, `BackendLifecycleResult`, `result_to_dict`, request handlers |
| Inject ports, not implementation steps | accepted for lifecycle slice | lifecycle owns command policy; ports are environmental/domain boundaries |
| Backend health is observation, not durable availability | partially accepted | status reads process state; health is used for start success, but no broader availability guarantee is recorded |
| Config change is not backend restart | accepted as invariant, not implemented as stale detection | no auto-restart path found; no stale/restart-required fingerprint yet |

Still-open architecture gaps:

| Gap | Why it remains open | Likely owner |
| --- | --- | --- |
| Backend process identity/keying | lifecycle state is per `ModelBackendLifecycle` instance; no registry keyed by workspace plus startup config identity yet | Model Backend Lifecycle / State Ownership |
| Stale startup config detection | request carries config-derived command/env/cwd/health data, but running process identity is not compared to a fingerprint | Model Backend Lifecycle plus Effective Policy |
| Provider failure handoff | docs say provider failure is Model Invocation unless lifecycle observes process failure; no explicit query/escalation contract yet | Model Invocation / Model Backend Lifecycle |
| Effective Policy And Authority resolver shape | config, grants, owner identity, env, workspace roots, and backend startup/runtime distinctions remain distributed | Effective Policy And Authority |
| Activity live-vs-durable state | active-run blocking exists, but crash-surviving activity facts vs live store state remain under-specified | Activity Lifecycle |
| Host death vs activity terminality | docs carry the invariant, but the policy deserves a focused contract pass | Session Host Supervision / Activity Lifecycle |
| Transcript reconciliation handoff | still named as a split, but the concrete handoff object remains undesigned | Transcript Reconciliation / Operator Semantics |
| Compatibility precedence | some consumers prefer envelope payloads for display, but the general rule that domain truth beats legacy fields is not yet consolidated | Transport And Protocol |

Subtask posture:

- Do not open the full child series yet.
- First perform a document-reconciliation slice that marks backend lifecycle
  proof-slice content as landed or historical and updates the decision ledger.
- Open child tasks only when the reconciliation pass can name evidence and exit
  criteria for each child.

Document reconciliation completed in this slice:

- `docs/architecture-masterplan.md` now treats the backend lifecycle proof slice
  as landed rather than pending.
- The masterplan decision ledger now marks backend lifecycle ownership and the
  current lifecycle command/result contract as accepted by implementation.
- The ledger now distinguishes accepted invariants from unresolved backend
  identity, stale-config, and provider-failure handoff follow-ups.
- Opened focused child stubs for Effective Policy And Authority resolver shape
  and backend lifecycle identity/stale-config contract.

## Models

Working coordination model:

```text
architecture follow-through coordination
  -> doc reconciliation and decision-status updates
  -> focused domain-discovery subtasks
  -> implementation slices that name their owning domain
  -> accepted guidance promoted to runtime-direction or runtime-ownership
```

The umbrella owns progress tracking. The documents own durable architecture
truth. Subtasks own the work.

## Risks

- Treating architecture vocabulary as a substitute for implementation evidence.
- Reopening broad catch-all decomposition behavior under a nicer name.
- Allowing `runtime/` to become a new god package while the docs say otherwise.
- Letting compatibility adapters preserve old ownership through cached state,
  response-shape truth, or duplicated policy decisions.
- Letting stale masterplan text mislead future agents about already-landed
  backend lifecycle work.

## Transformations

Initial coordination targets:

- separate landed backend-lifecycle facts from still-open architecture gaps
- promote accepted guidance into the correct architecture doc
- split unresolved work into focused subtasks only when the next action is
  concrete enough to verify
- keep roadmap and workboard active-state language synchronized with this task

Completed initial transformation:

- Converted masterplan backend-lifecycle proof-slice sections from "pending proof"
  to "landed evidence plus remaining gaps".
- Promoted or annotated the relevant decision-ledger rows:
  backend lifecycle ownership, common command/result contract, model-serving
  scope, port discipline, health observation, and non-restart config invariant.
- Left stale config fingerprinting, provider-failure handoff, and backend
  registry/keying as explicit follow-up candidates rather than pretending the
  landed slice solved them.

## Evidence

Evidence this umbrella is working:

- each architecture-driven code slice names its owning domain before editing
- subtasks link back here and to the relevant architecture document section
- roadmap/workboard state does not imply closed umbrellas are active
- masterplan critique notes are no longer required as warm context for choosing
  the next task
- accepted decisions are reflected in `runtime-direction.md` or
  `runtime-ownership.md`, not hidden only in the masterplan

## Decisions

- Use this task as the active coordination object for top-down architecture
  follow-through.
- Do not reopen `260614-toas-architecture-masterplan-draft` as the planning
  task.
- Do not treat this task as permission for broad unbounded refactoring; focused
  subtasks should still carry concrete scope and evidence obligations.

## Open Fronts

- Architecture document reconciliation after backend lifecycle landed.
- Effective Policy And Authority resolver shape and ownership.
- Activity Lifecycle vs Session Host Supervision restart/reconnect/failure
  boundaries.
- Transcript Reconciliation to Operator Semantics handoff shape.
- Transport/Protocol compatibility precedence and domain-truth rules.
- Runtime package growth pressure and package/module placement guidance.

## Candidate Child Tasks

This list records which children have been split and which remain candidates.

| Child or candidate | Status | Possible exit evidence |
| --- | --- | --- |
| `260614-effective-policy-authority-resolver` | closed | PolicyResolver consolidated boundary in runtime/policy.py |
| `260614-backend-lifecycle-identity-stale-config` | opened as follow-on stub | domain tests for workspace/config identity and stale/restart-required status |
| `260614-model-backend-failure-handoff` | opened inception-only | explicit query/escalation contract and tests proving provider failure does not mutate lifecycle state by accident |
| `260614-activity-live-durable-boundary` | opened inception-only | table of live-only, durable, replayable, and crash-recovery activity state with test obligations |
| `260614-transcript-reconciliation-handoff` | opened inception-only | named handoff shape and branch-or-refuse invariants |
| `260614-compatibility-domain-truth-precedence` | opened inception-only | protocol-specific rule for domain result, envelope payload, and legacy fallback precedence |
| `260614-retire-local-suffix-naming-inversion` | existing naming cleanup; thread in when contours are clearer | primary/default path naming no longer carries stale daemon-era `_local` suffix |

## Next Actions

1. Proceed to `260614-backend-lifecycle-identity-stale-config` to build process keying and stale configuration checks on top of the consolidated PolicyResolver.
2. Keep inception-only child tasks light until a slice can name its first real investigation or implementation exit evidence.
3. Thread `260614-retire-local-suffix-naming-inversion` into this tree only when renaming can reveal ownership boundaries instead of just cleaning words.

