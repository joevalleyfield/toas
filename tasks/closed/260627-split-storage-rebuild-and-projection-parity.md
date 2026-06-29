Filed as: 260627-split-storage-rebuild-and-projection-parity
FKA:
AKA: split storage parity; rebuild parity; projection parity across segments
Legacy index:

keywords: graph, hardening, inception, correctness, projection, transcript, storage

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocked by: `260627-graph-segmented-read-query-hardening`
Related: `260614-architecture-follow-through-coordination`

# Split Storage Rebuild And Projection Parity

## Current Reality

If storage splits but projection and rebuild surfaces drift, TOAS will have
preserved bytes while losing user-trust semantics. The visible proof surfaces
still need to read as one coherent history.

## Desired Reality

Physical storage segmentation should change storage layout only. It should not
change the observable meaning of:

- `toas rebuild`
- `toas transcript`
- `toas llm-input`
- `toas heads`
- `toas graph`

That parity goal needs an important nuance:

- parity does not require every ordinary operation to traverse arbitrarily deep
  cold history
- warm-history continuation should remain fast and explicit
- operations that truly need deeper cold history should either opt into that
  cost or fail/refuse clearly rather than silently falling onto a pathological
  slow path

This task is therefore partly a contract-definition slice, not just a generic
"same output everywhere" proof.

## Scope

- projection/rebuild parity over segmented history
- anchor behavior across hot and cold segments
- user-visible proof that one logical history still projects coherently
- explicit contracts for warm-history continuation versus cold-history access
- bounded behavior for ordinary operations when requested history extends beyond
  warm material

### Contract Pressure

The key contract question is not only:

```text
does split storage preserve observable meaning?
```

It is also:

```text
when is TOAS allowed to stay on a warm path, and when must it cross into cold history?
```

Likely requirements:

- recent continuation should not require loading arbitrarily old compressed
  segments
- cold-history traversal should be explicit, bounded, or diagnostically visible
- "can continue from warm history" and "can fully reconstruct deep history"
  are related but not identical contracts
- projection parity may need tiered guarantees rather than one unqualified
  promise

### Current Clarification

As of 2026-06-27, this task should assume the conservative contract:

- stitched logical history is a durable-state capability, not an automatic
  default for every user-facing history surface
- default `rebuild` and default `graph` should not silently traverse sealed
  cold segments merely because they exist
- any cold-history traversal on operator-facing surfaces should be intentional,
  explicit in the affordance, or otherwise clearly surfaced as crossing beyond
  the warm active working set
- parity therefore means "split storage does not change semantics within a
  declared access mode," not "every surface always behaves as if deep cold
  history were in the hot path"

## Non-Goals

- storage-layout ownership
- index strategy
- provenance metadata design

## Exit Evidence

- deterministic tests or acceptance-style proofs for split-storage projection
  parity
- explicit confirmation that storage segmentation does not alter transcript or
  history semantics
- an explicit warm-vs-cold contract describing when ordinary operations may
  refuse, defer, or require deeper history loading instead of silently taking a
  crazy-slow path

## Outcome

Closed on 2026-06-29.

The current contract is now explicit in the surrounding closed segmented-storage
chain:

- ordinary append/reconciliation remains hot-file scoped
- operator query/projection surfaces that advertise current logical history read
  the stitched durable view
- invalid segment layout and fatal message-history corruption fail closed rather
  than silently degrading into partial hot-file projections
- full graph rendering remains bounded by the existing node-count refusal

The `rebuild` wording in this task is historical. `260628-transcript-writeback-
surface-unification` removed the standalone `toas rebuild` command; the
transcript projection surface is now the resume-from-lineage proof surface.

Implementation evidence:

- `heads`, `history`, `transcript`, and `llm-input` already routed through
  `read_logical_history()`
- `graph` now builds from `read_logical_history()` as well, instead of reading
  only the hot events file
- `tests/test_operator_api.py::test_graph_text_uses_segmented_logical_history`
  proves cold-plus-hot graph projection parity
- `tests/test_operator_api.py::test_query_surfaces_use_segmented_logical_history`
  continues to prove transcript and LLM-input parity across the same storage
  split
