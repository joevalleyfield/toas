Filed as: 260920-branch-projected-policy-program
FKA:
AKA: lcp policy reevaluation program; transcript policy overlay; branch-forward control state
Legacy index:

keywords: runtime, decomp, active, correctness, contract, transcript, policy, lineage, config, grants, environment

Parent: `260920-transcript-control-state-survey`
Related: `260920-lcp-policy-reevaluation-contract`; `260920-transcript-policy-reinterpretation-examples`; `260920-transcript-control-documentation-contract`; `260831-transcript-source-reference-operations`; `325-config-override-lifecycle-load-save-restore-and-unset`; `330-semi-durable-shell-grants-transcript-and-config-lanes`; `310-transcript-env-modifiers-as-execution-surface`

# Branch-Projected Transcript Policy Program

## Intent

Replace accidental history-wide control-state behavior with branch-forward
policy evaluation without losing the useful ability to reinterpret unchanged
assistant content after inserting a policy change. The program owns the
cross-domain model and decomposition; its follow-ons own implementation
slices.

## Confirmed direction

- The effective operation policy is the current domain-specific
  user/workspace baseline plus the transcript deltas visible before that
  operation on its selected branch.
- A transcript rewrite uses LCP policy reevaluation: reduce the shared prefix,
  materialize the new suffix, then reduce eligible new-suffix deltas in source
  order through the selected operation.
- Recreated declarative control `C1'` is operational in the new branch. An old
  branch's `C1` effect record is audit evidence, not active policy.
- A direct restep can create `A2`, exactly related to unchanged `A1`, and run
  it under an inserted preceding `P1`; this is not model regeneration.
- Pure typed declarations may be reduced. External resolutions may be
  reconstituted only from immutable identified results. Fresh imperative work
  remains explicit.
- This program does not introduce a separate policy graph, a universal
  precedence ladder, fuzzy message matching, or settings checkpoints as the
  primary state model.

## End-state model

```text
effective policy for operation O
  = resolve_current_base_policy(domain, user, workspace, hard constraints)
    + reduce(branch-visible transcript deltas before O)
```

The reducer is domain-specific: ordinary config values/timeouts replace or
restore values, grants reduce add/remove/reset state, and child environment
uses its ordered merge/replace semantics. Transcript deltas cannot lift hard
safety constraints.

Every newly written transcript-originated control result needs provenance that
identifies its source message. When a new source reconstitutes an earlier
external resolution, provenance names both the new source and immutable result
ID. Legacy unlinked control records are compatibility input only; they cannot
be retroactively treated as branch-scoped facts.

## Program phases

### Phase 1 — direct declarative branch projection

Implement the smallest vertical slice around config value deltas and
shell-scope grants.

- Give new durable control records source-message linkage.
- Build a branch/LCP-aware policy projection at the step boundary instead of
  reducing the entire journal.
- Make an inserted preceding control affect the direct restep of unchanged
  assistant content.
- Add exact `restep_of` provenance for the resulting assistant message.
- Turn the two strict policy-reinterpretation examples green: inserted-policy
  success and sibling isolation.

Expected implementation surfaces: `src/toas/runtime/step_runtime.py`,
`src/toas/runtime/session_step_edges.py`, `src/toas/graph_control_state_edges.py`,
`src/toas/graph_record_writers.py`, and focused runtime/integration tests.

Status: Complete for the initial config/grant slice (`260920-lcp-direct-policy-deltas`).
Direct declarations now project from the reconstructed branch, exact assistant
resteps carry provenance, and new config/grant records link their source
message. The compatibility boundary is deliberately narrow: linear
continuation may consume legacy durable grants; rewrites do not.

### Phase 2 — other reducible transcript policy domains

Bring child-process environment modifiers, target selection, command/workspace
context, and other eligible serializable controls onto the same projection
interface. Preserve each domain's own merge and scope behavior rather than
forcing all controls into config-override semantics.

### Phase 3 — reconstitutable external resolutions

Introduce immutable typed resolution-result records for operations such as
`/config load`. A result records source message ID, canonical resolved delta,
input identity/digest, and reconstitution eligibility. A rewritten matching or
explicitly referencing control can reuse that immutable result without reading
the external source; a fresh load produces a new result.

### Phase 4 — inspection and optional checkpoints

Expose effective-policy provenance and source layers to operators. Consider
settings checkpoints only as explicit projections, distinguishing transcript
overlay snapshots from fully resolved current-baseline snapshots.

## Boundaries and deferred choices

- Phase 1 must not broaden into all record kinds or file-load reconstitution.
- The first restep relation uses exact structural correspondence of assistant
  content; fuzzy semantic matching is deferred.
- Compatibility treatment for old unlinked records must be explicit and
  observable; it must not silently preserve history-wide leakage forever.
- The concrete syntax for explicit result references and fresh loads is
  deferred to Phase 3.
- `/run` remains a forward source-reference operation under current policy; it
  is not a substitute for transcript restep semantics.

## Completion evidence

This parent remains active until the follow-on slices have either landed or
been deliberately reprioritized. Each implementation follow-on must update
this task with its scope, evidence, and remaining compatibility gaps.
