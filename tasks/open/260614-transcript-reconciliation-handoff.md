Filed as: 260614-transcript-reconciliation-handoff
FKA:
AKA: reconciliation handoff object; transcript to operator semantics boundary; branch-or-refuse handoff
Legacy index:

keywords: runtime, investigation, inception, architecture, transcript, frontier, reconciliation, semantics

# Transcript Reconciliation Handoff Object

## Current Reality

The architecture splits Transcript Reconciliation from Operator Semantics.
Reconciliation should decide how edited transcript text relates to durable
history; Operator Semantics should decide what consequence happens next.

The split is named, but the handoff object is not.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

There should be an explicit handoff shape from reconciliation to consequence
selection, likely including:

- reconciled working nodes
- selected frontier
- parentage/branch decision
- diagnostics or refusal reason
- enough provenance to keep rendered text from becoming canonical state

## Inception Note

This task is intentionally inception-only. It should become active when
frontier, branch ambiguity, transcript editing, or operator-semantics work needs
a stable boundary before implementation.

## Alignment Target

This task should make the current transcript-to-step boundary truthful. It
should not design new editing UX, merge tooling, or branch management features.

The first useful slice is an inventory of current reconciliation helpers,
frontier selection inputs, branch/refusal diagnostics, and the exact data shape
that Operator Semantics already consumes.

## Known Facts

- Edited prior aligned content means branch, not mutation.
- Branch ambiguity should be explicit: branch or refuse, never silently mutate.
- `toas step` semantics must not be decided by CLI, daemon, or host adapters.

## Unknowns

- Whether the handoff should be a dataclass, tuple of existing structures, or
  documented contract around current helper outputs.
- Which current helpers already imply the boundary.
- Which tests best prove reconciliation can be tested without model/tool
  consequence logic.
- Whether the handoff needs a new dataclass or only clearer names around
  existing values.

## Evidence

Ready to leave inception when:

- a code slice needs to cross the reconciliation/operator boundary
- the handoff fields and refusal semantics can be named precisely
- the proposed shape is grounded in current helpers rather than new UX ambition

## Inventory (completed)

### Current reconciliation helpers

- `_build_new_transcript_nodes` — parses transcript, computes LCP, extracts new nodes, annotates branch parent and provenance. Returns `(bind_index, lcp_index, annotated_nodes)` but also computes `divergence_parent` and `corrections`/`uncertain` internally without surfacing them.
- `_working_with_transcript_tail_frontier` — selects frontier by replacing last reconstructed node with transcript tail.
- `_stabilize_lcp_for_assistant_tail_replay` — prevents n-1 fallback when only terminal assistant replay text drifts.
- `_map_lcp_index_to_lineage_boundary_index` — maps message-space LCP index to lineage boundary index.

### Frontier selection inputs

- `working_for_frontier` = reconstructed_working[:-1] + [transcript_tail] (or reconstructed_working if no transcript nodes, or [transcript_tail] if no reconstructed working)
- `frontier` = working_for_frontier[-1]

### Branch/refusal diagnostics

- `divergence_parent` — computed but dropped; only used for `_annotate_branch_parent` on first new node. Never surfaced to operator semantics.
- `corrections` — map of new-from-transcript index → corrected LLM-generated node id. Used for provenance annotation, never surfaced.
- `uncertain` — set of new-from-transcript indices with uncertain provenance. Used only to skip `user_authored` annotation, never surfaced.
- Near-miss errors — checked separately in `run_step` via `_frontier_callable_near_miss_error`, not part of the handoff.

### Exact data shape operator semantics consumes

From `run_step`:
- `context.reconstructed_working` — bootstrap check (empty → seed)
- `context.frontier` — callable intent check, near-miss check
- `context.working_for_frontier` — frontier consequences execution
- `context.new_from_transcript` — output composition (`new_from_transcript + consequences`)

### Proposed handoff shape

`ReconciliationHandoff` dataclass in `src/toas/runtime/reconciliation_handoff.py`:

- `working_for_frontier: list[dict]` — reconciled working nodes
- `new_from_transcript: list[dict]` — new nodes to record
- `frontier: dict | None` — selected frontier
- `divergence_parent: str | None` — branch decision (None = linear continuation)
- `bind_index: int` — reconciliation metadata
- `lcp_index: int` — reconciliation metadata
- `diagnostics: ReconciliationDiagnostics | None` — corrections/uncertain/provenance decisions
- `refusal: RefusalReason | None` — refusal reason (future: branch ambiguity, etc.)

### Implementation status

- [x] Inventory complete
- [x] `ReconciliationHandoff` dataclass created in `src/toas/runtime/reconciliation_handoff.py`
- [x] `ReconciliationDiagnostics` surfaces corrections/uncertain from `_build_new_transcript_nodes`
- [x] `RefusalReason` shape defined (not yet used; placeholder for branch ambiguity)
- [x] `divergence_parent` surfaced as a field on the handoff
- [x] `RunStepFrontierContext` replaced by `ReconciliationHandoff`
- [x] `_build_run_step_frontier_context` returns `ReconciliationHandoff`
- [ ] Tests for reconciliation handoff isolation (testable without model/tool logic)
- [ ] Refusal semantics wired for branch ambiguity cases
- [ ] Task file updated in same commit as code changes
