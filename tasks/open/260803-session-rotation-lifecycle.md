Filed as: 260803-session-rotation-lifecycle
FKA:
AKA: bounded transcript working set; session lifecycle; transcript hygiene rotation
Legacy index:

keywords: runtime, decomp, inception, usability, session, transcript, rotation, lifecycle

Related: `260630-soft-rotation-scale-fixture`; `260803-llm-native-compaction-projection`; `260626-transcript-parallelism-design-pressures`

# Session Rotation For Bounded Transcript Working Sets

## Objective

Make session rotation a first-class transcript-hygiene operation: keep the
active working transcript small, continue from durable event history, and
preserve one logical line of work without implying parallelism.

## Critical Distinction

This is not the existing hot/cold `events.jsonl` segment-rotation problem.
Storage rotation bounds the active event-log file while preserving a logical
history. Session rotation bounds the user-visible and model-facing working
transcript while continuing from that history.

It is also not transcript parallelism. Rotation creates a successor working
set for the same line of work; it does not create sibling operators, concurrent
sessions, merge authority, or a new branch unless the user separately changes
lineage.

## Desired Contract

- A session has a bounded active transcript working set backed by append-only
  durable history.
- Rotation occurs only at a safe turn boundary and never splits an in-flight
  tool plan, generation, cancellation, or unresolved execution outcome.
- The successor starts with enough projected context to continue coherently,
  using explicit lineage/session metadata rather than copying all prior turns.
- The retired transcript remains recoverable from durable history and ordinary
  transcript/history projections.
- Manual and size-pressure rotation use the same lifecycle transition, with
  policy deciding when automatic rotation is suggested or performed.
- Rotation is observable to the operator but does not masquerade as a new
  conversational participant or parallel task.

## Requirements Parent Questions

- What exactly is a session identity now that `session.md` compatibility is no
  longer the runtime authority?
- Is the bounded working set a file, a selected projection, a head-relative
  range, or an explicit durable session-boundary record?
- What context seeds the successor: LLM compaction, deterministic outline,
  selected recent turns, explicit carry-forward fields, or a composition?
- Which unresolved facts prohibit rotation, and how are they diagnosed?
- Should threshold pressure suggest rotation, schedule it automatically at the
  next safe boundary, or follow configurable policy?
- How do `/compact` and rotation compose without making compaction a hidden
  lifecycle side effect?
- What operator command name avoids confusion with storage-segment rotation?

## Acceptance Criteria

- [ ] The session object/boundary and successor relationship are documented
  independently of storage segments, heads, and parallel operators.
- [ ] Manual rotation creates a bounded successor working transcript at a safe
  boundary while preserving the same logical lineage.
- [ ] Configurable transcript-size pressure can suggest or schedule the same
  transition without interrupting an active turn.
- [ ] Successor context preserves active objective, constraints, open work,
  recent execution state, and recovery references in representative fixtures.
- [ ] Full prior transcript content remains recoverable from durable history
  without treating the retired working transcript as canonical storage.
- [ ] Rotation does not create a sibling head, parallel session, merge record,
  or additional operator identity by default.
- [ ] Compaction is an explicit input/projection choice in the transition, not
  an invisible mutation of history.
- [ ] Repeated rotations keep model input and operator working surfaces bounded
  in a scale fixture.
- [ ] Failure to produce valid successor context leaves the current session
  active and unchanged.

## Non-Goals

- Implementing multi-operator or parallel transcript orchestration.
- Choosing archive deletion or retention policy.
- Replacing event-log segmentation or graph lineage.
- Rotating during an in-flight operation to satisfy a hard byte ceiling.

## Likely Ownership

Session lifecycle and successor selection belong in runtime/operator semantics;
durable boundary facts, if required, belong in graph storage. Transcript and
LLM-input surfaces remain projections over the selected lineage/session range.

## Allowed Write Surfaces

- session lifecycle and projection selection under `src/toas/runtime/`
- `src/toas/graph.py` for a justified append-only session-boundary record
- operator command and help surfaces
- projection/model-input code only as required to honor the selected working
  range
- focused tests under `tests/` and history scale-model fixtures
- lifecycle/projection documentation and this task file
- mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- settled session/boundary object model;
- safe-boundary state matrix;
- multi-rotation scale fixture showing bounded active input and complete
  durable recovery;
- transcript/history/llm-input examples before and after rotation;
- failure-path proof and default suite result.

## Operator Input Welcome

Useful additions include preferred rotation commands, target transcript bounds,
examples of ideal successor context, existing lifecycle sketches, and cases
that should postpone rotation despite size pressure.
