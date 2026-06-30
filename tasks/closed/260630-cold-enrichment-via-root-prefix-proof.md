Filed as: 260630-cold-enrichment-via-root-prefix-proof
FKA:
AKA: cold-side enrichment lookup; stitch proof related records; non-message recovery proof
Legacy index:

keywords: graph, storage, hardening, follow-on, correctness, contract, testing

Parent: `260629-storage-scale-model-proof-contract`
Related: `260630-root-prefix-stitch-proof-fixture`; `260630-history-scale-model-functional-tests`

# Cold Enrichment Via Root-Prefix Proof

## Current Reality

Root-prefix proof can align transcript-rehydrated hot message occurrences with
cold message occurrences, but it does not yet demonstrate the main payoff:
recovering cold-side non-message facts that did not rehydrate from the
transcript.

## Desired Reality

Given a proof pair such as `cold c2 -> hot h2`, TOAS can find cold non-message
records attached to `c2` using relationship fields that already exist in the
event log:

- `tool_request.related_to`
- `tool_result.related_to`
- `llm_call.payload.message_id`

The helper should return enrichment candidates only for matched proof pairs.

## Scope

- add a small helper for cold related-record lookup through a root-prefix proof
- use existing non-message relationship shapes only
- prove matched hot occurrences can recover cold-side enrichment candidates
- prove hot-only/unmatched occurrences do not guess enrichment
- keep public graph/history/transcript rendering unchanged

## Non-Goals

- render or merge the enrichment into transcript/history/graph surfaces
- invent new relationship fields
- recover unrelated command request/result chains
- implement general stitch traversal
- modify retention policy

## Exit Evidence

- scale-model tests use existing `related_to` and `payload.message_id` shapes
- matched hot occurrence returns cold tool/model enrichment candidates
- unmatched hot occurrence returns no candidates
- related history/graph tests still pass

## Outcome

Closed by adding a narrow root-prefix enrichment helper over existing cold
event relationship fields. The proof now demonstrates that a matched hot
message occurrence can recover cold-side `tool_request`, `tool_result`, and
`llm_call` records linked to the corresponding cold message, while unmatched
hot occurrences and failed proofs return no enrichment candidates.
