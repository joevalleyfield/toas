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

## Scope

- projection/rebuild parity over segmented history
- anchor behavior across hot and cold segments
- user-visible proof that one logical history still projects coherently

## Non-Goals

- storage-layout ownership
- index strategy
- provenance metadata design

## Exit Evidence

- deterministic tests or acceptance-style proofs for split-storage projection
  parity
- explicit confirmation that storage segmentation does not alter transcript or
  history semantics
