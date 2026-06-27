Filed as: 260628-graph-selected-history-topology-framing
FKA:
AKA: graph topology view framing; graph implicit-anchor contract; graph discoverability alignment
Legacy index:

keywords: surface, implementation, follow-on, usability, graph, history, projection, naming

Parent: `260627-history-surface-user-intent-alignment`
Related: `260627-fail-closed-history-query-hardening`; `260627-history-recovery-tooling`

# Graph Selected History Topology Framing

## Current Reality

`graph` already has a coherent core job, but its user contract is still
underframed:

- help/usage explain syntax more than purpose
- zero-arg scope is not explained in terms of the shared implicit anchor rule
- oversize refusal points to `heads` without a clear family story
- projection names (`temporal`, `consequence`) remain more explicit than their
  operator-facing explanation

The parent requirements task now gives a sharper target:

- `graph` is the selected history graph
- `history` is one root-to-head lineage through that graph
- `heads` is the leaf set of that graph

## Desired Reality

`graph` should read as the topology-oriented view over the same selected
history graph that sibling surfaces use.

Its zero-arg behavior should be explained in terms of the shared implicit
anchor rule:

- outside transcript context: last head and its ancestors
- inside transcript context: the lineage identified by transcript LCP

If topology rendering intentionally broadens beyond that slice for context,
that broadening should be visible and justified.

## Focus

- improve help/output framing so users know why and when to use `graph`
- make the implicit-anchor rule visible in the surface contract
- decide how much contextual broadening beyond the implicit slice is desirable
- clarify the operator-facing meaning of `temporal` and `consequence`
- decide whether oversize fallback should remain `heads`, gain a compact graph
  mode, or use stronger next-hop wording

## Exit Evidence

- `graph` help/output explains its role as the topology view over the selected
  history graph
- zero-arg behavior is documented in terms of the shared implicit anchor rule
- any broadening beyond the implicit slice is explicit rather than accidental
- oversize refusal/help text gives a coherent next hop
- focused tests cover framing/help or behavior changes that implement the new
  contract
