## Goal

Use anchors as real runtime shortcuts for transcript alignment and projection.

## Scope

- Define which transcript offsets and message-event ids are worth anchoring
- Teach alignment to resume from a nearby anchor rather than full replay
- Teach projection helpers to reuse anchors where they improve locality

## Behavior

- Anchors remain non-causal control records
- Alignment may start from an anchor-backed checkpoint before validating nearby transcript content
- Projection may emit fresh anchors as a side effect when that improves later work

## Rules

- Anchors are performance and locality aids, not sources of truth
- Alignment must still validate transcript/history correspondence around the resumed region
- Missing or stale anchors must degrade safely to existing replay behavior
- Anchor use must not change message lineage semantics

## Non-Goals

- No aggressive indexing layer yet
- No speculative anchor scheme that outruns observed usage

## Done When

- Anchor records participate in at least one real alignment shortcut
- The runtime can fall back cleanly when anchors are absent or stale
- The behavior is covered by tests that prove correctness is preserved
