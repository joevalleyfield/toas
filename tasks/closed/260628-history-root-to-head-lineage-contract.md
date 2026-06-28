Filed as: 260628-history-root-to-head-lineage-contract
FKA:
AKA: history lineage view narrowing; history root-to-head output contract; history surface path projection
Legacy index:

keywords: surface, implementation, follow-on, usability, history, projection, graph, transcript

Parent: `260627-history-surface-user-intent-alignment`
Related: `260627-fail-closed-history-query-hardening`; `260627-history-recovery-tooling`

# History Root-To-Head Lineage Contract

## Current Reality

`history` currently mixes several concerns:

- selected-head/bind-era status lines
- a terse head list
- recent durable-event summaries

That makes it hard to treat `history` as one coherent user-facing view.

The parent requirements task now gives a sharper target:

- `graph` is the selected history graph
- `history` is one root-to-head lineage through that graph
- `heads` is the leaf set of that graph

## Desired Reality

`history` should become the root-to-head lineage view over the shared implicit
anchor slice:

- outside transcript context: last head and its ancestors
- inside transcript context: the lineage identified by transcript LCP

On success, the command should read as one path through history rather than as
a mixed debug/status surface.

## Focus

- remove or relocate default output material that does not serve the lineage
  job
- define the zero-arg output contract for one root-to-head lineage
- decide whether the command should show all lineage rows or a bounded readable
  window over that lineage
- improve help/output framing so users can tell they are seeing a lineage view
- keep refusal/error wording aligned with the parent surface-family contract

## Exit Evidence

- `history` success output reads as one root-to-head lineage rather than a
  mixed summary
- stale bind-era/status framing is removed from the default surface or
  explicitly justified
- zero-arg behavior is documented in terms of the shared implicit anchor rule
- focused tests cover the new output contract and refusal/help behavior

## Progress

- 2026-06-28: Narrowed `history` default output to a bounded root-to-head
  lineage window instead of mixed selected-head/bind/head-summary/recent-event
  output. The surface now frames itself as lineage, keeps `limit` as a
  readable-window control, and reports when earlier lineage rows are omitted.
- 2026-06-28: Tightened `history` argument handling so `toas history --help`
  and invalid limits fail with a usage line instead of a raw integer-parse
  traceback, keeping the surface's local help behavior aligned with the task's
  discoverability contract.
- 2026-06-28: Moved the zero-arg lineage contract into user-facing surfaces:
  top-level `toas help`, `toas history --help`, session CLI help, and repo docs
  now describe `history` as the bounded root-to-head lineage view over the
  current default lineage.

## Closure

- 2026-06-28: Closed after the default `history` surface, local help behavior,
  and user-facing docs all converged on the same contract: `history` is the
  bounded root-to-head lineage view for the current default lineage, while
  `heads` remains the compact branch-tip sibling surface.
