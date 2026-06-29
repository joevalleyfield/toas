Filed as: 260630-source-qualified-logical-index-lookup
FKA:
AKA: scoped logical index lookup; ambiguous local id lookup; journal-local index identity
Legacy index:

keywords: graph, storage, hardening, follow-on, correctness, contract, indexes

Parent: `260629-storage-scale-model-proof-contract`
Related: `260627-split-storage-rebuild-and-projection-parity`; `260627-segmented-event-index-and-lookup-hardening`

# Source-Qualified Logical Index Lookup

## Current Reality

`find_logical_index_by_id()` searches the stitched logical index and returns the
first record whose `message_id` matches the requested string.

That was reasonable while message ids were treated as effectively global across
the stitched read surface. The current history contract says the opposite:
message ids such as `n1` are journal-local labels.

## Desired Reality

Logical index lookup must not quietly reintroduce global-id semantics.

Bare-id lookup should be safe only when the declared lookup scope makes the id
unambiguous. When multiple source journals contain the same local id, full-scope
lookup should refuse or return an explicit ambiguity/candidate result instead
of selecting the first physical occurrence.

## Scope

- define the minimal source-qualified or ambiguity-aware lookup contract
- add a focused test using the `ambiguous_duplicate_local_ids` scale model
- update `graph_index_edges.py` and public facade wiring in `graph.py` as needed
- preserve existing position-based logical index behavior
- keep this to index identity semantics; do not implement graph stitching or
  LCP alignment here

## Non-Goals

- source-qualified graph rendering
- transcript or LLM-input stitching
- retention/tombstone behavior
- content-addressed object storage
- full scale-model fixture harness

## Exit Evidence

- a test proves duplicate local ids across cold/hot sources are represented as
  distinct index candidates
- bare full-scope lookup no longer silently returns the first duplicate local id
- existing logical-position and single-source lookup tests still pass
- any public error/result wording distinguishes ambiguous local ids from source
  corruption

