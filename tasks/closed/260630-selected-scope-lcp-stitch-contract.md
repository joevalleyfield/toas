Filed as: 260630-stitch-plan-contract
FKA: 260630-stitch-plan-contract
AKA: alignment plan; selected-scope LCP; stitch evidence; stitch refusal contract; common prefix stitching
Legacy index:

keywords: graph, storage, projection, investigation, follow-on, correctness, contract

Parent: `260629-storage-scale-model-proof-contract`
Blocks: `260627-split-storage-rebuild-and-projection-parity`
Related: `260630-root-prefix-stitch-proof-fixture`; `260630-cold-enrichment-via-root-prefix-proof`; `260627-history-surface-user-intent-alignment`

# Selected-Scope LCP Stitch Contract

## Current Reality

TOAS now has a root-prefix proof helper and a cold-enrichment lookup helper.
Those helpers prove useful facts, but they are still too raw for history,
graph, transcript, or LLM-input surfaces to consume directly.

A selected multi-log surface should not have to rediscover:

- which histories were selected by CLI/config scope
- which root occurrences are equivalent
- which message occurrences remain equivalent while walking forward from root
- which source-side non-message facts are recoverable
- which canonical qualified identity represents each matched node
- which pseudonyms point to the same stitched node

## Desired Reality

TOAS has a small selected-scope LCP stitch contract between low-level proof
helpers and future user/runtime surfaces.

The contract should be evidence-bearing, bounded, and light. It should make it
possible to say:

```text
these selected histories share these equivalent roots
these physical message occurrences remain equivalent through this common prefix
this oldest qualified identity is canonical for the stitched node
these other qualified identities are pseudonyms for the same node
these non-message records may enrich the stitched node
```

## Scope

- define the shape of an LCP stitch result over selected event-log histories
- keep default selection local/base-config, with broader scope coming from CLI
  flags until a real selection DSL exists
- start from equivalent roots, then walk forward while message role/content and
  topology remain equivalent
- treat divergence as the normal end of the common prefix, not as corruption
  or surface refusal
- select the oldest qualified occurrence as the canonical identity for a
  stitched node
- preserve all matched qualified identities as pseudonyms for the same node
- include recoverable non-message enrichment candidates for matched pseudonyms
- keep source-qualified local-id semantics intact
- add scale-model tests around the selected-scope LCP contract

## Non-Goals

- render stitched `history`, `graph`, `transcript`, or `llm-input` output
- invent new event relationship fields
- implement archive traversal beyond declared selected scopes
- change active `step` reconciliation authority
- define retention policy for summaries, tombstones, or redactions
- explain absences beyond silence by default
- build a selection DSL

## Acceptance Shape

- default local scope produces no multi-log stitch requirement
- selected multi-log scope finds equivalent roots before walking forward
- selected multi-log scope produces common-prefix stitched nodes across N
  histories, not just a cold/hot pair
- divergence ends the stitched prefix without treating the selected histories
  as corrupt
- same local ids across sources remain expected and are resolved only through
  LCP evidence, not bare id equality
- canonical identity is the oldest qualified occurrence, with all equivalent
  qualified identities retained as pseudonyms
- enrichment from matched pseudonyms attaches to the stitched common identity
- related scale-model tests remain green

## Outcome

Closed by adding a selected-scope LCP stitch helper and scale-model tests. The
contract now represents single-source local scope as not requiring a stitch,
walks equivalent roots forward across N selected histories, stops cleanly at
divergence or selected-history exhaustion, chooses the oldest qualified
identity as canonical, preserves all matched qualified identities as
pseudonyms, and attaches source-side enrichment from matched pseudonyms to the
stitched common node.

Surface rendering, CLI selection flags, and richer absence/refusal language
remain outside this slice.
