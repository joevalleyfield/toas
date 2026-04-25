## Goal

Define and implement explicit mixed-intent arbitration for user-frontier turns that contain multiple executable/operator intents, with configurable ordering policy and surfaced intent IDs.

## Why Now

`441` covers the immediate precedence regression (slash command can be bypassed by executable intent). But operator workflow needs a first-class model for intentional multi-intent turns (for example last-wins vs in-order) without greedy hidden selection.

## Scope

- introduce an explicit mixed-intent arbitration policy surface (config/runtime):
  - `first_wins`
  - `last_wins`
  - `in_order`
  - optional strict/disallow mode for ambiguous turns
- set default arbitration mode to `in_order` (operator-first expectation)
- collect all eligible frontier intent candidates with ordering metadata instead of greedy single-plan selection
- assign stable per-turn intent IDs and surface them in projection/result channels
- define queue behavior for `in_order` mode using `331` durability/continuation patterns
- add `/help` and operator-facing usage notes for the new arbitration controls

## Intended Behavior

- mixed-intent turns are deterministic under explicit policy
- ordering choice is visible and auditable
- operators can reference specific extracted intents by ID
- queue-backed continuation behavior is consistent with `331`
- queue and intent handles are visible in text projections, not only transient stderr/result hints

## Constraints

- preserve append-only history invariants
- preserve user-intent vs model-addressable capability boundary
- avoid hidden parser heuristics that silently drop candidate intents

## Done When

- arbitration policy is implemented and test-covered
- mixed-intent tests cover at least `first_wins`, `last_wins`, and `in_order`
- intent IDs are visible in at least one operator-facing surface (`/extract`, `/replay`, or equivalent projection path)
- queue IDs are visible in at least one persistent operator-facing surface (for example history/state projection), not only blocked-event text
- docs/help include concrete examples for selecting and continuing mixed-intent execution

## Progress

- 2026-04-25: Landed first intent-ID surfacing slice on `/extract`:
  - candidate preview lines now include stable per-turn IDs (`#d1`, `#d2`, ...)
  - `/extract` selection parser now accepts ID tokens in addition to numeric index (`d1` and `#d1`)
  - added handler/parser and end-to-end regressions for ID parsing and projection text
- 2026-04-25: Landed first mixed-intent arbitration policy slice on user-frontier execution:
  - added `extraction.intent_arbitration` config key with `in_order` default and supported values `first_wins|last_wins|in_order`
  - user-frontier mixed intent candidates are now selected via explicit arbitration policy instead of implicit greedy precedence
  - default `in_order` behavior executes mixed slash/tool/shell intent in deterministic operator->plan->shell order
  - added runtime helper tests for `first_wins`, `last_wins`, and default `in_order`, plus end-to-end step coverage for mixed slash+plan turns under each mode
- 2026-04-25: Landed replay intent-ID surfacing and selection follow-on:
  - `/replay` candidate projection now shows replay intent IDs (`#rN`) alongside numeric indices.
  - `/replay --index` now accepts `rN` and `#rN` selectors in addition to numeric indices.
  - replay usage/help text updated to advertise `--index <n|rN>` shape.
- 2026-04-25: Landed mixed-intent consequence annotation follow-on:
  - user-frontier mixed-intent execution now annotates consequence nodes with `intent_execution` metadata (`id`, `kind`, `order`, `total`, `arbitration`).
  - annotation is scoped to mixed-intent turns only (`total > 1`) to preserve single-intent output shape compatibility.
- 2026-04-25: Landed persistent-handle visibility follow-on in `/outline`:
  - outline rows now surface mixed-intent execution handles (`intent:<dN>`) when `intent_execution.id` metadata is present on a message.
  - outline rows now surface queue handles (`queue:<qN>`) when queue-update metadata is present on a message.
- 2026-04-25: Landed arbitration discoverability follow-on in help content:
  - `/help` common-goals section now includes explicit `extraction.intent_arbitration` tuning examples for `in_order`, `first_wins`, and `last_wins`.
- 2026-04-25: Landed optional strict arbitration mode:
  - `extraction.intent_arbitration` now supports `strict`.
  - strict mode rejects mixed-intent user-frontier turns with an actionable error listing detected handles (for example `#d1:operator`, `#d2:plan`) instead of executing any intent.
- 2026-04-25: Landed strict/arbitration and replay-queue discoverability examples in `/help`:
  - `/help` common-goals now includes `strict` arbitration toggle and explicit replay/queue continuation examples (`/replay --index #r1`, `/queue approve`).
