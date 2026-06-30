Filed as: 260630-stitch-plan-contract
FKA:
AKA: alignment plan; cold-hot stitch evidence; stitch refusal contract
Legacy index:

keywords: graph, storage, projection, investigation, follow-on, correctness, contract

Parent: `260629-storage-scale-model-proof-contract`
Blocks: `260627-split-storage-rebuild-and-projection-parity`
Related: `260630-root-prefix-stitch-proof-fixture`; `260630-cold-enrichment-via-root-prefix-proof`; `260627-history-surface-user-intent-alignment`

# Stitch Plan Contract

## Current Reality

TOAS now has a root-prefix proof helper and a cold-enrichment lookup helper.
Those helpers prove useful facts, but they are still too raw for history,
graph, transcript, or LLM-input surfaces to consume directly.

A cold-inclusive surface should not have to rediscover:

- which cold and hot scopes were considered
- which message occurrences were aligned
- which cold-side non-message facts are recoverable
- why a stitch was refused
- whether the result is complete enough for the requested surface

## Desired Reality

TOAS has a small semantic stitch-plan contract between low-level proof helpers
and future user/runtime surfaces.

The plan should be evidence-bearing, bounded, and explicit about refusal. It
should make it possible to say:

```text
this hot lineage can be aligned with this cold lineage by root-prefix proof
these physical message occurrences correspond
these cold-side records may enrich the matched hot occurrences
this surface may proceed, warn, or refuse for this declared reason
```

## Scope

- define the shape of a stitch/alignment plan over declared cold and hot scopes
- include matched occurrence pairs from the existing root-prefix proof
- include recoverable cold-side enrichment candidates for matched pairs
- include explicit refusal reasons for absent, mismatched, ambiguous, or
  incomplete alignment evidence
- keep source-qualified local-id semantics intact
- add scale-model tests around the plan contract

## Non-Goals

- render stitched `history`, `graph`, `transcript`, or `llm-input` output
- invent new event relationship fields
- implement archive traversal beyond declared cold/hot scopes
- change active `step` reconciliation authority
- define retention policy for summaries, tombstones, or redactions

## Acceptance Shape

- a matched cold/hot continuation produces a stitch plan with proof pairs and
  cold enrichment candidates
- an unmatched or partially mismatched continuation produces a refusal reason
  instead of a partial stitched view
- same local ids across sources remain expected and are resolved only through
  plan evidence, not bare id equality
- hot-only or single-source views can proceed without needing a stitch plan
- related scale-model tests remain green
