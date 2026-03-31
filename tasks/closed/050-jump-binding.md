## Goal

Implement `toas jump N` as the manual binding override for transcript-to-history alignment.

## Scope

- Define how a jump target is represented
- Implement `run_jump(index: int)` behavior
- Make `step` honor the active override during alignment

## Behavior

- `toas jump N` declares that the current transcript should bind to node index `N`
- The override is explicit; it does not rely on normalization heuristics
- Applying a jump does not rewrite transcript content
- Applying a jump does not mutate prior history

## Open Design Points

- Whether the override is stored in `events.jsonl` as a non-causal control entry
- Whether anchors and jump share storage or stay separate
- How stale or invalid target indices are handled
- Whether the override is one-shot or persists until replaced

## Notes

- Byte-level LCP remains the default binding behavior
- `jump` is the semantic override when formatting changes would otherwise break continuity
- Sameness is declared, not inferred

## Done When

- `uv run toas jump N` records or applies a binding override
- A subsequent `toas step` can honor that override instead of relying only on byte-level LCP
- Transcript edits can be semantically rebound without replaying unrelated history
