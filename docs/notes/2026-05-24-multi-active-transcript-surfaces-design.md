# Multi-Active Transcript Surfaces Over Shared Graph (Task 561)

## Status

Directional design note. This is the implementation contract for opening `561` after `550` closure.

## Problem

TOAS currently treats one transcript path as the primary authored surface for one step loop.
That is insufficient for operator workflows that maintain multiple independent authored surfaces in the same repository (for example: docs-keeper, roadmap, bug triage), while sharing one durable message graph.

Without explicit surface identity in durable/control records, continuity can be inferred from the wrong context and accidentally inherit lineage from unrelated transcript evolution.

## Design Constraints

1. Transcript-first remains primary: authored transcript changes drive graph updates.
2. Continuity inference stays LCP-based per transcript surface.
3. No explicit branch metadata is authored in transcript text.
4. Shared graph remains extraction from transcript evolution, not source-of-truth replacement.
5. Existing single-surface behavior remains a degenerate case.

## Core Model

### Surface Identity

Define a stable `surface_id` for each transcript control surface.

- Default surface id: `default`
- Default path: existing configured transcript path (currently `.toas/session.md` by default)
- Additional surfaces: explicit operator registration/binding to transcript paths

`surface_id` is operational metadata and durable-control context, not transcript inline content.

### Surface Continuity State

For each `surface_id`, runtime tracks:

- `surface_id`
- `transcript_path`
- `last_anchor_head_id` (most recent selected/rebuilt head context for that surface)
- `last_transcript_fingerprint` (for guardrails and stale-path detection)

This state must be recoverable from durable records; no hidden daemon-only authority.

### Durable Record Shapes

Introduce control records (append-only) to make surface provenance auditable:

1. `surface_bind`
- payload: `{surface_id, transcript_path, reason}`
- written when a surface is first created or path is intentionally rebound

2. `surface_select`
- payload: `{surface_id, transcript_path}`
- written when operator explicitly selects active surface for stepping

3. `surface_rebind`
- payload: `{surface_id, from_head_id, to_head_id, reason}`
- written when continuity is intentionally retargeted beyond normal LCP evolution

4. `surface_guardrail`
- payload: `{surface_id, candidate_parent_id, decision, reason, override}`
- written when unrelated-lineage detection triggers block/warn/confirm pathways

These are control records only; message events remain message events.

## Continuity Semantics

For a `toas step` on surface `S`:

1. Load transcript from `S.transcript_path`.
2. Compute LCP against transcript projection for `S` context.
3. Build new message nodes from divergence boundary using existing rewrite laws (`550` root-sentinel semantics included).
4. Parent selection is resolved strictly within `S` continuity context unless explicit rebind intent exists.

Rule: selected tip from surface `A` cannot silently seed parentage for unrelated divergence in surface `B`.

## Guardrail Policy (Initial)

At divergence time, if candidate parent lineage is not reachable from `S.last_anchor_head_id` and LCP does not prove continuity, classify as probable unrelated inheritance.

Default policy:

- fail closed for implicit attach
- require explicit rebind command/intention to proceed
- emit `surface_guardrail` record with reason and candidate ids

This mirrors the anti-accidental-inheritance principle already established for root divergence semantics in `550`.

## CLI/Runtime Surface Proposal

1. `toas surface list`
- show `surface_id`, path, active marker, last anchor

2. `toas surface select <surface_id>`
- set active surface for subsequent `step`
- write `surface_select`

3. `toas surface bind <surface_id> <transcript_path>`
- create/update mapping intentionally
- write `surface_bind`

4. `toas step --surface <surface_id>`
- explicit one-shot surface targeting
- preserves existing behavior when omitted (`default`)

5. `toas surface rebind <surface_id> --to-head <head_id> --reason <text>`
- explicit continuity retarget
- write `surface_rebind`

## Compatibility and Migration

1. Existing repos with no surface records are interpreted as single-surface `default`.
2. Existing transcript path config remains authoritative for `default` path.
3. No mutation/rewrite of historical message events is required.
4. Optional backfill can append `surface_bind` bootstrap record on first command that touches multi-surface APIs.

## Test Plan (Implementation Target)

1. Independent surfaces step without cross-parent inheritance.
2. Same transcript content under two surfaces remains independently auditable via control records.
3. Root divergence on any surface still respects `550` law (effective root sentinel anchoring, never selected-tip inheritance).
4. Guardrail blocks probable unrelated attach without explicit rebind.
5. Explicit rebind path unblocks and leaves durable provenance trail.
6. Default single-surface flows stay behavior-compatible.

## Implementation Slices

1. Storage/query seams for surface control records and active-surface resolution.
2. Runtime step integration with `surface_id` context propagation.
3. Guardrail classifier + enforcement seam + deterministic tests.
4. CLI command family (`surface *`) and `--surface` option wiring.
5. Projection/docs updates for operator visibility.

