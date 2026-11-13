Filed as: 261112-in-turn-policy-overlays
FKA:
AKA: in-turn policy overlays
Legacy index:

keywords: active, feature, projection, policy, transcript, continuation

Depends on: `260831-transcript-source-reference-operations` (ordered execution and recovery slice)
Related: `260831-transcript-source-reference-operations`; `261029-serialize-grants-on-session-rotation`

# In-turn policy overlays

## Intent

Keep continuation policy overlays and their results visible to the operator within a single user turn, while projecting effective policy to the model.

## Requirements

- Generate a single user turn containing the continuation handoff, policy
  overlay, and restoration plan. Apply the overlay before the plan.
- Preserve the overlay and its outcome in durable history and in the operator
  transcript, including after rebuild. Use an in-turn structure whose source
  and results are omitted from model projection. Keep the surrounding user
  content in the same model message.
- Give the model the effective policy for the selected lineage. Surface real
  capability changes without exposing the overlay command or its result.
  An equivalent grant produces no capability delta.
- Keep the existing `TOAS:CONTROL` turn boundary and its input/output elision.
  An operator can move overlay actions into a control turn by editing.
- Apply ordinary first-failure recovery to the overlay and restoration plan.
  Leave one-turn grant lifetime and compact pending forms to follow-on work.

## Acceptance

Generate and step a real continuation. Inspect the operator transcript after
rebuild and compare it with `toas llm-input --envelope` and the actual model
request. Cover a changed grant, an equivalent grant, and a failed overlay
that leaves the restoration plan staged. The changed grant must affect the
plan when it runs. The equivalent grant must produce no capability delta.
