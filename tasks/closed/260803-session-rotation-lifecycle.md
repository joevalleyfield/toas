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

These questions are settled by the continuation and rollover follow-ons:

- A working session is the explicitly selected transcript path. It does not
  require a new operator/session identity; the append-only
  `session_successor` record relates predecessor and successor paths and
  anchors the successor after the continuation parent message.
- The bounded working set is the successor transcript file plus its explicit
  durable relationship. Message history remains the canonical recoverable
  record; storage segments are a separate physical concern.
- Successor context is the configured seed prompt, the exact assistant-role
  compaction handoff, and the ordered literal user restoration commands.
- Active runs and unresolved execution queues prohibit continuation; missing,
  invalid, or non-`/compact` predecessor context also refuses without
  mutation, with precise runtime errors.
- `/compact` creates projection evidence only. Continuation consumes the
  transcript-local handoff and appends only the successor relationship before
  the first ordinary successor step synchronizes its messages.
- `continue`/`successor` is canonical. `rotate` names remain tested,
  documented compatibility aliases while physical journal rollover retains
  the term rotation.

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

- [x] The session object/boundary and successor relationship are documented
  independently of storage segments, heads, and parallel operators.
- [x] Manual continuation creates a bounded successor working transcript at a safe
  boundary while preserving the same logical lineage.
- [x] Successor context preserves active objective, constraints, open work,
  recent execution state, and recovery references in representative fixtures.
- [x] Full prior transcript content remains recoverable from durable history
  without treating the retired working transcript as canonical storage.
- [x] Continuation does not create a sibling head, parallel session, merge record,
  or additional operator identity by default.
- [x] Compaction is an explicit input/projection choice in the transition, not
  an invisible mutation of history.
- [x] No transcript-size policy, timer, or background lifecycle automatically
  invokes the transition.
- [x] Repeated continuations keep model input and operator working surfaces bounded
  in a scale fixture.
- [x] Failure to produce valid successor context leaves the current session
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
- repeated explicit-continuation fixture showing bounded active input and complete
  durable recovery;
- transcript/history/llm-input examples before and after continuation and
  physical journal rollover;
- failure-path proof and default suite result.

## Completion Evidence

Completed 2026-08-23 after reconciling the parent contract with its closed
implementation follow-ons.

- **Object and boundary model:** the active working surface is an explicit
  workspace-relative transcript path. Continuation writes one append-only
  `session_successor` relationship containing predecessor path, successor path,
  seed prompt reference, and continuation-parent message ID. The first ordinary
  successor step binds after that parent and synchronizes the seed, handoff,
  and restoration messages. No session identity, sibling head, merge record,
  surface rebind, or config override is created by continuation.
- **Context and recovery:** the successor is composed from the resolved seed,
  exact assistant-role handoff, and ordered literal user `$ ...` restoration
  commands. The predecessor and complete message lineage remain recoverable
  through ordinary history/transcript/LLM-input projections; physical
  `.toas/events.jsonl` rollover is covered independently by
  `260804-automatic-hot-journal-rollover`.
- **Safe-boundary matrix:** active or cancelling runs, pending/running/blocked/
  awaiting-approval queues, missing or out-of-workspace predecessors, and
  missing or malformed transcript-local `/compact` handoffs refuse without
  mutation. Empty names cancel; collisions receive a numeric suffix; successor
  file or relationship-write failures clean up the new surface and preserve
  the predecessor.
- **Compaction separation:** `/compact` records the semantic handoff and its
  projection evidence. Continuation requires the predecessor transcript to end
  in `/compact` followed by the handoff, but does not require or rewrite the
  selected compaction record and does not eagerly append the successor's
  messages.
- **Bounded repeated continuation:**
  `tests/test_runtime_session_rotation.py::test_repeated_continuations_remain_on_one_lineage`
  proves repeated successor creation remains on one graph head, while the
  first-successor-step fixture proves the bounded successor is populated only
  when stepped. Storage rollover tests separately prove repeated hot-journal
  sealing and complete ordered recovery.
- **Projection and storage evidence:**
  `tests/test_history_scale_models.py::test_transcript_rehydrated_hot_prefix_after_rotation_projects_hot_surfaces`
  covers transcript/history/LLM-input behavior after physical rollover;
  `tests/test_graph_rotation_edges.py` covers post-turn thresholding, crash
  recovery, index rebuild, ordinal collision, concurrency, and guard release.
- **Verification:** focused continuation, daemon/host, graph rollover, and
  history-scale coverage passes (90 tests in the current focused run). The
  repository's latest full-suite evidence remains 2,857 passed with 20
  sandbox-only integration failures and 9 deselected; the failures are Unix/TCP
  socket permission and Vim viminfo-write restrictions, not continuation or
  rollover behavior.

The former rotate names were retired in the follow-on cleanup task
`260823-retire-session-rotate-compatibility`. The canonical callable surfaces
are now `session_continue`, `run_session_continue`, and `:ToasContinue`; the
established `<leader>r` shortcut remains and invokes `:ToasContinue`.

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
