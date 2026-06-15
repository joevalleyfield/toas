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

## Next Actions

1. Reconcile `docs/architecture-masterplan.md` with the current backend
   lifecycle implementation reality.
2. Update the decision ledger statuses and split concrete follow-ups where
   unresolved items need task ownership.
3. Decide the first focused architecture-driven subtask from the highest
   leverage open front.
