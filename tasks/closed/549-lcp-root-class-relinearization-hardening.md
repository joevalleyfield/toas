# 549: LCP Root-Parenting Pathology Repro and Hardening
keywords: projection, hardening, historical, correctness, transcript, frontier, lineage, root


## Why

LCP/adoption parent selection can admit root-equivalent message changes as non-root children.
Once this occurs, subsequent adoption passes can propagate the mistake into deep linear replay chains.

This pass focuses on reproducing that pathology in minimal fixtures, then hardening parent-selection so root-equivalent changes branch/root correctly and do not cascade.

## Problem Statement

- Root-equivalent message changes can be persisted as children of active frontier nodes.
- Subsequent messages may propagate from that incorrect parentage, expanding linear replay depth.
- Projection/rebuild then faithfully amplify the malformed lineage shape.

## Goals

1. Reproduce root-equivalent parenting failures with minimal deterministic fixtures.
2. Prevent root-equivalent messages from being attached as non-root children.
2. Preserve append-only durability while enforcing parent-selection invariants.
3. Add deterministic diagnostics so regressions are obvious in CI.

## Non-Goals

- Rewriting historical durable records in place.
- Semantic stripping of message content.
- Broad graph schema changes beyond parent-selection and diagnostics hardening.

## Invariants To Enforce

1. If a message is classified as root-equivalent under LCP/adoption rules, its durable parent must be `null` (or canonical root-equivalent), never an unrelated active frontier node.
2. Prefix-stable replay must branch by parentage rather than accumulate a linear chain from a root-parenting mistake.
3. Parent-selection logic must remain deterministic under equivalent transcript inputs.

## Planned Work

1. Add minimal repro fixtures for:
   - root-equivalent change persisted as non-root
   - short propagation sequence that worsens lineage depth
2. Add a root-equivalence detector seam in LCP/adoption parent-selection path (whitespace-robust, non-semantic).
3. Route root-equivalent matches to root/canonical-root parent policy.
4. Add regression fixtures asserting bounded branch depth growth under propagation attempts.
4. Add graph-health diagnostics for:
   - root-equivalent non-root anomalies
   - repeated propagation signatures after a root-parenting miss
   - path-depth deltas to selected head
5. Fan out exploration notes for additional LCP pathology classes discovered while implementing the fix.

## Acceptance Criteria

1. Minimal repro fixture confirms prior failure mode and then passes with hardening.
2. Tests prove root-equivalent messages are not persisted with non-null parent.
3. Selected-head transcript/rebuild projection remains bounded for the same repro corpus.
4. New diagnostics surface anomaly counts and fail loudly under regression fixtures.

## Closeout Rationale (2026-06-08)

This task was closed historically. The LCP root-parenting pathology where root-equivalent messages got attached as non-root children under active frontier nodes was solved by a cluster of related changes:

1. **Task 539 (Append-Time Parent Selection)**: Fixed the parent-selection logic so that transcript edits create graph branches from the LCP divergence boundary parent (`bound_lineage[i-1].id`) instead of falling back to the selected-tip/frontier node.
2. **Task 550 (Root Sentinel Taxonomy Unification `n0`)**: Introduced the dedicated virtual/materialized root sentinel node `n0` as a uniform parent target. This removed the special `parent: null` exception path in transcript reconciliation, ensuring that root-edit branch creation deterministically routes to `n0` under unified rules instead of tip-inheritance.
3. **Task 679 (New Log Root Sentinel Storage Contract)**: Ensured new logs start at `n1` parenting to `n0` (virtual root sentinel), solidifying the sentinel contract at the storage boundary.
4. **Task 567 (Frontier Recognition Off-By-One)**: Confirmed that anchor fallback is intentionally locked to `0` when durable anchor match is absent to prevent reopening regressions from the `549/550` boundary class.

Targeted test tripwires (e.g., `test_build_new_transcript_nodes_root_divergence_never_inherits_selected_tip_parent` in [tests/test_runtime_step_runtime.py](file:///Users/tim/Documents/Projects/toas-gemini/tests/test_runtime_step_runtime.py)) assert that root-divergence parentage resolves to `"n0"` rather than inheriting any active tip/frontier `bind_parent`, ensuring that the pathology cannot reappear.

## Validation

```bash
.gemini-local/bin/uvt run pytest -n 17
```

Plus targeted graph-parentage tests for root-class duplicate sequences.

