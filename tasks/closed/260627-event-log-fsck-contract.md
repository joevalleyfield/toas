Filed as: 260627-event-log-fsck-contract
FKA:
AKA: event log fsck; durable history integrity check; graph fsck
Legacy index:

keywords: tooling, hardening, inception, correctness, graph, history, provenance, contract

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocks: `260627-history-surface-corruption-semantics`; `260627-fail-closed-history-query-hardening`
Related: `260627-segmented-event-index-and-lookup-hardening`; `260627-split-storage-rebuild-and-projection-parity`

# Event Log Fsck Contract

## Current Reality

TOAS currently assumes durable history is usable if it parses and roughly looks
message-shaped. The live repo shows that this is too weak: `.toas/events.jsonl`
can contain duplicate message ids while query and projection surfaces continue
by silently collapsing or skipping conflicting records.

Today there is no adopted integrity contract for a simple "git fsck equivalent"
pass over durable history.

## Desired Reality

TOAS should define a bounded, explicit durable-history integrity pass that can
classify whether an event journal is structurally trustworthy enough for graph,
history, and projection surfaces.

That contract should be strong enough to reject obvious graph corruption such
as duplicate message ids, missing parents, malformed message records, or other
record-shape violations before higher-level surfaces normalize the damage away.

## Focus

- define the minimal integrity checks for a durable-history `fsck`
- decide which checks are fatal versus warn-only
- define how hot plus sealed logical history participates in one integrity pass
- specify output/reporting shape for operator and test use
- keep the contract narrow and structural rather than speculative product UX

## Evidence

- Live repo trace on 2026-06-27 found duplicate message ids in
  `.toas/events.jsonl` (`n1` repeated 9 times, `n2` 6 times, and more), which
  would fail a simple graph-integrity check.
- `src/toas/graph_message_edges.py` and `src/toas/graph.py` currently collapse
  duplicates via `id -> event` map overwrite semantics.
- `src/toas/tools_cluster/event_graph.py` currently keeps only the first
  occurrence of a duplicate id when rendering the event graph.

## Exit Evidence

- an explicit integrity-check contract naming each structural failure class
- examples covering duplicate ids, missing parents, malformed message shape,
  and invalid segment layout interaction
- agreement on which downstream surfaces must refuse on fatal integrity errors

## Progress

- Added `fsck_logical_history(...)` in `src/toas/graph.py` as the first narrow
  contract/reporting seam for logical-history integrity.
- Current fatal classes implemented and covered:
  `invalid_segment_layout`, `duplicate_message_id`, `missing_parent`,
  `malformed_message_shape`.
- The report shape is intentionally small for now:
  `HistoryIntegrityReport(issues=[...])` with `ok`, `fatal_issues`, and
  `warning_issues` helpers.
- Operator history-facing surfaces now consult the integrity gate and refuse on
  fatal corruption: `heads`, `history`, `transcript`, `llm-input`, `rebuild`,
  and `graph`.
- Broader surface-policy refinement and any remaining hot/logical-history
  parity questions remain follow-on work under
  `260627-history-surface-corruption-semantics` and
  `260627-fail-closed-history-query-hardening`.

## Closure

Closed after landing the bounded durable-history fsck contract, coverage for
the adopted fatal structural classes, and fail-closed operator behavior across
`heads`, `history`, `transcript`, `llm-input`, `rebuild`, and `graph`.

Remaining work is follow-on rather than blocker material for this task:

- `260627-history-surface-corruption-semantics` for broader surface-policy
  refinement and any future warn-only classes.
- `260627-fail-closed-history-query-hardening` for additional parity and
  hardening follow-through beyond the operator surface seam landed here.

## Errata

- Immediate dogfooding after closure exposed one storage-contract exception the
  first cut of `fsck_logical_history(...)` did not preserve: fresh logs reserve
  `n0` as a virtual root sentinel and write first authored content as
  `n1 -> n0`.
- That means fail-closed parent validation must treat `n0` as an allowed
  virtual-root parent for new-log history rather than reporting it as fatal
  `missing_parent` corruption.
