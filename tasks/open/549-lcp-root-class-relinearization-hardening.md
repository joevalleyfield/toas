# 549: LCP Root-Parenting Pathology Repro and Hardening
keywords: projection, hardening, active, correctness, transcript, frontier, lineage, root

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

## Validation

```bash
uv run pytest
```

Plus targeted graph-parentage tests for root-class duplicate sequences.
