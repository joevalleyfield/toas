Filed as: 260628-heads-selected-history-leaf-framing
FKA:
AKA: heads branch-tip framing; heads leaf-set contract; selected history leaf view
Legacy index:

keywords: surface, implementation, follow-on, usability, heads, history, graph, framing

Parent: `260627-history-surface-user-intent-alignment`
Related: `260628-history-preview-heuristic-selection`; `260627-history-recovery-tooling`; `260628-graph-selected-history-topology-framing`

# Heads Selected History Leaf Framing

## Current Reality

`history` and `graph` now have local usage/framing that teaches their place in
the selected-history surface family.

`heads` does not.

Today the command is useful and fairly honest once you already know TOAS:

- zero-arg invocation is safe
- the row format is compact and information-dense
- the output is effectively the leaf set of the selected history graph

But that contract is mostly implicit. A user can discover `heads` from global
help, yet the command still lacks nearby language explaining:

- what object it is listing
- how it relates to `history` and `graph`
- why to choose it over those sibling surfaces
- what its compact row fields mean at first encounter

That leaves `heads` readable for substrate-fluent operators but less teachable
than its sibling surfaces.

## Desired Reality

`heads` should read as the compact branch-tip or leaf-set view over the same
selected history graph that `graph` renders topologically and `history` samples
as one bounded lineage.

The first follow-on should improve framing and discoverability without changing
the underlying leaf-set semantics.

## Focus

- define the operator-facing contract for `heads` in one narrow sentence
- add local usage/help text consistent with the selected-history family
- decide whether the command should print a short framing line before rows
- make the row fields legible enough for first successful use
- preserve zero-arg default scope on the shared implicit anchor
- keep preview-quality improvements delegated to the separate preview task

## Non-Goals

- redesigning head-selection semantics
- adding new selectors or filters
- broad branch-management workflows
- richer preview synthesis beyond cheap shared heuristics

## Exit Evidence

- `toas heads --help` teaches the command as the leaf-set sibling to `history`
  and `graph`
- top-level CLI help and any nearby docs use compatible wording
- first successful output is better framed or otherwise easier to interpret on
  sight
- focused tests lock the help/output contract without widening the surface job

## Progress

- implemented local `toas heads --help` usage framing
- added a short success-output framing header that teaches `heads` as the
  compact leaf-set sibling to `history` and `graph`
- aligned top-level help plus nearby user-facing docs with the same contract

## Implemented

- `toas heads --help` now explains the command as the selected-history
  leaf-set or compact branch-tip sibling to `history` and `graph`
- successful `toas heads` output now starts with a short framing header before
  the compact per-head rows
- top-level CLI help and nearby contributor-facing docs now use the same
  selected-history leaf-set wording
