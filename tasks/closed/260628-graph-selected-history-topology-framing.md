Filed as: 260628-graph-selected-history-topology-framing
FKA:
AKA: graph topology view framing; graph implicit-anchor contract; graph discoverability alignment
Legacy index:

keywords: surface, implementation, historical, usability, graph, history, projection, naming

Parent: `260627-history-surface-user-intent-alignment`
Related: `260627-fail-closed-history-query-hardening`; `260627-history-recovery-tooling`; `260628-graph-local-neighborhood-selector`

# Graph Selected History Topology Framing

## Current Reality

`graph` already has a coherent core job, but its user contract is still
underframed:

- help/usage explain syntax more than purpose
- zero-arg whole-graph scope is not explained in family terms
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

Its zero-arg behavior should be explained as the topology-first whole-graph
view across current logical history, not as a disguised lineage view.

The sibling relationship should stay explicit:

- `history` is one root-to-head lineage through the graph
- `graph` is the topology view over that graph
- any intentional middle subset should arrive through explicit selection rather
  than more zero-arg heuristics

## Focus

- improve help/output framing so users know why and when to use `graph`
- make the whole-graph default explicit in the surface contract
- decide how much contextual middle selection should be deferred to explicit
  follow-on selector work rather than inferred heuristically
- clarify the operator-facing meaning of `temporal` and `consequence`
- decide whether oversize fallback should remain `heads`, gain a compact graph
  mode, or use stronger next-hop wording

## Exit Evidence

- `graph` help/output explains its role as the topology view over the selected
  history graph
- zero-arg behavior is documented as the topology-first whole-graph default
- any middle subset need is explicitly deferred to follow-on selector work
- oversize refusal/help text gives a coherent next hop
- focused tests cover framing/help or behavior changes that implement the new
  contract

## Completion Notes

- Kept `graph` topology-first rather than collapsing it toward `history`'s
  single-lineage job.
- Framed the rendered output as the selected history graph and stated that the
  surface shows topology across current logical history, with `history` as the
  sibling lineage view.
- Aligned command-local help, top-level help, and slash-command expectations
  with that same family story.
- Split the next bounded seam into `260628-graph-local-neighborhood-selector`
  so local subsets can arrive through explicit anchor-and-expansion selection
  rather than more zero-arg heuristics.
