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

## Evidence

Ready to leave inception when:

- a code slice needs to cross the reconciliation/operator boundary
- the handoff fields and refusal semantics can be named precisely
