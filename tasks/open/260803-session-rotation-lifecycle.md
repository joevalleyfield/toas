Filed as: 260803-session-rotation-lifecycle
FKA:
AKA: bounded transcript working set; session lifecycle; transcript successor continuation
Legacy index:

keywords: runtime, decomp, inception, usability, session, transcript, rotation, lifecycle

Related: `260804-automatic-hot-journal-rollover`; `260804-successor-continuation-remediation`; `260803-llm-native-compaction-projection`; `260626-transcript-parallelism-design-pressures`

# Successor Continuation For Bounded Transcript Working Sets

## Objective

Define the explicit lifecycle transition that lets an operator carry a selected
compaction handoff into a successor working transcript for the same logical
line of work. This is an enabler for the user-facing compact/continue action, not
an automatic transcript-management policy.

## Critical Distinction

This is not the hot/cold `events.jsonl` segment-rollover problem. Storage
rollover should eventually happen automatically to bound the hot journal; that
work is tracked separately by `260804-automatic-hot-journal-rollover`.

User-visible transcripts must not rotate automatically. The operator can call
for semantic compaction when the transcript needs it, then explicitly request
the successor transition. This task supplies the lifecycle semantics needed by
that action and nothing more.

It is also not transcript parallelism. Continuation creates a successor working
set for the same line of work; it does not create sibling operators, concurrent
sessions, merge authority, or a new branch unless the user separately changes
lineage.

Reserve **rotation** for physical event-journal rollover. The explicit
user-visible operation in this task is **continuation** or **successor
creation**. `/compact`, successor creation, and journal rollover are three
separate operations that may compose but must not share hidden side effects.

## Desired Contract

- An explicit operator continuation creates a successor working transcript backed
  by the same append-only durable history.
- The transition occurs only at a safe turn boundary and never splits an in-flight
  tool plan, generation, cancellation, or unresolved execution outcome.
- The successor starts with enough projected context to continue coherently,
  using explicit lineage/session metadata rather than copying all prior turns.
- The retired transcript remains recoverable from durable history and ordinary
  transcript/history projections.
- No size threshold, timer, or background policy automatically rotates the
  user-visible transcript.
- Continuation is observable to the operator but does not masquerade as a new
  conversational participant or parallel task.

## Requirements Parent Questions

- What exactly is a session identity now that `session.md` compatibility is no
  longer the runtime authority?
- Is the bounded working set a file, a selected projection, a head-relative
  range, or an explicit durable session-boundary record?
- What context seeds the successor: LLM compaction, deterministic outline,
  selected recent turns, explicit carry-forward fields, or a composition?
- Which unresolved facts prohibit continuation, and how are they diagnosed?
- How do `/compact` and continuation compose without making compaction a hidden
  lifecycle side effect?
- Which `continue`/`successor` command names best express the operation, and
  what compatibility life should the original rotate names receive?

## Acceptance Criteria

- [ ] The session object/boundary and successor relationship are documented
  independently of storage segments, heads, and parallel operators.
- [ ] Manual continuation creates a bounded successor working transcript at a safe
  boundary while preserving the same logical lineage.
- [ ] Successor context preserves active objective, constraints, open work,
  recent execution state, and recovery references in representative fixtures.
- [ ] Full prior transcript content remains recoverable from durable history
  without treating the retired working transcript as canonical storage.
- [ ] Continuation does not create a sibling head, parallel session, merge record,
  or additional operator identity by default.
- [ ] Compaction is an explicit input/projection choice in the transition, not
  an invisible mutation of history.
- [ ] No transcript-size policy, timer, or background lifecycle automatically
  invokes the transition.
- [ ] Repeated continuations keep model input and operator working surfaces bounded
  in a scale fixture.
- [ ] Failure to produce valid successor context leaves the current session
  active and unchanged.

## Non-Goals

- Implementing multi-operator or parallel transcript orchestration.
- Choosing archive deletion or retention policy.
- Replacing event-log segmentation or graph lineage.
- Rotating during an in-flight operation to satisfy a hard byte ceiling.
- Automatically suggesting or continuing user-visible transcripts based on size.

## Likely Ownership

Explicit session successor selection belongs in runtime/operator semantics;
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
- repeated explicit-rotation fixture showing bounded active input and complete
  durable recovery;
- transcript/history/llm-input examples before and after rotation;
- failure-path proof and default suite result.

## Gap-Closing Follow-Ons

- `260804-vim-session-rotate-handoff` historically landed the first manual
  post-`/compact` rotate-step-step path: runtime successor composition and lifecycle evidence,
  deterministic editable naming, ordinary restoration-plan staging, and the
  thin Vim action that opens the successor. Completed 2026-08-04 with the
  explicit successor boundary, one-lineage rebinding, failure matrix, and
  repeated-rotation fixture. Its composite journal rewrite, message roles,
  restoration-plan translation, and rotation naming are superseded by the
  clarified contract below.
- `260804-successor-continuation-remediation` owns the gap-closing
  implementation: append-only fact separation, assistant-role handoff
  projection, structured successor composition, literal user `$` restoration
  commands, cross-platform behavior, and continuation-oriented naming.
  Completed 2026-08-04 with transcript-local `/compact` discovery, one
  append-only `session_successor` relationship, explicit-path step binding, and
  no continuation-owned config or surface selection.

## Operator Input Welcome

Useful additions include preferred continuation commands, target transcript bounds,
examples of ideal successor context, existing lifecycle sketches, and cases
that should refuse or postpone an explicitly requested successor transition.
